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
    background-color: #e8e8ed;
}

QPushButton:pressed {
    background-color: #d2d2d7;
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
    background-color: #e8e8ed;
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
}

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #d2d2d7;
    border-radius: 6px;
    gridline-color: transparent;
    font-size: 13px;
}

QTableWidget::item {
    padding: 6px 10px;
}

QTableWidget::item:selected {
    background-color: #0071e3;
    color: #ffffff;
}

QTableWidget::item:alternate {
    background-color: #f9f9fb;
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
    app = QApplication(sys.argv)
    app.setApplicationName("直播语音助手")
    app.setOrganizationName("live_agent")
    app.setStyleSheet(STYLESHEET)

    from live_agent.gui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())
