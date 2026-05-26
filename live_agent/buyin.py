import os
import asyncio
import threading
import json
import base64
import hashlib
import logging
import psutil
import sys
from PySide6.QtCore import QObject, Signal
from playwright.async_api import async_playwright
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from live_agent.utils import get_app_data_dir

# 获取当前模块的日志记录器
logger = logging.getLogger("BuYin")

# --- 核心路径配置 ---
BASE_DIR = get_app_data_dir()
USER_DATA_DIR = os.path.join(BASE_DIR, "browser_session")
PID_FILE = os.path.join(USER_DATA_DIR, ".browser.pid") 
TARGET_URL = "https://buyin.jinritemai.com/mpa/account/login"
EWID_STORAGE_KEY = "__ecom_did_sdk"
AES_KEY = "ecom-did-sdk"

# --- 打包兼容逻辑 ---
def setup_playwright_env():
    """如果是打包环境，确保环境变量正确"""
    if getattr(sys, 'frozen', False):
        # 优先使用 run_gui.py 或外部设置好的路径
        if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
            from pathlib import Path
            bundle_dir = Path(sys._MEIPASS)
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundle_dir / "ms-playwright")
        logger.debug(f"Playwright 浏览器路径: {os.environ.get('PLAYWRIGHT_BROWSERS_PATH')}")

