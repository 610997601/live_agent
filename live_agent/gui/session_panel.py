"""会话控制面板 —— 开始/停止按钮、识别文字显示、命中提示。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QSizePolicy,
)


class SessionPanel(QGroupBox):
    """直播会话控制区。"""

    def __init__(self, parent=None):
        super().__init__("会话控制", parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.start_btn = QPushButton("▶  开始识别")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setMinimumHeight(40)

        self.stop_btn = QPushButton("■  停止")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)

        self.status_label = QLabel("●  等待开始")
        self.status_label.setObjectName("statusLabel")

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.status_label)
        btn_row.addStretch()

        layout.addLayout(btn_row)

        layout.addWidget(QLabel("识别内容:"))

        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setMaximumHeight(70)
        self.text_display.setPlaceholderText(
            "点击「开始识别」后，此处将实时显示 ASR 识别结果..."
        )
        layout.addWidget(self.text_display)

        self.hit_label = QLabel("")
        self.hit_label.setObjectName("hitLabel")
        self.hit_label.setWordWrap(True)
        layout.addWidget(self.hit_label)

    def set_listening(self, active: bool) -> None:
        if active:
            self.status_label.setText("●  监听中...")
            self.status_label.setObjectName("statusActive")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.status_label.setText("●  等待开始")
            self.status_label.setObjectName("statusLabel")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def show_hit(self, keyword: str, reply: str, voice_name: str) -> None:
        self.hit_label.setText(
            f"最近命中: 「{keyword}」 → [{voice_name}] {reply}"
        )

    def update_current_text(self, history: str, active: str) -> None:
        """更新显示内容，由历史记录和当前正在识别的文字组成。"""
        full_text = history + active
        
        # 滑动窗口：如果总长度超过 5000，截断历史记录
        if len(full_text) > 5000:
            history = "..." + history[-4000:]
            full_text = history + active
            
        self.text_display.setPlainText(full_text)
        self.text_display.moveCursor(Qt.TextCursor.End)

    def clear(self) -> None:
        self.text_display.clear()
        self.hit_label.clear()
