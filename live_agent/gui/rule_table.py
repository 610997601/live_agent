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
    enabled_toggled = Signal(str, bool)
    play_triggered = Signal(str)

    COL_ENABLED = 0
    COL_STATUS = 1
    COL_KEYWORD = 2
    COL_TYPE = 3
    COL_REPLY = 4
    COL_VOICE = 5
    COL_RATE = 6
    COL_PLAY = 7

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

        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels([
            "启用", "状态", "关键词", "类型", "回复内容", "音色", "语速", "试听"
        ])
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(38) # 增加默认行高，防止按钮被切掉
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(self.COL_ENABLED, QHeaderView.Fixed)
        header.setSectionResizeMode(self.COL_STATUS, QHeaderView.Fixed)
        header.setSectionResizeMode(self.COL_KEYWORD, QHeaderView.Fixed)
        header.setSectionResizeMode(self.COL_TYPE, QHeaderView.Fixed)
        header.setSectionResizeMode(self.COL_REPLY, QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_VOICE, QHeaderView.Fixed)
        header.setSectionResizeMode(self.COL_RATE, QHeaderView.Fixed)
        header.setSectionResizeMode(self.COL_PLAY, QHeaderView.Fixed)
        
        self._table.setColumnWidth(self.COL_ENABLED, 50)
        self._table.setColumnWidth(self.COL_STATUS, 50)
        self._table.setColumnWidth(self.COL_KEYWORD, 100)
        self._table.setColumnWidth(self.COL_TYPE, 60)
        self._table.setColumnWidth(self.COL_VOICE, 100)
        self._table.setColumnWidth(self.COL_RATE, 60)
        self._table.setColumnWidth(self.COL_PLAY, 110)

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
            # --- 启用开关 ---
            from PySide6.QtWidgets import QCheckBox, QWidget
            cb_container = QWidget()
            cb_layout = QHBoxLayout(cb_container)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb = QCheckBox()
            cb.setChecked(getattr(rule, "enabled", True))
            cb.toggled.connect(lambda checked, rid=rule.id: self.enabled_toggled.emit(rid, checked))
            cb_layout.addWidget(cb)
            self._table.setCellWidget(row, self.COL_ENABLED, cb_container)

            # --- 状态 ---
            has_audio = audio_manager.has_audio(rule.id) if audio_manager else False
            status_item = QTableWidgetItem("✓" if has_audio else "○")
            status_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, self.COL_STATUS, status_item)

            self._table.setItem(row, self.COL_KEYWORD, QTableWidgetItem(rule.keyword))

            reply_type = getattr(rule, "reply_type", "tts")
            type_text = "智能" if reply_type == "tts" else "录音"
            type_item = QTableWidgetItem(type_text)
            type_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, self.COL_TYPE, type_item)

            reply_text = rule.reply[:40] + "..." if len(rule.reply) > 40 else rule.reply
            self._table.setItem(row, self.COL_REPLY, QTableWidgetItem(reply_text))

            if reply_type == "record":
                voice_item = QTableWidgetItem("--")
                rate_item = QTableWidgetItem("--")
            else:
                voice_name = self.VOICE_SHORT.get(rule.voice, rule.voice)
                voice_item = QTableWidgetItem(voice_name)
                rate_item = QTableWidgetItem(rule.rate)

            voice_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, self.COL_VOICE, voice_item)

            rate_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, self.COL_RATE, rate_item)

            # --- 试听按钮 ---
            play_container = QWidget()
            play_layout = QHBoxLayout(play_container)
            play_layout.setContentsMargins(0, 0, 0, 0)
            play_layout.setAlignment(Qt.AlignCenter)
            
            play_btn = QPushButton("▶ 试听音频")
            # 使用文字链接形式，避免边框导致的裁剪问题
            play_btn.setCursor(Qt.PointingHandCursor)
            play_btn.setStyleSheet("""
                QPushButton {
                    color: #0071e3;
                    border: none;
                    background: transparent;
                    font-size: 13px;
                    font-weight: 500;
                    padding: 0px;
                }
                QPushButton:hover {
                    color: #005bb2;
                    text-decoration: underline;
                }
                QPushButton:disabled {
                    color: #aeaeb2;
                    text-decoration: none;
                }
            """)
            play_btn.setEnabled(has_audio)
            play_btn.clicked.connect(lambda _, rid=rule.id: self.play_triggered.emit(rid))
            play_layout.addWidget(play_btn)
            self._table.setCellWidget(row, self.COL_PLAY, play_container)
