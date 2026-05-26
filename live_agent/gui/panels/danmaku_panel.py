"""定时弹幕面板 —— 本地持久化定时循环弹幕。"""

from datetime import datetime
import pandas as pd
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QMessageBox,
    QFileDialog, QGroupBox, QSizePolicy, QAbstractItemView
)
from live_agent.utils import ConfigManager
from live_agent.gui.panels.danmaku_editor import DanmakuEditor

class DanmakuPanel(QWidget):
    """定时弹幕面板。"""
    def __init__(self, buyin, parent=None):
        super().__init__(parent)
        self.buyin = buyin
        self.ewid = None
        self.config = None
        self.is_live = False
        
        # 定时执行逻辑
        self.danmu_exec_timer = QTimer(self)
        self.danmu_exec_timer.setInterval(1000)
        self.danmu_exec_timer.timeout.connect(self._on_timer_tick)
        self.danmu_last_sent = {} # {content: timestamp}

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. 手动发送区
        self.group_manual = QGroupBox("会话控制")
        self.group_manual.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        l_manual = QVBoxLayout(self.group_manual)
        l_manual.setSpacing(8)
        
        from PySide6.QtWidgets import QLineEdit
        manual_row = QHBoxLayout()
        self.dm_manual_in = QLineEdit()
        self.dm_manual_in.setPlaceholderText("手动发送一条弹幕...")
        self.dm_manual_in.setMinimumHeight(40)
        
        self.btn_send = QPushButton("▶  发送")
        self.btn_send.setObjectName("startBtn")
        self.btn_send.setMinimumHeight(40)
        
        manual_row.addWidget(self.dm_manual_in)
        manual_row.addWidget(self.btn_send)
        l_manual.addLayout(manual_row)
        layout.addWidget(self.group_manual)

        # 2. 定时规则区
        self.group_auto = QGroupBox("弹幕列表")
        l_auto = QVBoxLayout(self.group_auto)
        l_auto.setSpacing(8)

        self.danmu_table = QTableWidget(0, 3)
        self.danmu_table.setHorizontalHeaderLabels(["启用", "弹幕内容", "间隔(秒)"])
        self.danmu_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.danmu_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.danmu_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.danmu_table.setAlternatingRowColors(True)
        self.danmu_table.setShowGrid(False)
        self.danmu_table.verticalHeader().setVisible(False)
        
        header = self.danmu_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.danmu_table.setColumnWidth(0, 50)
        self.danmu_table.setColumnWidth(2, 80)
        
        l_auto.addWidget(self.danmu_table)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        
        self.add_btn = QPushButton("＋ 添加")
        self.add_btn.setObjectName("toolBtn")
        self.edit_btn = QPushButton("✎ 编辑")
        self.edit_btn.setObjectName("toolBtn")
        self.delete_btn = QPushButton("✕ 删除")
        self.delete_btn.setObjectName("toolBtn")
        
        self.import_btn = QPushButton("📥 导入")
        self.import_btn.setObjectName("toolBtn")
        self.export_btn = QPushButton("📤 导出")
        self.export_btn.setObjectName("toolBtn")
        
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.import_btn)
        toolbar.addWidget(self.export_btn)
        l_auto.addLayout(toolbar)
        
        layout.addWidget(self.group_auto)

        # 信号绑定
        self.btn_send.clicked.connect(self._send_dm_manual)
        self.add_btn.clicked.connect(self._on_add)
        self.edit_btn.clicked.connect(self._on_edit)
        self.delete_btn.clicked.connect(self._on_delete)
        self.import_btn.clicked.connect(self._import_danmu)
        self.export_btn.clicked.connect(self._export_danmu)
        self.danmu_table.doubleClicked.connect(lambda idx: self._on_edit())

    def set_session_info(self, ewid, outer_id, is_live):
        self.ewid = ewid
        self.is_live = is_live
        if outer_id:
            self.config = ConfigManager(outer_id)
            self._load_local_rules()
            self.danmu_exec_timer.start()
        else:
            self.danmu_exec_timer.stop()

    def _load_local_rules(self):
        if not self.config: return
        rules = self.config.load_danmu_rules()
        self.danmu_table.setRowCount(0)
        for r in rules:
            self._add_row_to_table(r.get("enabled", False), r.get("content", ""), r.get("interval", 10))

    def _on_add(self):
        editor = DanmakuEditor(self)
        if editor.exec() == DanmakuEditor.Accepted:
            content, interval = editor.get_data()
            self._add_row_to_table(False, content, interval)
            self._save_local_rules()

    def _on_edit(self):
        row = self.danmu_table.currentRow()
        if row < 0: return
        old_content = self.danmu_table.item(row, 1).text()
        old_interval = int(self.danmu_table.item(row, 2).text())
        editor = DanmakuEditor(self, old_content, old_interval)
        if editor.exec() == DanmakuEditor.Accepted:
            content, interval = editor.get_data()
            self.danmu_table.item(row, 1).setText(content)
            self.danmu_table.item(row, 2).setText(str(interval))
            self._save_local_rules()

    def _on_delete(self):
        row = self.danmu_table.currentRow()
        if row < 0: return
        content = self.danmu_table.item(row, 1).text()
        
        msg = QMessageBox(self)
        msg.setWindowTitle("确认删除")
        msg.setText(f"确定要删除弹幕「{content}」吗？")
        msg.setIcon(QMessageBox.Question)
        yes_btn = msg.addButton("是", QMessageBox.YesRole)
        no_btn = msg.addButton("否", QMessageBox.NoRole)
        msg.setDefaultButton(no_btn)
        msg.exec()
        
        if msg.clickedButton() == yes_btn:
            self.danmu_table.removeRow(row)
            self._save_local_rules()

    def _add_row_to_table(self, enabled, content, interval):
        row = self.danmu_table.rowCount()
        self.danmu_table.insertRow(row)
        cb = QCheckBox()
        cb.setChecked(enabled)
        cb.clicked.connect(self._save_local_rules)
        self.danmu_table.setCellWidget(row, 0, cb)
        
        content_item = QTableWidgetItem(content)
        self.danmu_table.setItem(row, 1, content_item)
        
        interval_item = QTableWidgetItem(str(interval))
        interval_item.setTextAlignment(Qt.AlignCenter)
        self.danmu_table.setItem(row, 2, interval_item)

    def _save_local_rules(self):
        if not self.config: return
        rules = []
        for i in range(self.danmu_table.rowCount()):
            cb = self.danmu_table.cellWidget(i, 0)
            ct = self.danmu_table.item(i, 1)
            it = self.danmu_table.item(i, 2)
            if cb and ct and it:
                rules.append({"enabled": cb.isChecked(), "content": ct.text(), "interval": int(it.text())})
        self.config.save_danmu_rules(rules)

    def _on_timer_tick(self):
        if not self.ewid or not self.is_live: return
        now = datetime.now().timestamp()
        for i in range(self.danmu_table.rowCount()):
            cb = self.danmu_table.cellWidget(i, 0)
            if cb and cb.isChecked():
                content = self.danmu_table.item(i, 1).text()
                interval = int(self.danmu_table.item(i, 2).text())
                last = self.danmu_last_sent.get(content, 0)
                if now - last >= interval:
                    self.buyin.send_danmu(self.ewid, content)
                    self.danmu_last_sent[content] = now

    def _send_dm_manual(self):
        txt = self.dm_manual_in.text().strip()
        if txt and self.ewid:
            if not self.is_live:
                QMessageBox.warning(self, "提示", "仅直播中可发送弹幕")
                return
            self.buyin.send_danmu(self.ewid, txt)
            self.dm_manual_in.clear()

    def _import_danmu(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入弹幕", "", "Excel Files (*.xlsx *.xls)")
        if not path: return
        try:
            df = pd.read_excel(path)
            for _, row in df.iterrows():
                ct, it = str(row.iloc[0]).strip(), str(row.iloc[1]).strip()
                if ct and it.isdigit():
                    self._add_row_to_table(False, ct, it)
            self._save_local_rules()
        except Exception as e:
            QMessageBox.critical(self, "出错", str(e))

    def _export_danmu(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出弹幕", "定时弹幕规则.xlsx", "Excel Files (*.xlsx)")
        if not path: return
        try:
            data = []
            for i in range(self.danmu_table.rowCount()):
                data.append({"弹幕内容": self.danmu_table.item(i, 1).text(), "间隔(秒)": self.danmu_table.item(i, 2).text()})
            pd.DataFrame(data).to_excel(path, index=False)
            QMessageBox.information(self, "成功", "导出成功")
        except Exception as e:
            QMessageBox.critical(self, "出错", str(e))
