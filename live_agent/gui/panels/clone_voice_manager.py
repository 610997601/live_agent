"""声音复刻管理对话框 —— 管理复刻素材。"""

import os
import time
import wave
import tempfile
import uuid
from pathlib import Path
import numpy as np
import sounddevice as sd
from PySide6.QtCore import Qt, QTimer, Slot, Signal
from PySide6.QtWidgets import (
    QDialog, QLineEdit, QVBoxLayout, QHBoxLayout, QMessageBox, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFileDialog, QWidget
)

from live_agent.gui.clone_voice_store import CloneVoiceStore, CloneVoice
from live_agent.gui.workers import CosUploadWorker

class CloneVoiceAddDialog(QDialog):
    """录制并添加一个新的声音复刻素材"""
    finished = Signal(CloneVoice)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("录制声音")
        self.setMinimumWidth(450)
        
        self._temp_path = None
        self._is_recording = False
        self._recorded_data = []
        self._stream = None
        self._recording_timer = QTimer(self)
        self._recording_timer.timeout.connect(self._update_status)
        self._start_time = 0
        self._sample_rate = 44100
        
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        layout.addWidget(QLabel("<b>声音名称:</b>"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: 我的主声音")
        layout.addWidget(self.name_edit)
        
        layout.addWidget(QLabel("<b>备注 (可选):</b>"))
        self.remark_edit = QLineEdit()
        self.remark_edit.setPlaceholderText("例如: 录制于 2026-05-26")
        layout.addWidget(self.remark_edit)
        
        # 录音控制
        btn_row = QHBoxLayout()
        self.rec_btn = QPushButton("🎤 开始录音")
        self.rec_btn.clicked.connect(self._start_record)
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_record)
        self.play_btn = QPushButton("▶ 试听")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._preview)
        
        btn_row.addWidget(self.rec_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.play_btn)
        layout.addLayout(btn_row)
        
        self.status_label = QLabel("准备录音... (请朗读一段文字，建议 10-30 秒)")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        # 确定/取消
        btns = QHBoxLayout()
        self.confirm_btn = QPushButton(" 确 定 ")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self._on_confirm)
        cancel_btn = QPushButton(" 取 消 ")
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(self.confirm_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _start_record(self):
        try:
            self._recorded_data = []
            self._is_recording = True
            self._start_time = time.time()
            
            # 探测
            from live_agent.gui.settings_dialog import get_audio_devices
            in_idx, _, _ = get_audio_devices()
            device_info = sd.query_devices(in_idx, 'input')
            self._sample_rate = int(device_info['default_samplerate'])

            self._stream = sd.InputStream(
                samplerate=self._sample_rate, channels=1, device=in_idx,
                callback=lambda i, f, t, s: self._recorded_data.append(i.copy())
            )
            self._stream.start()
            self.rec_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.play_btn.setEnabled(False)
            self.confirm_btn.setEnabled(False)
            self._recording_timer.start(100)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"录音启动失败: {e}")

    def _stop_record(self):
        self._is_recording = False
        self._recording_timer.stop()
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self.rec_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self._recorded_data:
            self._save_temp()
            self.play_btn.setEnabled(True)
            self.confirm_btn.setEnabled(True)
            self.status_label.setText(f"录音完成: {time.time() - self._start_time:.1f}s")
        else:
            self.status_label.setText("未检测到声音数据")

    def _update_status(self):
        dur = time.time() - self._start_time
        self.status_label.setText(f"正在录音: {dur:.1f}s (建议 10-30s)")
        if dur > 60: self._stop_record()

    def _save_temp(self):
        data = np.concatenate(self._recorded_data, axis=0)
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        self._temp_path = Path(path)
        with wave.open(str(self._temp_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self._sample_rate)
            wf.writeframes((data * 32767).astype(np.int16).tobytes())

    def _preview(self):
        if self._temp_path and self._temp_path.exists():
             import subprocess
             import platform
             if platform.system() == "Windows":
                 subprocess.Popen(["powershell", "-c", f"Add-Type -AssemblyName PresentationCore; $p = New-Object System.Windows.Media.MediaPlayer; $p.Open([Uri]'{self._temp_path.absolute().as_uri()}'); $p.Play(); Start-Sleep -s 10"])

    def _on_confirm(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入声音名称。")
            return
        
        # 启动上传
        self.confirm_btn.setEnabled(False)
        self.status_label.setText("正在上传至腾讯云 CDN...")
        
        self._uploader = CosUploadWorker(self._temp_path, prefix="voice-clones")
        self._uploader.finished.connect(self._on_upload_finished)
        self._uploader.start()

    def _on_upload_finished(self, url, md5, success, error):
        if success:
            voice = CloneVoice(
                name=self.name_edit.text().strip(),
                remark=self.remark_edit.text().strip(),
                cdn_url=url,
                md5=md5
            )
            # 删除临时文件
            if self._temp_path.exists(): self._temp_path.unlink()
            self.finished.emit(voice)
            self.accept()
        else:
            QMessageBox.critical(self, "上传失败", f"文件同步至 CDN 失败: {error}")
            self.confirm_btn.setEnabled(True)
            self.status_label.setText("上传失败，请重试。")

class CloneVoiceManagerDialog(QDialog):
    """声音复刻素材管理主弹窗"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("管理复刻声音")
        self.setMinimumSize(600, 500)
        self._store = CloneVoiceStore()
        self._init_ui()
        self._refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 顶部工具栏 (全局操作)
        top_bar = QHBoxLayout()
        self.add_btn = QPushButton("＋ 添加声音素材")
        self.add_btn.setMinimumHeight(35)
        self.add_btn.clicked.connect(self._on_add)
        
        self.import_btn = QPushButton("↓ 导入")
        self.import_btn.setMinimumHeight(35)
        self.import_btn.clicked.connect(self._on_import)
        
        self.export_btn = QPushButton("↑ 导出")
        self.export_btn.setMinimumHeight(35)
        self.export_btn.clicked.connect(self._on_export)
        
        top_bar.addWidget(self.add_btn)
        top_bar.addStretch()
        top_bar.addWidget(self.import_btn)
        top_bar.addWidget(self.export_btn)
        layout.addLayout(top_bar)
        
        # 表格 (仅显示数据)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["声音名称", "备注信息"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(38)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 200)
        
        # 选择变更时更新按钮状态
        self.table.itemSelectionChanged.connect(self._update_button_states)
        
        layout.addWidget(self.table)

        # 底部工具栏 (针对选中项的操作)
        bottom_bar = QHBoxLayout()
        self.preview_btn = QPushButton("▶ 试听素材")
        self.preview_btn.setMinimumHeight(35)
        self.preview_btn.clicked.connect(self._on_preview_clicked)
        
        self.redo_btn = QPushButton("↻ 重新录制")
        self.redo_btn.setMinimumHeight(35)
        self.redo_btn.clicked.connect(self._on_redo_clicked)
        
        self.delete_btn = QPushButton("✕ 删除声音")
        self.delete_btn.setMinimumHeight(35)
        self.delete_btn.setStyleSheet("color: #ff3b30;")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        
        bottom_bar.addWidget(self.preview_btn)
        bottom_bar.addWidget(self.redo_btn)
        bottom_bar.addWidget(self.delete_btn)
        bottom_bar.addStretch()
        layout.addLayout(bottom_bar)
        
        self._update_button_states()

    def _update_button_states(self):
        has_selection = len(self.table.selectedItems()) > 0
        self.preview_btn.setEnabled(has_selection)
        self.redo_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

    def _get_selected_voice(self) -> CloneVoice | None:
        row = self.table.currentRow()
        if row >= 0:
            voices = self._store.get_all()
            if row < len(voices):
                return voices[row]
        return None

    def _refresh(self):
        voices = self._store.get_all()
        self.table.setRowCount(len(voices))
        
        for i, v in enumerate(voices):
            name_item = QTableWidgetItem(v.name)
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(i, 0, name_item)
            
            remark_item = QTableWidgetItem(v.remark)
            remark_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(i, 1, remark_item)
        
        self._update_button_states()

    def _on_preview_clicked(self):
        voice = self._get_selected_voice()
        if voice and voice.cdn_url:
            self._on_preview(voice.cdn_url)

    def _on_redo_clicked(self):
        voice = self._get_selected_voice()
        if voice:
            self._on_redo(voice)

    def _on_delete_clicked(self):
        voice = self._get_selected_voice()
        if voice:
            self._on_delete(voice.id)

    def _on_preview(self, url):
        """试听 CDN 上的声音素材"""
        if not url: return
        import tempfile
        from pathlib import Path
        from live_agent.gui.workers import DownloadWorker
        
        # 下载到临时文件并播放
        temp_dest = Path(tempfile.gettempdir()) / f"preview_{uuid.uuid4().hex[:8]}.wav"
        self._dw = DownloadWorker(url, temp_dest)
        def _play(path, success, err):
            if success:
                import subprocess
                import platform
                if platform.system() == "Windows":
                    subprocess.Popen(["powershell", "-c", f"Add-Type -AssemblyName PresentationCore; $p = New-Object System.Windows.Media.MediaPlayer; $p.Open([Uri]'{Path(path).absolute().as_uri()}'); $p.Play(); Start-Sleep -s 15"])
        self._dw.finished.connect(_play)
        self._dw.start()

    def _on_redo(self, voice):
        """重录逻辑：打开添加弹窗并预填信息，成功后替换旧项"""
        dlg = CloneVoiceAddDialog(self)
        dlg.name_edit.setText(voice.name)
        dlg.remark_edit.setText(voice.remark)
        
        def _handle_finished(new_voice):
            # 保持原 ID 以便更新
            new_voice.id = voice.id
            self._store.update(new_voice)
            
        dlg.finished.connect(_handle_finished)
        if dlg.exec() == QDialog.Accepted:
            self._refresh()

    def _on_add(self):
        dlg = CloneVoiceAddDialog(self)
        dlg.finished.connect(lambda v: self._store.add(v))
        if dlg.exec() == QDialog.Accepted:
            self._refresh()

    def _on_delete(self, vid):
        if QMessageBox.question(self, "确认", "确定要删除这个声音吗？") == QMessageBox.Yes:
            self._store.delete(vid)
            self._refresh()

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入声音素材", "", "JSON Files (*.json)")
        if path:
            try:
                import json
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                count = self._store.import_data(data.get("voices", []))
                QMessageBox.information(self, "成功", f"成功导入 {count} 条声音素材。")
                self._refresh()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {e}")

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出声音素材", "clone_voices_export.json", "JSON Files (*.json)")
        if path:
            try:
                import json
                voices = [v.to_dict() for v in self._store.get_all()]
                data = {"version": 1, "voices": voices}
                Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                QMessageBox.information(self, "成功", "导出完成。")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")
