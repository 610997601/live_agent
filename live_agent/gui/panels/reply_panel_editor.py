"""关键词回复编辑器 —— 全量管理百应关键词回复规则。"""

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QMessageBox, QFileDialog, QLabel, QAbstractItemView
)
from live_agent.gui.panels.reply_sub_editor import ReplySubEditor

class KeywordEditorDialog(QDialog):
    """关键词回复全量编辑器。"""
    def __init__(self, current_rules, parent=None):
        super().__init__(parent)
        self.setWindowTitle("管理关键词回复规则")
        self.resize(900, 650)
        self.rules = current_rules
        self.final_rules = []
        self._init_ui()
        self._load_rules_to_table()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 24, 24, 24)
        
        desc = QLabel(
            "🔹 限制：关键词 ≤ 8字符 | 回复内容 ≤ 50字符 | 每条回复最多对应 10个关键词 | 总组数 1~50 组"
        )
        desc.setObjectName("statusLabel")
        desc.setStyleSheet("font-size: 11px;")
        layout.addWidget(desc)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["关键词 (多个用逗号分隔)", "回复内容"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 300)
        
        layout.addWidget(self.table)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        self.btn_add = QPushButton("＋ 添加")
        self.btn_add.setObjectName("toolBtn")
        self.btn_edit = QPushButton("✎ 编辑")
        self.btn_edit.setObjectName("toolBtn")
        self.btn_delete = QPushButton("✕ 删除")
        self.btn_delete.setObjectName("toolBtn")
        
        self.btn_import = QPushButton("📥 导入")
        self.btn_import.setObjectName("toolBtn")
        self.btn_export = QPushButton("📤 导出")
        self.btn_export.setObjectName("toolBtn")

        btn_box.addWidget(self.btn_add)
        btn_box.addWidget(self.btn_edit)
        btn_box.addWidget(self.btn_delete)
        btn_box.addStretch()
        btn_box.addWidget(self.btn_import)
        btn_box.addWidget(self.btn_export)
        layout.addLayout(btn_box)

        final_box = QHBoxLayout()
        final_box.setSpacing(15)
        self.btn_save = QPushButton("💾 保存并同步到云端")
        self.btn_save.setObjectName("generateBtn")
        self.btn_save.setMinimumHeight(40)
        
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setMinimumHeight(40)
        
        final_box.addStretch()
        final_box.addWidget(self.btn_cancel)
        final_box.addWidget(self.btn_save)
        layout.addLayout(final_box)

        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_import.clicked.connect(self._import_excel)
        self.btn_export.clicked.connect(self._export_excel)
        self.btn_save.clicked.connect(self._validate_and_accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.table.doubleClicked.connect(lambda idx: self._on_edit())

    def _load_rules_to_table(self):
        self.table.setRowCount(0)
        for rule in self.rules:
            self._add_row_data(", ".join(rule.get("keywords", [])), rule.get("content", ""))

    def _add_row_data(self, kw_str, content):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(kw_str))
        self.table.setItem(row, 1, QTableWidgetItem(content))

    def _on_add(self):
        if self.table.rowCount() >= 50:
            QMessageBox.warning(self, "上限提示", "关键词回复规则最多支持 50 组")
            return
        editor = ReplySubEditor(self)
        if editor.exec() == ReplySubEditor.Accepted:
            kw_str, content = editor.get_data()
            self._add_row_data(kw_str, content)

    def _on_edit(self):
        row = self.table.currentRow()
        if row < 0: return
        old_kw = self.table.item(row, 0).text()
        old_ct = self.table.item(row, 1).text()
        editor = ReplySubEditor(self, old_kw, old_ct)
        if editor.exec() == ReplySubEditor.Accepted:
            kw_str, content = editor.get_data()
            self.table.item(row, 0).setText(kw_str)
            self.table.item(row, 1).setText(content)

    def _on_delete(self):
        row = self.table.currentRow()
        if row < 0: return
        kw = self.table.item(row, 0).text()
        if QMessageBox.question(self, "确认删除", f"确定要删除规则「{kw}」吗？") == QMessageBox.Yes:
            self.table.removeRow(row)

    def _validate_and_accept(self):
        processed_rules = []
        for i in range(self.table.rowCount()):
            kw_text = self.table.item(i, 0).text().strip()
            content = self.table.item(i, 1).text().strip()
            kws = [k.strip() for k in kw_text.split(",") if k.strip()]
            processed_rules.append({"keywords": kws, "content": content})
        
        if not processed_rules:
            if QMessageBox.question(self, "确认清空", "规则列表为空，保存将清空云端所有规则，确定吗？") == QMessageBox.No:
                return

        self.final_rules = processed_rules
        self.accept()

    def _import_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入 Excel", "", "Excel Files (*.xlsx *.xls)")
        if not path: return
        try:
            df = pd.read_excel(path)
            data_map = {}
            for _, row in df.iterrows():
                kw, content = str(row.iloc[0]).strip(), str(row.iloc[1]).strip()
                if not kw or not content or kw == "nan" or content == "nan": continue
                if content not in data_map: data_map[content] = []
                data_map[content].append(kw)
            
            # 导入前询问是否清空
            if self.table.rowCount() > 0:
                rep = QMessageBox.question(self, "导入提示", "是否清空当前列表后再导入？", 
                                          QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                if rep == QMessageBox.Cancel: return
                if rep == QMessageBox.Yes: self.table.setRowCount(0)

            for content, all_kws in data_map.items():
                for i in range(0, len(all_kws), 10):
                    if self.table.rowCount() >= 50: break
                    self._add_row_data(", ".join(all_kws[i:i+10]), content)
        except Exception as e:
            QMessageBox.critical(self, "失败", f"导入出错: {e}")

    def _export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出 Excel", "关键词回复规则.xlsx", "Excel Files (*.xlsx)")
        if not path: return
        try:
            data = []
            for i in range(self.table.rowCount()):
                kw_item, ct_item = self.table.item(i, 0), self.table.item(i, 1)
                if not kw_item or not ct_item: continue
                for k in [k.strip() for k in kw_item.text().split(",") if k.strip()]:
                    data.append({"关键词": k, "回复内容": ct_item.text().strip()})
            pd.DataFrame(data).to_excel(path, index=False)
            QMessageBox.information(self, "成功", "导出成功")
        except Exception as e:
            QMessageBox.critical(self, "失败", f"导出出错: {e}")
