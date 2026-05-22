"""智能回复面板 —— 百应平台关键词回复配置。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from live_agent.gui.panels.reply_panel_editor import KeywordEditorDialog


class ReplyPanel(QWidget):
    """智能回复配置面板。"""

    def __init__(self, buyin, parent=None):
        super().__init__(parent)
        self.buyin = buyin
        self.ewid = None
        self.current_remote_rules = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 智能回复
        self.group_intel = QGroupBox("百应智能回复")
        self.group_intel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        l_intel = QVBoxLayout(self.group_intel)
        l_intel.setSpacing(8)

        desc = QLabel(
            "开启智能回复功能后，百应平台将识别“商品详情、尺码重量”等商品信息相关评论，结合商品详情页信息进行智能回复。如已对指定评论进行自定义回复设置，则该评论仍保持原有设置进行回复。"
        )
        desc.setWordWrap(True)
        desc.setObjectName("statusLabel")
        l_intel.addWidget(desc)

        self.intel_reply_sw = QCheckBox("开启智能回复功能")
        self.intel_reply_sw.clicked.connect(self._on_toggle_intel)
        l_intel.addWidget(self.intel_reply_sw)
        layout.addWidget(self.group_intel)

        # 关键词回复 (仅展示)
        self.group_kw = QGroupBox("回复列表 (云端)")
        l_kw = QVBoxLayout(self.group_kw)
        l_kw.setSpacing(8)

        self.kw_display_table = QTableWidget(0, 2)
        self.kw_display_table.setHorizontalHeaderLabels(["关键词", "回复内容"])
        self.kw_display_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.kw_display_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.kw_display_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.kw_display_table.setAlternatingRowColors(True)
        self.kw_display_table.setShowGrid(False)
        self.kw_display_table.verticalHeader().setVisible(False)
        self.kw_display_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        l_kw.addWidget(self.kw_display_table)

        toolbar = QHBoxLayout()
        self.btn_open_editor = QPushButton("✏️ 编辑关键词回复规则")
        self.btn_open_editor.setObjectName("generateBtn")
        self.btn_open_editor.setMinimumHeight(40)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_open_editor)
        l_kw.addLayout(toolbar)

        layout.addWidget(self.group_kw)

        self.btn_open_editor.clicked.connect(self._open_keyword_editor)

    def set_ewid(self, ewid):
        self.ewid = ewid
        if ewid:
            self.buyin.get_intelligent_reply_status(ewid)
            self.buyin.get_auto_reply_rules(ewid)

    def update_intel_status(self, enabled):
        self.intel_reply_sw.setChecked(enabled)

    def update_rules(self, rules):
        self.current_remote_rules = rules
        self.kw_display_table.setRowCount(0)
        for r in rules:
            row = self.kw_display_table.rowCount()
            self.kw_display_table.insertRow(row)
            self.kw_display_table.setItem(
                row, 0, QTableWidgetItem(", ".join(r["keywords"]))
            )
            self.kw_display_table.setItem(row, 1, QTableWidgetItem(r["content"]))

    def _on_toggle_intel(self):
        if self.ewid:
            self.buyin.set_intelligent_reply_status(
                self.ewid, self.intel_reply_sw.isChecked()
            )

    def _open_keyword_editor(self):
        dialog = KeywordEditorDialog(self.current_remote_rules, self)
        if dialog.exec() == KeywordEditorDialog.Accepted:
            self.buyin.set_auto_reply_rules(self.ewid, dialog.final_rules)
