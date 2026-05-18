"""规则编辑对话框 —— 添加/编辑关键词触发规则。"""

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QTextEdit, QComboBox,
    QDialogButtonBox, QVBoxLayout, QMessageBox,
)

VOICES = [
    ("zh-CN-XiaoxiaoNeural", "晓晓 (活泼温暖女声)"),
    ("zh-CN-YunxiNeural", "云希 (阳光有冲劲男声)"),
    ("zh-CN-YunyangNeural", "云扬 (专业沉稳男声)"),
    ("zh-CN-XiaohanNeural", "晓涵 (温暖甜美女生)"),
    ("zh-CN-XiaoyanNeural", "晓颜 (客服口吻女声)"),
    ("zh-CN-XiaoshuangNeural", "晓双 (可爱女生)"),
    ("zh-CN-XiaochenNeural", "晓辰 (自然女声)"),
]

RATE_OPTIONS = [
    "-50%", "-30%", "-20%", "-10%", "+0%",
    "+10%", "+20%", "+30%", "+50%", "+100%",
]


class RuleEditor(QDialog):
    """模态对话框，用于添加或编辑一条规则。"""

    def __init__(self, parent=None, rule=None):
        super().__init__(parent)
        self._rule = rule
        is_edit = rule is not None
        self.setWindowTitle("编辑规则" if is_edit else "添加规则")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("例如: 上架")
        form.addRow("关键词:", self.keyword_edit)

        self.reply_edit = QTextEdit()
        self.reply_edit.setPlaceholderText("例如: 货品已经上架了，大家快抢啊")
        self.reply_edit.setMaximumHeight(80)
        form.addRow("回复文案:", self.reply_edit)

        self.voice_combo = QComboBox()
        for value, label in VOICES:
            self.voice_combo.addItem(label, value)
        form.addRow("语音音色:", self.voice_combo)

        self.rate_combo = QComboBox()
        self.rate_combo.addItems(RATE_OPTIONS)
        self.rate_combo.setCurrentText("+0%")
        form.addRow("语速:", self.rate_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox()
        buttons.addButton("保存", QDialogButtonBox.AcceptRole)
        buttons.addButton("取消", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if is_edit:
            self._populate(rule)

    def _populate(self, rule) -> None:
        self.keyword_edit.setText(rule.keyword)
        self.reply_edit.setPlainText(rule.reply)
        idx = self.voice_combo.findData(rule.voice)
        if idx >= 0:
            self.voice_combo.setCurrentIndex(idx)
        rate_idx = self.rate_combo.findText(rule.rate)
        if rate_idx >= 0:
            self.rate_combo.setCurrentIndex(rate_idx)

    def _validate_and_accept(self) -> None:
        keyword = self.keyword_edit.text().strip()
        reply = self.reply_edit.toPlainText().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "关键词不能为空。")
            return
        if not reply:
            QMessageBox.warning(self, "提示", "回复文案不能为空。")
            return
        self.accept()

    def get_rule(self):
        from live_agent.gui.rule_store import Rule
        rule_id = self._rule.id if self._rule else None
        return Rule(
            id=rule_id or Rule().id,
            keyword=self.keyword_edit.text().strip(),
            reply=self.reply_edit.toPlainText().strip(),
            voice=self.voice_combo.currentData(),
            rate=self.rate_combo.currentText(),
        )
