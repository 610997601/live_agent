"""主窗口 —— 布局组装与多模块协调。"""

import threading
import requests
from datetime import datetime, timedelta, timezone
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStatusBar,
    QLabel, QPushButton, QListWidget, QStackedWidget, QMessageBox, QFrame, QApplication
)

from live_agent.buyin import BuYin
from live_agent.gui.panels.voice_panel import VoicePanel
from live_agent.gui.panels.reply_panel import ReplyPanel
from live_agent.gui.panels.danmaku_panel import DanmakuPanel

class MainWindow(QMainWindow):
    """集成了语音识别、回复配置及定时弹幕的统一主窗口。"""
    avatar_loaded = Signal(QPixmap)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("直播助手 - 统一客户端")
        self.setMinimumSize(1000, 750)
        self.resize(1100, 800)

        # 业务逻辑实例
        self.buyin = BuYin()
        self.ewid = None
        self.is_live = False
        self.is_browser_open = False

        # 核心监控计时器 (用于授权后的状态轮询)
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self._on_monitor_tick)

        self._init_ui()
        self._connect_signals()
        self._update_ui_state()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 1. 顶部状态栏 / Header ---
        header = QFrame()
        header.setFixedHeight(65)
        header.setStyleSheet("background-color: white; border-bottom: 1px solid #d2d2d7;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        header_layout.setSpacing(15)

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(44, 44)
        self.avatar_label.setStyleSheet("border-radius: 22px; background-color: #f5f5f7; border: 1px solid #d2d2d7;")
        self.avatar_label.setScaledContents(True)

        self.account_label = QLabel("未授权")
        self.account_label.setStyleSheet("font-weight: 600; font-size: 15px; color: #1d1d1f;")

        self.live_status_label = QLabel("直播状态: 需先登录")
        self.live_status_label.setStyleSheet("color: #86868b; font-size: 13px; margin-left: 10px;")

        header_layout.addWidget(self.avatar_label)
        header_layout.addWidget(self.account_label)
        header_layout.addWidget(self.live_status_label)
        header_layout.addStretch()

        self.login_btn = QPushButton("🚀 授权登录")
        self.login_btn.setMinimumHeight(34)
        self.login_btn.clicked.connect(self._on_login_click)

        self.refresh_btn = QPushButton("🔄 同步")
        self.refresh_btn.setMinimumHeight(34)
        self.refresh_btn.clicked.connect(self.buyin.refresh_data)

        header_layout.addWidget(self.login_btn)
        header_layout.addWidget(self.refresh_btn)
        main_layout.addWidget(header)

        # --- 补充 'by' 项目缺失的全局提示 ---
        self.warning_label = QLabel(
            "⚠️ 运行中：请务必保持浏览器和程序打开的百应页面开启！"
        )
        self.warning_label.setStyleSheet(
            "color: #d35400; background-color: #fff3cd; padding: 10px 20px; font-weight: bold; border-bottom: 1px solid #ffeeba;"
        )
        self.warning_label.setVisible(False)
        main_layout.addWidget(self.warning_label)

        # --- 2. 主体部分 (侧栏 + 内容) ---
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 左侧导航
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #f5f5f7;
                border: none;
                border-right: 1px solid #d2d2d7;
                color: #1d1d1f;
                font-size: 14px;
                outline: none;
            }
            QListWidget::item {
                padding: 18px 20px;
                border: none;
                border-radius: 0px;
            }
            QListWidget::item:selected {
                background-color: #e8e8ed;
                color: #0071e3;
                font-weight: bold;
            }
            QListWidget::item:hover:!selected:enabled {
                background-color: #f0f0f2;
            }
            QListWidget::item:disabled {
                color: #aeaeb2;
            }
        """)
        self.sidebar.addItems(["🎤 语音识别", "🤖 回复配置", "💬 定时弹幕"])
        self.sidebar.currentRowChanged.connect(self._on_nav_changed)

        # 右侧内容堆栈
        self.content_stack = QStackedWidget()
        
        self.voice_panel = VoicePanel()
        self.reply_panel = ReplyPanel(self.buyin)
        self.danmaku_panel = DanmakuPanel(self.buyin)

        self.content_stack.addWidget(self.voice_panel)
        self.content_stack.addWidget(self.reply_panel)
        self.content_stack.addWidget(self.danmaku_panel)

        body_layout.addWidget(self.sidebar)
        body_layout.addWidget(self.content_stack)
        main_layout.addWidget(body)

        # --- 3. 底部状态栏 ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("准备就绪")

        self.sidebar.setCurrentRow(0)

    def _connect_signals(self):
        # BuYin 信号
        self.buyin.browser_started.connect(self._on_browser_started)
        self.buyin.browser_closed.connect(self._on_browser_closed)
        self.buyin.data_ready.connect(self._on_data_ready)
        self.buyin.api_finished.connect(self._on_api_finished)
        self.buyin.error_occurred.connect(self._on_error)
        
        # 本地头像加载
        self.avatar_loaded.connect(lambda p: self.avatar_label.setPixmap(p))

        # 面板状态消息
        self.voice_panel.status_message.connect(self.status_bar.showMessage)

    def _update_ui_state(self):
        is_open = self.is_browser_open
        self.login_btn.setText("🚪 退出登录" if is_open else "🚀 授权登录")
        self.warning_label.setVisible(is_open)
        
        logged_in = self.ewid is not None
        
        if not logged_in:
            self.account_label.setText("未登录")
            self.avatar_label.clear()
            self.live_status_label.setText("直播状态: 需先登录")
            # 如果当前在受限页，退回到语音识别页
            if self.sidebar.currentRow() > 0:
                self.sidebar.setCurrentRow(0)
        
        # 只有登录后才启用回复和弹幕配置，并显式置灰
        for i in [1, 2]:
            item = self.sidebar.item(i)
            if logged_in:
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            else:
                item.setFlags(Qt.NoItemFlags) # 这会使 item 变为 disabled 状态

    def _on_nav_changed(self, index):
        self.content_stack.setCurrentIndex(index)

    def _on_login_click(self):
        if not self.is_browser_open:
            self.buyin.start_browser()
        else:
            reply = QMessageBox.question(self, "确认退出", "确定退出并关闭浏览器？", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._logout()

    def _logout(self):
        self.monitor_timer.stop()
        if self.is_browser_open:
            self.buyin.close_browser()
        self.is_browser_open = False
        self.ewid = None
        self.is_live = False
        self._update_ui_state()

    def _on_monitor_tick(self):
        if not self.is_browser_open: return
        if not self.ewid:
            self.buyin.refresh_data()
        else:
            self.buyin.get_account_info(self.ewid)

    @Slot()
    def _on_browser_started(self):
        self.is_browser_open = True
        self._update_ui_state()
        self.monitor_timer.start(2000)

    @Slot()
    def _on_browser_closed(self):
        if self.is_browser_open:
            self.is_browser_open = False
            self._logout()
            # 延迟 100ms 弹出提示并退出，确保状态更新完成
            QTimer.singleShot(100, lambda: (
                QMessageBox.critical(self, "连接断开", "百应浏览器已关闭，为保证同步安全，程序将退出。"),
                QApplication.quit()
            ))

    @Slot(dict)
    def _on_data_ready(self, res):
        if res.get("ewid"):
            info = res["ewid"]
            self.ewid = info.get("fingerprint_id") or info.get("seraph_did")
            self.buyin.get_account_info(self.ewid)
        elif self.ewid:
            self.ewid = None
            self._update_ui_state()

    @Slot(str, dict)
    def _on_api_finished(self, tag, res):
        if tag == "ACCOUNT_INFO":
            data = res.get("data")
            if data and data.get("nickname"):
                if self.monitor_timer.interval() == 2000:
                    self.monitor_timer.setInterval(10000)
                
                self.account_label.setText(data['nickname'])
                if data.get("avatar"):
                    self._async_load_avatar(data["avatar"])
                
                self.buyin.get_live_status(self.ewid)
                self.reply_panel.set_ewid(self.ewid)
                self._update_ui_state()
            else:
                self.ewid = None
                self._update_ui_state()

        elif tag == "LIVE_STATUS":
            d = res.get("data", {})
            self.is_live = bool(d.get("room_id") and d.get("room_create_time"))
            if self.is_live:
                dt = datetime.fromtimestamp(
                    d["room_create_time"], timezone(timedelta(hours=8))
                )
                self.live_status_label.setText(f"🟢 直播中 | 开播时间: {dt.strftime('%m-%d %H:%M:%S')}")
                self.live_status_label.setStyleSheet("color: green; font-weight: bold; margin-left: 10px;")
            else:
                self.live_status_label.setText("⚪️ 未开播")
                self.live_status_label.setStyleSheet("color: #86868b; margin-left: 10px;")
            
            # 同步信息给弹幕面板
            outer_id = res.get("data", {}).get("outer_id", "default")
            self.danmaku_panel.set_session_info(self.ewid, outer_id, self.is_live)

        elif tag == "GET_STATUS":
            self.reply_panel.update_intel_status(res.get("data", {}).get("switch", False))
        elif tag == "GET_RULES":
            self.reply_panel.update_rules(res.get("data", {}).get("auto_reply_list", []))
        elif tag == "SET_RULES":
            self.status_bar.showMessage("同步成功", 3000)
            self.buyin.get_auto_reply_rules(self.ewid)

    def _async_load_avatar(self, url):
        def _t():
            try:
                r = requests.get(url, timeout=5)
                img = QImage.fromData(r.content)
                if not img.isNull():
                    self.avatar_loaded.emit(QPixmap.fromImage(img))
            except: pass
        threading.Thread(target=_t, daemon=True).start()

    def _on_error(self, err):
        self.status_bar.showMessage(f"错误: {err}")

    def closeEvent(self, event):
        self.voice_panel.stop_all()
        self._logout()
        event.accept()
