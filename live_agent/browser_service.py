import asyncio
import json
import base64
import sys
import hashlib
from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
from playwright.async_api import async_playwright
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# --- 配置区 ---
USER_DATA_DIR = os.path.join(os.getcwd(), "browser_session")
TARGET_URL = "https://buyin.jinritemai.com/mpa/account/login"
EWID_STORAGE_KEY = "__ecom_did_sdk"
AES_KEY = "ecom-did-sdk"

def decrypt_cryptojs_aes(encrypted_b64, password):
    """Python 端解密 CryptoJS AES 密文"""
    try:
        data = base64.b64decode(encrypted_b64)
        if data[:8] != b'Salted__':
            return None
        
        salt = data[8:16]
        ciphertext = data[16:]
        
        def evp_bytes_to_key(password, salt, key_len, iv_len):
            m = b''
            result = b''
            while len(result) < (key_len + iv_len):
                m = hashlib.md5(m + password + salt).digest()
                result += m
            return result[:key_len], result[key_len:key_len + iv_len]

        key, iv = evp_bytes_to_key(password.encode(), salt, 32, 16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return json.loads(decrypted.decode('utf-8'))
    except Exception as e:
        print(f"[!] 解密失败: {e}")
        return None

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser_context = None
        self.page = None
        self._start_lock = asyncio.Lock()

    async def start(self):
        async with self._start_lock:
            if self.page:
                return
            
            try:
                if not os.path.exists(USER_DATA_DIR):
                    os.makedirs(USER_DATA_DIR)
                    
                print("[*] 正在初始化 Playwright...")
                self.playwright = await async_playwright().start()
                
                print(f"[*] 启动浏览器 (持久化目录: {USER_DATA_DIR})...")
                self.browser_context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=USER_DATA_DIR,
                    headless=False,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                    ]
                )
                
                await self.browser_context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                self.page = await self.browser_context.new_page()
                print(f"[*] 正在跳转至: {TARGET_URL}")
                await self.page.goto(TARGET_URL, wait_until="networkidle")
                print("[!] 浏览器已就绪。")
            except Exception as e:
                print(f"[!] 浏览器启动失败: {e}")
                raise e

    async def get_session_data(self):
        if not self.page or self.page.is_closed():
            return {"status": "error", "message": "Browser not initialized or page closed."}

        try:
            # 获取 Cookie
            cookies = await self.browser_context.cookies()
            cookie_dict = {c['name']: c['value'] for c in cookies}
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])

            # 获取 localStorage 中的加密串
            raw_storage = await self.page.evaluate("""(storageKey) => {
                return localStorage.getItem(storageKey);
            }""", EWID_STORAGE_KEY)

            # 在 Python 端进行解密
            ewid_info = None
            if raw_storage:
                ewid_info = decrypt_cryptojs_aes(raw_storage, AES_KEY)

            return {
                "status": "success",
                "ewid": ewid_info,
                "raw_storage": raw_storage,
                "cookie_str": cookie_str,
                "cookie_dict": cookie_dict,
                "url": self.page.url
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def call_api_in_browser(self, method, url, data=None):
        """核心方法：在浏览器内部通过 fetch 调用 API，自动带上 Cookie 和签名"""
        if not self.page or self.page.is_closed():
            return {"status": "error", "message": "Browser not initialized"}
        
        script = """async (args) => {
            const { method, url, data } = args;
            try {
                const options = {
                    method: method,
                    headers: {
                        'accept': 'application/json, text/plain, */*',
                        'content-type': 'application/json'
                    }
                };
                if (data) {
                    options.body = JSON.stringify(data);
                }
                const response = await fetch(url, options);
                const result = await response.json();
                return { status: 'success', data: result };
            } catch (e) {
                return { status: 'error', message: e.message };
            }
        }"""
        return await self.page.evaluate(script, {"method": method, "url": url, "data": data})

manager = BrowserManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(manager.start())
    yield
    if manager.playwright:
        await manager.playwright.stop()

app = FastAPI(lifespan=lifespan)

@app.get("/get_data")
async def get_data():
    return await manager.get_session_data()

@app.post("/proxy_api")
async def proxy_api(request_data: dict):
    """通用代理接口"""
    method = request_data.get("method", "GET")
    url = request_data.get("url")
    data = request_data.get("data")
    return await manager.call_api_in_browser(method, url, data)

@app.get("/refresh")
async def refresh_page():
    try:
        if not manager.page or manager.page.is_closed():
            await manager.start()
        else:
            await manager.page.reload(wait_until="networkidle")
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
