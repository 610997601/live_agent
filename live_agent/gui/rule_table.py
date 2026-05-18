"""规则列表 —— QTableWidget 显示规则 + 工具栏按钮。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)


class RuleTable(QGroupBox):
    """规则列表与工具栏。"""

    add_clicked = Signal()
    edit_clicked = Signal(str)
    delete_clicked = Signal(str)
    generate_clicked = Signal()

    COL_STATUS = 0
    COL_KEYWORD = 1
    COL_REPLY = 2
    COL_VOICE = 3
    COL_RATE = 4

    VOICE_SHORT = {
        "zh-CN-XiaoxiaoNeural": "晓晓",
        "zh-CN-YunxiNeural": "云希",
        "zh-CN-YunyangNeural": "云扬",
        "zh-CN-XiaohanNeural": "晓涵",
        "zh-CN-XiaoyanNeural": "晓颜",
        "zh-CN-XiaoshuangNeural": "晓双",
        "zh-CN-XiaochenNeural": "晓辰",
    }

    def __init__(self, parent=None):
        super().__init__("规则列表", parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "状态", "关键词", "回复内容", "音色", "语速"
        ])
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(self.COL_STATUS, QHeaderView.Fixed)
        header.setSectionResizeMode(self.COL_KEYWORD, QHeaderView.Fixed)
        header.setSectionResizeMode(self.COL_REPLY, QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_VOICE, QHeaderView.Fixed)
        header.setSectionResizeMode(self.COL_RATE, QHeaderView.Fixed)
        self._table.setColumnWidth(self.COL_STATUS, 50)
        self._table.setColumnWidth(self.COL_KEYWORD, 100)
        self._table.setColumnWidth(self.COL_VOICE, 120)
        self._table.setColumnWidth(self.COL_RATE, 60)

        self._table.doubleClicked.connect(
            lambda idx: self._on_double_click(idx.row())
        )

        layout.addWidget(self._table)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.add_btn = QPushButton("＋ 添加")
        self.add_btn.setObjectName("toolBtn")
        self.edit_btn = QPushButton("✎ 编辑")
        self.edit_btn.setObjectName("toolBtn")
        self.delete_btn = QPushButton("✕ 删除")
        self.delete_btn.setObjectName("toolBtn")
        self.generate_btn = QPushButton("↻ 生成全部音频")
        self.generate_btn.setObjectName("generateBtn")

        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.generate_btn)

        layout.addLayout(toolbar)

        self.add_btn.clicked.connect(self.add_clicked.emit)
        self.edit_btn.clicked.connect(self._emit_edit)
        self.delete_btn.clicked.connect(self._emit_delete)
        self.generate_btn.clicked.connect(self.generate_clicked.emit)

        self._rule_ids: list[str] = []

    def _emit_edit(self) -> None:
        row = self._table.currentRow()
        if 0 <= row < len(self._rule_ids):
            self.edit_clicked.emit(self._rule_ids[row])

    def _emit_delete(self) -> None:
        row = self._table.currentRow()
        if 0 <= row < len(self._rule_ids):
            self.delete_clicked.emit(self._rule_ids[row])

    def _on_double_click(self, row: int) -> None:
        if 0 <= row < len(self._rule_ids):
            self.edit_clicked.emit(self._rule_ids[row])

    def refresh(self, rules: list, audio_manager) -> None:
        """根据规则列表刷新表格内容。"""
        self._rule_ids = [r.id for r in rules]
        self._table.setRowCount(len(rules))

        for row, rule in enumerate(rules):
            has_audio = audio_manager.has_audio(rule.id) if audio_manager else False
            status_item = QTableWidgetItem("✓" if has_audio else "○")
            status_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, self.COL_STATUS, status_item)

            self._table.setItem(row, self.COL_KEYWORD, QTableWidgetItem(rule.keyword))

            reply_text = rule.reply[:40] + "..." if len(rule.reply) > 40 else rule.reply
            self._table.setItem(row, self.COL_REPLY, QTableWidgetItem(reply_text))

            voice_name = self.VOICE_SHORT.get(rule.voice, rule.voice)
            self._table.setItem(row, self.COL_VOICE, QTableWidgetItem(voice_name))

            rate_item = QTableWidgetItem(rule.rate)
            rate_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, self.COL_RATE, rate_item)
