"""关键词回复子编辑对话框 —— 用于全量编辑窗内的单条规则编辑。"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QMessageBox, QLabel
)

class ReplySubEditor(QDialog):
    """模态对话框，用于在全量编辑器中添加或编辑一条规则。"""

    def __init__(self, parent=None, keywords="", content=""):
        super().__init__(parent)
        self.setWindowTitle("编辑回复规则" if keywords else "添加回复规则")
        self.setMinimumWidth(650) 

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 20) # 减小左右边距
        layout.setSpacing(15)

        # 限制提示
        desc = QLabel(
            "🔹 限制：关键词 ≤ 8字符 | 回复内容 ≤ 50字符 | 每条回复最多 10个关键词"
        )
        desc.setObjectName("statusLabel")
        desc.setStyleSheet("font-size: 11px; margin-bottom: 5px;")
        layout.addWidget(desc)

        # 关键词部分
        layout.addWidget(QLabel("<b>关键词 (多个用英文逗号分隔):</b>"))
        self.keywords_edit = QTextEdit()
        self.keywords_edit.setPlainText(keywords)
        self.keywords_edit.setPlaceholderText("例如: 价格, 多少钱, 怎么卖")
        self.keywords_edit.setMinimumHeight(80)
        self.keywords_edit.setStyleSheet("font-size: 14px; padding: 8px;")
        layout.addWidget(self.keywords_edit)

        # 回复内容部分
        layout.addWidget(QLabel("<b>回复内容:</b>"))
        self.content_edit = QTextEdit()
        self.content_edit.setPlainText(content)
        self.content_edit.setPlaceholderText("请输入回复文案...")
        self.content_edit.setMinimumHeight(120)
        self.content_edit.setStyleSheet("font-size: 14px; padding: 8px;")
        layout.addWidget(self.content_edit)

        # 底部按钮
        buttons = QDialogButtonBox()
        save_btn = buttons.addButton(" 确 定 ", QDialogButtonBox.AcceptRole)
        save_btn.setObjectName("generateBtn")
        save_btn.setMinimumHeight(40)
        save_btn.setMinimumWidth(100)
        
        cancel_btn = buttons.addButton(" 取 消 ", QDialogButtonBox.RejectRole)
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setMinimumWidth(100)
        
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addSpacing(10)
        layout.addWidget(buttons)

    def _validate_and_accept(self) -> None:
        kw_text = self.keywords_edit.toPlainText().strip()
        content = self.content_edit.toPlainText().strip()
        if not kw_text or not content:
            QMessageBox.warning(self, "验证失败", "关键词和回复内容都不能为空。")
            return
        
        raw_kws = kw_text.replace("，", ",").split(",")
        kws = [k.strip() for k in raw_kws if k.strip()]
        
        if len(kws) == 0:
            QMessageBox.warning(self, "验证失败", "请输入有效的关键词。")
            return
            
        if len(kws) > 10:
            QMessageBox.warning(self, "验证失败", f"关键词数量过多 ({len(kws)}/10)。")
            return
            
        for k in kws:
            if len(k) > 8:
                QMessageBox.warning(self, "验证失败", f"关键词「{k}」太长(>8字)。")
                return
        
        if len(content) > 50:
            QMessageBox.warning(self, "验证失败", f"回复内容太长 ({len(content)}/50)。")
            return
            
        self.accept()

    def get_data(self):
        kw_text = self.keywords_edit.toPlainText().strip().replace("，", ",")
        kws = [k.strip() for k in kw_text.split(",") if k.strip()]
        content = self.content_edit.toPlainText().strip()
        return ", ".join(kws), content
