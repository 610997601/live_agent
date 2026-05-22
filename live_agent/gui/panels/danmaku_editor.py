"""定时弹幕编辑对话框 —— 添加/编辑定时弹幕规则。"""

from PySide6.QtWidgets import (
    QDialog, QLineEdit, QDialogButtonBox, QVBoxLayout, QMessageBox, QLabel
)

class DanmakuEditor(QDialog):
    """模态对话框，用于添加或编辑一条定时弹幕规则。"""

    def __init__(self, parent=None, content="", interval=10):
        super().__init__(parent)
        self.setWindowTitle("编辑弹幕规则" if content else "添加弹幕规则")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(15)

        layout.addWidget(QLabel("<b>弹幕内容:</b>"))
        self.content_edit = QLineEdit()
        self.content_edit.setText(content)
        self.content_edit.setPlaceholderText("例如: 喜欢主播的点点关注")
        self.content_edit.setMinimumHeight(40)
        self.content_edit.setStyleSheet("font-size: 14px; padding: 8px;")
        layout.addWidget(self.content_edit)

        layout.addWidget(QLabel("<b>发送间隔 (秒):</b>"))
        self.interval_edit = QLineEdit()
        self.interval_edit.setText(str(interval))
        self.interval_edit.setPlaceholderText("例如: 10")
        self.interval_edit.setMinimumHeight(40)
        self.interval_edit.setStyleSheet("font-size: 14px; padding: 8px;")
        layout.addWidget(self.interval_edit)

        layout.addSpacing(10)
        buttons = QDialogButtonBox()
        save_btn = buttons.addButton(" 保 存 ", QDialogButtonBox.AcceptRole)
        save_btn.setObjectName("generateBtn")
        save_btn.setMinimumHeight(40)
        save_btn.setMinimumWidth(100)
        
        cancel_btn = buttons.addButton(" 取 消 ", QDialogButtonBox.RejectRole)
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setMinimumWidth(100)
        
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self) -> None:
        content = self.content_edit.text().strip()
        interval = self.interval_edit.text().strip()
        if not content:
            QMessageBox.warning(self, "提示", "内容不能为空。")
            return
        if not interval.isdigit() or int(interval) < 1:
            QMessageBox.warning(self, "提示", "间隔必须为正整数。")
            return
        self.accept()

    def get_data(self):
        return self.content_edit.text().strip(), int(self.interval_edit.text().strip())
