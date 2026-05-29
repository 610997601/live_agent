"""规则编辑对话框 —— 添加/编辑关键词触发规则。"""

import os
import time
import wave
import tempfile
import uuid
import shutil
from pathlib import Path
import numpy as np
import sounddevice as sd
from PySide6.QtCore import Qt, QTimer, Slot, Signal
from PySide6.QtWidgets import (
    QDialog, QLineEdit, QTextEdit, QComboBox,
    QDialogButtonBox, QVBoxLayout, QHBoxLayout, QMessageBox, QLabel,
    QPushButton, QStackedWidget, QWidget, QProgressBar
)

from live_agent.gui.clone_voice_store import CloneVoiceStore
from live_agent.gui.panels.clone_voice_manager import CloneVoiceManagerDialog
from live_agent.gui.workers import AudioGenWorker, VoiceCloneApiWorker, CosUploadWorker, DownloadWorker
from live_agent.gui.audio_manager import AudioManager
from live_agent.utils import GlobalConfig

RATE_OPTIONS = [
    "-50%", "-30%", "-20%", "-10%", "+0%",
    "+10%", "+20%", "+30%", "+50%", "+100%",
]

class RuleEditor(QDialog):
    """模态对话框，用于添加或编辑一条规则。"""

    def __init__(self, parent=None, rule=None):
        super().__init__(parent)
        self._rule = rule
        self._audio_mgr = AudioManager()
        self._voice_store = CloneVoiceStore()
        
        # 当前编辑中的音频状态
        self._current_audio_path = None
        self._current_cdn_url = rule.cdn_url if rule else ""
        self._current_md5 = rule.audio_md5 if rule else ""
        
        # 录音相关
        self._is_recording = False
        self._recorded_data = []
        self._stream = None
        self._recording_timer = QTimer(self)
        self._recording_timer.timeout.connect(self._update_record_status)
        self._recording_start_time = 0
        self._sample_rate = 44100

        is_edit = rule is not None
        self.setWindowTitle("编辑规则" if is_edit else "添加规则")
        self.setMinimumWidth(650)

        self._init_ui()
        if is_edit:
            self._populate(rule)
        else:
            self._update_save_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(QLabel("<b>触发关键词:</b>"))
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("例如: 上架")
        self.keyword_edit.setMinimumHeight(40)
        layout.addWidget(self.keyword_edit)

        layout.addWidget(QLabel("<b>回复文案:</b>"))
        self.reply_edit = QTextEdit()
        self.reply_edit.setPlaceholderText("例如: 货品已经上架了，大家快抢啊")
        self.reply_edit.setMinimumHeight(80)
        layout.addWidget(self.reply_edit)

        # 回复方式选择
        layout.addWidget(QLabel("<b>回复方式:</b>"))
        self.type_combo = QComboBox()
        self.type_combo.setMinimumHeight(40)
        self.type_combo.addItem("智能生成 (TTS)", "tts")
        self.type_combo.addItem("现场录音", "record")
        self.type_combo.addItem("声音复刻", "clone")
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addWidget(self.type_combo)

        # 堆栈窗口
        self.stack = QStackedWidget()
        
        # --- 1. TTS 面板 ---
        self.tts_panel = QWidget()
        tts_layout = QVBoxLayout(self.tts_panel)
        tts_layout.setContentsMargins(0, 0, 0, 0)
        
        tts_layout.addWidget(QLabel("语音音色:"))
        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumHeight(35)
        voices = GlobalConfig.get_voices()
        for v in voices:
            short_name = v.get("ShortName", "")
            gender = "女声" if v.get("Gender") == "Female" else "男声"
            core_id = short_name.split("-")[-1].replace("Neural", "")
            mapping = {"Xiaoxiao": "晓晓", "Xiaoyi": "晓伊", "Yunxi": "云希", "Yunyang": "云扬", "Yunjian": "云健"}
            display_name = f"{mapping.get(core_id, core_id)} ({gender})"
            self.voice_combo.addItem(display_name, short_name)
        tts_layout.addWidget(self.voice_combo)

        tts_layout.addWidget(QLabel("语音语速:"))
        self.rate_combo = QComboBox()
        self.rate_combo.addItems(RATE_OPTIONS)
        self.rate_combo.setCurrentText("+0%")
        tts_layout.addWidget(self.rate_combo)
        
        self.tts_gen_btn = QPushButton("✨ 生成语音")
        self.tts_gen_btn.setMinimumHeight(40)
        self.tts_gen_btn.clicked.connect(self._generate_tts)
        tts_layout.addWidget(self.tts_gen_btn)
        self.stack.addWidget(self.tts_panel)

        # --- 2. 录音面板 ---
        self.record_panel = QWidget()
        rec_layout = QVBoxLayout(self.record_panel)
        rec_layout.setContentsMargins(0, 0, 0, 0)
        btn_row = QHBoxLayout()
        self.rec_btn = QPushButton("🎤 开始录音")
        self.rec_btn.clicked.connect(self._start_record)
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_record)
        btn_row.addWidget(self.rec_btn)
        btn_row.addWidget(self.stop_btn)
        rec_layout.addLayout(btn_row)
        self.status_label = QLabel("录音完成后将自动同步至云端。")
        rec_layout.addWidget(self.status_label)
        self.stack.addWidget(self.record_panel)

        # --- 3. 声音复刻面板 ---
        self.clone_panel = QWidget()
        clo_layout = QVBoxLayout(self.clone_panel)
        clo_layout.setContentsMargins(0, 0, 0, 0)
        
        clo_layout.addWidget(QLabel("选择复刻底噪:"))
        clo_row = QHBoxLayout()
        self.clone_voice_combo = QComboBox()
        self.clone_voice_combo.setMinimumHeight(35)
        self._refresh_clone_voices()
        
        manage_clo_btn = QPushButton("管理声音")
        manage_clo_btn.clicked.connect(self._on_manage_clone_voices)
        
        clo_row.addWidget(self.clone_voice_combo, stretch=1)
        clo_row.addWidget(manage_clo_btn)
        clo_layout.addLayout(clo_row)
        
        self.clone_gen_btn = QPushButton("🚀 开始复刻生成")
        self.clone_gen_btn.setMinimumHeight(40)
        self.clone_gen_btn.clicked.connect(self._generate_clone)
        clo_layout.addWidget(self.clone_gen_btn)
        self.stack.addWidget(self.clone_panel)

        layout.addWidget(self.stack)

        # 试听和进度
        preview_row = QHBoxLayout()
        self.play_btn = QPushButton("▶ 试听当前生成结果")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._preview_audio)
        preview_row.addWidget(self.play_btn)
        layout.addLayout(preview_row)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 底部按钮
        layout.addSpacing(10)
        self.button_box = QDialogButtonBox()
        self.save_btn = self.button_box.addButton(" 保 存 ", QDialogButtonBox.AcceptRole)
        self.save_btn.setEnabled(False)
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setMinimumWidth(100)
        
        cancel_btn = self.button_box.addButton(" 取 消 ", QDialogButtonBox.RejectRole)
        cancel_btn.setMinimumHeight(40)
        self.button_box.accepted.connect(self._on_save_clicked)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _refresh_clone_voices(self):
        self.clone_voice_combo.clear()
        voices = self._voice_store.get_all()
        for v in voices:
            self.clone_voice_combo.addItem(v.name, v.cdn_url)

    def _on_manage_clone_voices(self):
        dlg = CloneVoiceManagerDialog(self)
        dlg.exec()
        self._refresh_clone_voices()

    def _on_type_changed(self, index):
        self.stack.setCurrentIndex(index)
        self._update_save_status()

    def _update_save_status(self):
        # 回复方式对应的音频是否已就绪
        is_ready = False
        if self._current_audio_path and Path(self._current_audio_path).exists():
            # record 模式在点击保存时才同步 COS，TTS/Clone 必须已经有 CDN 地址
            rtype = self.type_combo.currentData()
            if rtype == "record":
                is_ready = True
            else:
                is_ready = bool(self._current_cdn_url)
        
        self.save_btn.setEnabled(is_ready)
        self.play_btn.setEnabled(bool(self._current_audio_path))

    def _populate(self, rule):
        self.keyword_edit.setText(rule.keyword)
        self.reply_edit.setPlainText(rule.reply)
        idx = self.type_combo.findData(rule.reply_type)
        if idx >= 0: self.type_combo.setCurrentIndex(idx)
        
        # 加载已有音频
        path = self._audio_mgr.audio_path(rule.id)
        if path.exists():
            self._current_audio_path = str(path)
        
        self._update_save_status()

    # --- 逻辑: TTS 生成 ---
    def _generate_tts(self):
        text = self.reply_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请填写回复文案。")
            return
            
        # 清理该规则之前的旧临时文件
        self._cleanup_temp_files()

        self.tts_gen_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        # 1. 生成本地文件，存放在物理隔离的 temp 目录
        temp_id = uuid.uuid4().hex[:8]
        dest_path = self._audio_mgr._temp_dir / f"tts_{temp_id}.mp3"
        
        from live_agent.tts import EdgeTTS
        self._tts_worker = AudioGenWorker(
            rules=[{"id": f"tts_{temp_id}", "reply": text, "voice": self.voice_combo.currentData(), "rate": self.rate_combo.currentText()}],
            tts=EdgeTTS(),
            audio_dir=self._audio_mgr._temp_dir
        )
        
        def on_done(rid):
            # 2. 上传到 COS
            self._uploader = CosUploadWorker(dest_path)
            self._uploader.finished.connect(lambda u, m, s, e: self._on_tts_upload_finished(u, m, s, e, str(dest_path)))
            self._uploader.start()

        self._tts_worker.rule_done.connect(on_done)
        self._tts_worker.start()

    def _on_tts_upload_finished(self, url, md5, success, error, local_path):
        self.progress_bar.setVisible(False)
        self.tts_gen_btn.setEnabled(True)
        if success:
            self._current_cdn_url = url
            self._current_md5 = md5
            self._current_audio_path = local_path
            self._update_save_status()
            QMessageBox.information(self, "成功", "TTS 语音生成并同步成功。")
        else:
            QMessageBox.critical(self, "失败", f"同步至云端失败: {error}")

    def _cleanup_temp_files(self):
        """物理删除 temp 文件夹下的所有临时文件"""
        if self._audio_mgr._temp_dir.exists():
            for p in self._audio_mgr._temp_dir.iterdir():
                if p.is_file():
                    try: p.unlink()
                    except: pass

    # --- 逻辑: 录音 ---
    def _start_record(self):
        self._recorded_data = []
        self._is_recording = True
        self._recording_start_time = time.time()
        from live_agent.gui.settings_dialog import get_audio_devices
        in_idx, _, _ = get_audio_devices()
        device_info = sd.query_devices(in_idx, 'input')
        self._sample_rate = int(device_info['default_samplerate'])
        self._stream = sd.InputStream(samplerate=self._sample_rate, channels=1, device=in_idx,
                                      callback=lambda i,f,t,s: self._recorded_data.append(i.copy()))
        self._stream.start()
        self.rec_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._recording_timer.start(100)

    def _stop_record(self):
        self._is_recording = False
        self._recording_timer.stop()
        if self._stream:
            self._stream.stop(); self._stream.close(); self._stream = None
        self.rec_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self._recorded_data:
            data = np.concatenate(self._recorded_data, axis=0)
            # 录音也存放在 temp 目录
            temp_id = uuid.uuid4().hex[:8]
            path = self._audio_mgr._temp_dir / f"rec_{temp_id}.wav"
            self._current_audio_path = str(path)
            with wave.open(str(path), "wb") as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(self._sample_rate)
                wf.writeframes((data * 32767).astype(np.int16).tobytes())
            self._update_save_status()

    def _update_record_status(self):
        self.status_label.setText(f"正在录音: {time.time()-self._recording_start_time:.1f}s")

    # --- 逻辑: 复刻生成 ---
    def _generate_clone(self):
        spk_url = self.clone_voice_combo.currentData()
        text = self.reply_edit.toPlainText().strip()
        if not spk_url or not text:
            QMessageBox.warning(self, "提示", "请选择复刻底噪并填写回复文案。")
            return
            
        self._cleanup_temp_files()
        self.clone_gen_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self._clone_worker = VoiceCloneApiWorker(spk_audio=spk_url, text=text)
        self._clone_worker.finished.connect(self._on_clone_api_finished)
        self._clone_worker.start()

    def _on_clone_api_finished(self, result_url, success, error):
        if not success:
            self.progress_bar.setVisible(False)
            self.clone_gen_btn.setEnabled(True)
            QMessageBox.critical(self, "复刻失败", f"接口调用失败: {error}")
            return
            
        # 下载生成的音频到 temp 目录
        temp_id = uuid.uuid4().hex[:8]
        dest_path = self._audio_mgr._temp_dir / f"clone_{temp_id}.wav"
        self._downloader = DownloadWorker(result_url, dest_path)
        self._downloader.finished.connect(lambda p, s, e: self._on_clone_download_finished(p, s, e, result_url))
        self._downloader.start()

    def _on_clone_download_finished(self, path, success, error, cdn_url):
        self.progress_bar.setVisible(False)
        self.clone_gen_btn.setEnabled(True)
        if success:
            from live_agent.utils.cos_utils import calculate_md5
            self._current_audio_path = path
            self._current_cdn_url = cdn_url
            self._current_md5 = calculate_md5(path)
            self._update_save_status()
            QMessageBox.information(self, "成功", "人声复刻生成成功。")
        else:
            QMessageBox.critical(self, "失败", f"下载生成的音频失败: {error}")

    def _preview_audio(self):
        if self._current_audio_path:
             import subprocess
             import platform
             p = Path(self._current_audio_path)
             if platform.system() == "Windows":
                 subprocess.Popen(["powershell", "-c", f"Add-Type -AssemblyName PresentationCore; $p = New-Object System.Windows.Media.MediaPlayer; $p.Open([Uri]'{p.absolute().as_uri()}'); $p.Play(); Start-Sleep -s 10"])

    # --- 保存最终规则 ---
    def _on_save_clicked(self):
        # 如果是录音模式，点击保存时才上传 COS
        if self.type_combo.currentData() == "record" and not self._current_cdn_url:
            self.save_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self._uploader = CosUploadWorker(Path(self._current_audio_path))
            self._uploader.finished.connect(self._on_final_record_upload_finished)
            self._uploader.start()
        else:
            self.accept()

    def _on_final_record_upload_finished(self, url, md5, success, error):
        self.progress_bar.setVisible(False)
        if success:
            self._current_cdn_url = url
            self._current_md5 = md5
            self.accept()
        else:
            self.save_btn.setEnabled(True)
            QMessageBox.critical(self, "保存失败", f"录音同步至云端失败: {error}")

    def get_rule(self):
        from live_agent.gui.rule_store import Rule
        rule_id = self._rule.id if self._rule else uuid.uuid4().hex[:8]
        
        # 移动临时音频文件到正式路径
        rtype = self.type_combo.currentData()
        ext = ".wav" if rtype in ["record", "clone"] else ".mp3"
        final_path = self._audio_mgr._dir / f"{rule_id}{ext}"
        
        if self._current_audio_path and str(final_path) != str(self._current_audio_path):
            # 清理旧格式文件
            for old_ext in [".mp3", ".wav"]:
                old_p = self._audio_mgr._dir / f"{rule_id}{old_ext}"
                if old_p.exists(): old_p.unlink()
            shutil.move(self._current_audio_path, final_path)

        return Rule(
            id=rule_id,
            keyword=self.keyword_edit.text().strip(),
            reply=self.reply_edit.toPlainText().strip(),
            voice=self.voice_combo.currentData(),
            rate=self.rate_combo.currentText(),
            reply_type=rtype,
            enabled=getattr(self._rule, "enabled", True) if self._rule else True,
            cdn_url=self._current_cdn_url,
            audio_md5=self._current_md5
        )