class BuYin(QObject):
    """百应业务逻辑类：负责 Playwright 自动化、凭证提取及接口代理"""
    browser_started = Signal()
    browser_closed = Signal() 
    data_ready = Signal(dict)
    api_finished = Signal(str, dict)  # tag, result
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        setup_playwright_env()
        self.loop = None
        self.playwright = None
        self.context = None
        self.page = None
        # 启动专用异步线程
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()
        logger.debug("BuYin 逻辑线程已启动")

    def _run_event_loop(self):
        """后台异步事件循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_async(self, coro):
        """线程安全的异步提交工具"""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    # --- 内部辅助：AES 解密 ---
    def _decrypt_ewid(self, encrypted_b64):
        """解密从浏览器 localStorage 获取的加密身份信息"""
        try:
            data = base64.b64decode(encrypted_b64)
            if data[:8] != b"Salted__":
                logger.error("解密失败：无效的 Salt 头部")
                return None
            salt = data[8:16]
            ciphertext = data[16:]
            def evp_key(pwd, salt, klen, ilen):
                m = b""; res = b""
                while len(res) < (klen + ilen):
                    m = hashlib.md5(m + pwd + salt).digest()
                    res += m
                return res[:klen], res[klen : klen + ilen]
            key, iv = evp_key(AES_KEY.encode(), salt, 32, 16)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
            result = json.loads(decrypted.decode("utf-8"))
            logger.debug(f"ewid 解密成功: {result}")
            return result
        except Exception as e:
            logger.exception(f"ewid 解密抛出异常: {e}")
            return None

    # --- 核心协程逻辑 ---
    async def _do_start(self):
        """启动浏览器并导航至目标页面"""
        try:
            if self.page and not self.page.is_closed():
                logger.warning("浏览器已在运行中")
                return

            # 1. 精准清理残留
            await self._cleanup_previous_process()
            
            if not os.path.exists(USER_DATA_DIR):
                os.makedirs(USER_DATA_DIR)
            else:
                self._remove_singleton_locks()

            self.playwright = await async_playwright().start()
            
            # 2. 启动上下文
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                ignore_default_args=["--enable-automation"],
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--mute-audio",
                ],
            )

            # 定义统一的内部清理逻辑
            def handle_internal_close(source):
                logger.info(f"后台：感知到 {source} 已关闭，准备执行清理...")
                # 异步执行彻底关闭
                self.run_async(self._do_close(False))
                # 通知 UI 层
                self.loop.call_soon_threadsafe(self.browser_closed.emit)

            # 监听整个浏览上下文的关闭
            self.context.on("close", lambda _: handle_internal_close("Context"))
            self.context.on("crash", lambda _: handle_internal_close("Context Crashed"))
            
            # 监听 Playwright 驱动断开（浏览器进程被强制杀死）
            self.playwright.on("disconnect", lambda _: handle_internal_close("Playwright Disconnected"))
            
            # 资源拦截逻辑
            await self.context.route("**/*", lambda route: self._resource_blocker(route))
            
            # Stealth 逻辑
            await self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 防误关脚本
            protect_script = """
            window.onbeforeunload = function(e) {
                const msg = '正在同步直播数据，确定要离开吗？';
                e = e || window.event;
                if (e) e.returnValue = msg;
                return msg;
            };
            """
            await self.context.add_init_script(protect_script)

            # 3. 页面初始化
            self.page = await self.context.new_page()
            # 监听特定页面的关闭
            self.page.on("close", lambda _: handle_internal_close("Page"))

            self._record_pid()
            asyncio.create_task(self._dom_cleaner_loop())

            logger.info(f"正在导航至: {TARGET_URL}")
            try:
                await self.page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                logger.warning(f"初次导航重试: {e}")
                await asyncio.sleep(1)
                await self.page.goto(TARGET_URL)
            
            self.browser_started.emit()
            logger.info("浏览器已就绪")
        except Exception as e:
            logger.exception(f"启动浏览器失败: {e}")
            self.error_occurred.emit(str(e))
            await self._do_close(False)

    async def _cleanup_previous_process(self):
        """精准清理上一次运行残留的进程"""
        if not os.path.exists(PID_FILE): return
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            if psutil.pid_exists(old_pid):
                proc = psutil.Process(old_pid)
                if any(x in proc.name().lower() for x in ["chrome", "chromium"]):
                    logger.info(f"清理残留进程 PID: {old_pid}")
                    proc.kill()
                    await asyncio.sleep(0.5)
        except: pass
        finally: self._clear_pid_file()

    def _record_pid(self):
        """记录当前子进程 PID"""
        try:
            children = psutil.Process().children(recursive=True)
            for child in children:
                if any(x in child.name().lower() for x in ["chrome", "chromium"]):
                    with open(PID_FILE, "w") as f:
                        f.write(str(child.pid))
                    break
        except: pass

    def _clear_pid_file(self):
        if os.path.exists(PID_FILE):
            try: os.unlink(PID_FILE)
            except: pass

    def _remove_singleton_locks(self):
        """删除 Chrome 锁定文件"""
        for lock_file in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
            path = os.path.join(USER_DATA_DIR, lock_file)
            if os.path.exists(path):
                try: os.unlink(path)
                except: pass

    async def _resource_blocker(self, route):
        """拦截图片、媒体、字体以节省内存"""
        if route.request.resource_type in ["image", "media", "font", "imageset"]:
            await route.abort()
        else:
            await route.continue_()

    async def _dom_cleaner_loop(self):
        """后台刷新页面防止内存泄漏"""
        while self.page and not self.page.is_closed():
            try:
                await asyncio.sleep(600)
                if self.page and not self.page.is_closed():
                    logger.info("内存保护：刷新控制台页面")
                    await self.page.reload()
            except: break

    async def _do_get_data(self):
        """提取 Session 数据"""
        if not self.page or self.page.is_closed(): return
        try:
            raw = await self.page.evaluate(f"localStorage.getItem('{EWID_STORAGE_KEY}')")
            info = self._decrypt_ewid(raw) if raw else None
            self.data_ready.emit({"ewid": info, "url": self.page.url})
        except Exception as e:
            logger.error(f"同步数据失败: {e}")

    async def _do_proxy_call(self, tag, method, url, data=None):
        """在浏览器内代理 API 调用"""
        if not self.page or self.page.is_closed(): return
        try:
            script = """async (args) => {
                const { method, url, data } = args;
                try {
                    const opt = { 
                        method, credentials: 'include',
                        headers: { 'content-type': 'application/json', 'accept': 'application/json, text/plain, */*' } 
                    };
                    if (data) opt.body = JSON.stringify(data);
                    const res = await fetch(url, opt);
                    const result = await res.json();
                    return { status: 'success', data: result };
                } catch (e) { return { status: 'error', message: e.message }; }
            }"""
            res_wrapper = await self.page.evaluate(script, {"method": method, "url": url, "data": data})
            if res_wrapper["status"] == "success":
                self.api_finished.emit(tag, res_wrapper["data"])
        except Exception as e:
            logger.error(f"API 代理异常 | {tag}: {e}")

    # --- 外部公开业务方法 ---
    def start_browser(self): 
        self.run_async(self._do_start())
    
    def close_browser(self, clear_data=False):
        """彻底释放资源"""
        logger.info(f"用户触发：请求关闭资源 | 清理数据: {clear_data}")
        if not self.playwright:
            if clear_data: self._clear_local_data()
            return
        self.run_async(self._do_close(clear_data))

    async def _do_close(self, clear_data):
        try:
            if self.context:
                try: await self.context.close()
                except: pass
                self.context = None
            
            if self.playwright:
                try: await self.playwright.stop()
                except: pass
                self.playwright = None
            
            self.page = None
            self._clear_pid_file()
            
            if clear_data: self._clear_local_data()
            logger.info("后台资源释放完毕")
        except Exception as e:
            logger.error(f"释放资源时出现异常: {e}")

    def _clear_local_data(self):
        if os.path.exists(USER_DATA_DIR):
            import shutil
            try: shutil.rmtree(USER_DATA_DIR)
            except: pass

    def refresh_data(self): self.run_async(self._do_get_data())
    
    def get_account_info(self, ewid):
        url = f"https://darenim.jinritemai.com/chat/api/sd/by/account?PIGEON_BIZ_TYPE=5&ewid={ewid}"
        self.run_async(self._do_proxy_call("ACCOUNT_INFO", "GET", url))
        
    def get_live_status(self, ewid):
        url = f"https://buyin.jinritemai.com/api/anchor/livepc/playinfo?ewid={ewid}&source=2"
        self.run_async(self._do_proxy_call("LIVE_STATUS", "GET", url))

    def get_intelligent_reply_status(self, ewid):
        url = f"https://buyin.jinritemai.com/api/anchor/comment/intelligent_reply_get?ewid={ewid}"
        self.run_async(self._do_proxy_call("GET_STATUS", "GET", url))

    def set_intelligent_reply_status(self, ewid, enabled):
        url = f"https://buyin.jinritemai.com/api/anchor/comment/intelligent_reply_set?ewid={ewid}"
        self.run_async(self._do_proxy_call("SET_STATUS", "POST", url, {"switch": enabled}))

    def get_auto_reply_rules(self, ewid):
        url = f"https://buyin.jinritemai.com/api/anchor/comment/auto_reply_get?ewid={ewid}"
        self.run_async(self._do_proxy_call("GET_RULES", "GET", url))

    def set_auto_reply_rules(self, ewid, rules):
        url = f"https://buyin.jinritemai.com/api/anchor/comment/auto_reply_set?ewid={ewid}"
        self.run_async(self._do_proxy_call("SET_RULES", "POST", url, {"auto_reply_list": rules}))

    def send_danmu(self, ewid, content):
        url = f"https://buyin.jinritemai.com/api/anchor/comment/operate_v2?ewid={ewid}"
        self.run_async(self._do_proxy_call("SEND_DANMU", "POST", url, {"operate_type": 2, "content": content}))
