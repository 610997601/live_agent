"""GUI 应用入口 —— QApplication 初始化与全局样式表。"""

import sys

from PySide6.QtWidgets import QApplication

STYLESHEET = """
QMainWindow {
    background-color: #f5f5f7;
}

QGroupBox {
    font-size: 13px;
    font-weight: bold;
    color: #1d1d1f;
    border: 1px solid #d2d2d7;
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #0071e3;
}

QPushButton {
    border: 1px solid #c7c7cc;
    border-radius: 6px;
    padding: 6px 16px;
    background-color: #ffffff;
    color: #1d1d1f;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #f2f2f7;
    border-color: #0071e3;
    color: #0071e3;
}

QPushButton:pressed {
    background-color: #e5e5ea;
}

QPushButton:disabled {
    background-color: #f5f5f7;
    color: #aeaeb2;
    border-color: #e5e5ea;
}

QPushButton#startBtn {
    background-color: #34c759;
    color: #ffffff;
    border: none;
    font-size: 15px;
    font-weight: bold;
    padding: 8px 28px;
}

QPushButton#startBtn:hover {
    background-color: #30b350;
}

QPushButton#startBtn:pressed {
    background-color: #248a3d;
}

QPushButton#startBtn:disabled {
    background-color: #a5e8b8;
}

QPushButton#stopBtn {
    background-color: #ff3b30;
    color: #ffffff;
    border: none;
    font-size: 15px;
    font-weight: bold;
    padding: 8px 28px;
}

QPushButton#stopBtn:hover {
    background-color: #e0352b;
}

QPushButton#stopBtn:pressed {
    background-color: #c42b23;
}

QPushButton#stopBtn:disabled {
    background-color: #ff8a84;
}

QPushButton#toolBtn {
    border: 1px solid #c7c7cc;
    border-radius: 5px;
    padding: 5px 14px;
    background-color: #ffffff;
    font-size: 13px;
}

QPushButton#toolBtn:hover {
    background-color: #f2f2f7;
    border-color: #0071e3;
}

QPushButton#toolBtn:pressed {
    background-color: #e5e5ea;
}

QPushButton#generateBtn {
    border: 1px solid #0071e3;
    border-radius: 5px;
    padding: 5px 14px;
    background-color: #0071e3;
    color: #ffffff;
    font-size: 13px;
}

QPushButton#generateBtn:hover {
    background-color: #0077ed;
    border-color: #0077ed;
}

QPushButton#generateBtn:pressed {
    background-color: #005bb2;
    border-color: #005bb2;
}

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #d2d2d7;
    border-radius: 6px;
    gridline-color: #f2f2f7;
    font-size: 13px;
    outline: none;
}

QTableWidget::item {
    padding: 8px 10px;
    color: #1d1d1f;
}

QTableWidget::item:selected {
    background-color: #e5f1ff;
    color: #1d1d1f;
}

QTableWidget::item:alternate {
    background-color: #fafafa;
}

QTableWidget::item:hover {
    background-color: #f2f2f7;
}

QTableWidget::item:selected:hover {
    background-color: #d1e8ff;
}

QHeaderView::section {
    background-color: #f5f5f7;
    border: none;
    border-bottom: 1px solid #d2d2d7;
    padding: 8px 10px;
    font-weight: bold;
    font-size: 13px;
    color: #6e6e73;
}

QTextEdit, QLineEdit {
    border: 1px solid #c7c7cc;
    border-radius: 5px;
    padding: 6px 10px;
    background-color: #ffffff;
    font-size: 13px;
    selection-background-color: #0071e3;
}

QTextEdit:focus, QLineEdit:focus {
    border-color: #0071e3;
}

QComboBox {
    border: 1px solid #c7c7cc;
    border-radius: 5px;
    padding: 5px 10px;
    background-color: #ffffff;
    font-size: 13px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    selection-background-color: #e5f1ff;
    selection-color: #1d1d1f;
    outline: none;
    border: 1px solid #d2d2d7;
}

QComboBox:focus {
    border-color: #0071e3;
}

QComboBox::drop-down {
    border: none;
    padding-right: 6px;
}

QLabel {
    font-size: 13px;
    color: #1d1d1f;
}

QLabel#statusLabel {
    color: #8e8e93;
}

QLabel#statusActive {
    color: #34c759;
    font-weight: bold;
}

QLabel#hitLabel {
    color: #ff9f0a;
    font-weight: bold;
    font-size: 14px;
}

QStatusBar {
    background-color: #f0f0f2;
    border-top: 1px solid #d2d2d7;
    font-size: 12px;
    color: #6e6e73;
    padding: 4px 12px;
}

QDialog {
    background-color: #f5f5f7;
}
"""


def main():
    from live_agent.utils.logger import setup_logging
    setup_logging()

    # Windows 任务栏图标修复：让 Windows 识别这是一个独立的 App，而不是 Python 脚本
    import platform
    if platform.system() == "Windows":
        import ctypes
        myappid = 'hsuanyuen.buyinassistant.1.0' # 唯一 ID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    app.setApplicationName("直播助手-内测版")
    app.setOrganizationName("live_agent")
    app.setStyleSheet(STYLESHEET)

    from live_agent.gui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())
