"""规则编辑对话框 —— 添加/编辑关键词触发规则。"""

import os
import time
import wave
import tempfile
import uuid
from pathlib import Path
import numpy as np
import sounddevice as sd
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import (
    QDialog, QLineEdit, QTextEdit, QComboBox,
    QDialogButtonBox, QVBoxLayout, QHBoxLayout, QMessageBox, QLabel,
    QPushButton, QStackedWidget, QWidget
)

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
        self._temp_record_path = None
        self._is_recording = False
        self._recorded_data = []
        self._stream = None
        self._recording_timer = QTimer(self)
        self._recording_timer.timeout.connect(self._update_record_status)
        self._recording_start_time = 0

        is_edit = rule is not None
        self.setWindowTitle("编辑规则" if is_edit else "添加规则")
        self.setMinimumWidth(600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(QLabel("<b>触发关键词:</b>"))
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("例如: 上架")
        self.keyword_edit.setMinimumHeight(40)
        self.keyword_edit.setStyleSheet("font-size: 14px; padding: 8px;")
        layout.addWidget(self.keyword_edit)

        layout.addWidget(QLabel("<b>回复文案:</b>"))
        self.reply_edit = QTextEdit()
        self.reply_edit.setPlaceholderText("例如: 货品已经上架了，大家快抢啊")
        self.reply_edit.setMinimumHeight(80)
        self.reply_edit.setStyleSheet("font-size: 14px; padding: 8px;")
        layout.addWidget(self.reply_edit)

        # 回复方式选择
        layout.addWidget(QLabel("<b>回复方式:</b>"))
        self.type_combo = QComboBox()
        self.type_combo.setMinimumHeight(40)
        self.type_combo.addItem("智能生成 (TTS)", "tts")
        self.type_combo.addItem("现场录音", "record")
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addWidget(self.type_combo)

        # 堆栈窗口切换 TTS 设置和录音设置
        self.stack = QStackedWidget()
        
        # TTS 面板
        self.tts_panel = QWidget()
        tts_layout = QVBoxLayout(self.tts_panel)
        tts_layout.setContentsMargins(0, 0, 0, 0)
        
        tts_layout.addWidget(QLabel("<b>语音音色:</b>"))
        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumHeight(40)
        
        # 动态加载音色
        voices = GlobalConfig.get_voices()
        for v in voices:
            short_name = v.get("ShortName", "")
            friendly_name = v.get("FriendlyName", "")
            gender = "女声" if v.get("Gender") == "Female" else "男声"
            
            # 1. 尝试从 ShortName 提取核心 ID 并映射中文
            # zh-CN-XiaoxiaoNeural -> Xiaoxiao
            core_id = short_name.split("-")[-1].replace("Neural", "")
            
            mapping = {
                "Xiaoxiao": "晓晓", "Xiaoyi": "晓伊", "Yunxi": "云希", 
                "Yunyang": "云扬", "Yunjian": "云健", "Yunxia": "云夏",
                "Xiaobei": "晓北 (东北话)", "Xiaoni": "晓妮 (陕西话)"
            }
            
            name = mapping.get(core_id, core_id)
            display_name = f"{name} ({gender})"
            
            self.voice_combo.addItem(display_name, short_name)
            
        tts_layout.addWidget(self.voice_combo)

        tts_layout.addWidget(QLabel("<b>语音语速:</b>"))
        self.rate_combo = QComboBox()
        self.rate_combo.setMinimumHeight(40)
        self.rate_combo.addItems(RATE_OPTIONS)
        self.rate_combo.setCurrentText("+0%")
        tts_layout.addWidget(self.rate_combo)
        self.stack.addWidget(self.tts_panel)

        # 录音面板
        self.record_panel = QWidget()
        rec_layout = QVBoxLayout(self.record_panel)
        rec_layout.setContentsMargins(0, 0, 0, 0)
        
        btn_row = QHBoxLayout()
        self.rec_btn = QPushButton("🎤 开始录音")
        self.rec_btn.setMinimumHeight(40)
        self.rec_btn.clicked.connect(self._start_record)
        
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_record)
        
        self.play_btn = QPushButton("▶ 试听")
        self.play_btn.setMinimumHeight(40)
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._preview_record)
        
        btn_row.addWidget(self.rec_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.play_btn)
        rec_layout.addLayout(btn_row)
        
        self.status_label = QLabel("等待录音... (建议不超过 30 秒)")
        self.status_label.setStyleSheet("color: #666;")
        rec_layout.addWidget(self.status_label)
        
        self.stack.addWidget(self.record_panel)
        layout.addWidget(self.stack)

        layout.addSpacing(10)
        buttons = QDialogButtonBox()
        save_btn = buttons.addButton(" 保 存 ", QDialogButtonBox.AcceptRole)
        save_btn.setObjectName("generateBtn")
        save_btn.setMinimumHeight(40)
        save_btn.setMinimumWidth(100)
        
        cancel_btn = buttons.addButton(" 取 消 ", QDialogButtonBox.RejectRole)
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setMinimumWidth(100)
        
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if is_edit:
            self._populate(rule)

    def _on_type_changed(self, index):
        self.stack.setCurrentIndex(index)

    def _populate(self, rule) -> None:
        self.keyword_edit.setText(rule.keyword)
        self.reply_edit.setPlainText(rule.reply)
        
        type_idx = self.type_combo.findData(rule.reply_type)
        if type_idx >= 0:
            self.type_combo.setCurrentIndex(type_idx)
            self.stack.setCurrentIndex(type_idx)

        idx = self.voice_combo.findData(rule.voice)
        if idx >= 0:
            self.voice_combo.setCurrentIndex(idx)
        rate_idx = self.rate_combo.findText(rule.rate)
        if rate_idx >= 0:
            self.rate_combo.setCurrentIndex(rate_idx)
            
        if rule.reply_type == "record":
            # 检查是否有现有录音
            from live_agent.gui.audio_manager import AudioManager
            mgr = AudioManager()
            path = mgr.audio_path(rule.id)
            if path.exists() and path.suffix == ".wav":
                self.play_btn.setEnabled(True)
                self.status_label.setText("已有录音文件，可直接保存或重新录制。")

    def _start_record(self):
        try:
            self._recorded_data = []
            self._is_recording = True
            self._recording_start_time = time.time()
            self._stream = sd.InputStream(samplerate=44100, channels=1, callback=self._audio_callback)
            self._stream.start()
            
            self.rec_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.play_btn.setEnabled(False)
            self._recording_timer.start(100)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开麦克风: {e}")

    def _audio_callback(self, indata, frames, time_info, status):
        if self._is_recording:
            self._recorded_data.append(indata.copy())

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
            self._save_temp_wav()
            self.play_btn.setEnabled(True)
            duration = time.time() - self._recording_start_time
            self.status_label.setText(f"录音完成: {duration:.1f}s")
        else:
            self.status_label.setText("未采集到音频数据")

    def _save_temp_wav(self):
        if not self._recorded_data: return
        data = np.concatenate(self._recorded_data, axis=0)
        
        # --- 自动裁剪前后空白音 ---
        # 1. 计算振幅绝对值
        abs_data = np.abs(data).flatten()
        # 2. 设置阈值（通常 0.01 - 0.05 之间，视环境噪音而定）
        threshold = 0.02
        # 3. 寻找超过阈值的起始和结束索引
        indices = np.where(abs_data > threshold)[0]
        
        if len(indices) > 0:
            start_idx = max(0, indices[0] - 4410) # 留 100ms 缓冲
            end_idx = min(len(abs_data), indices[-1] + 4410) # 留 100ms 缓冲
            data = data[start_idx:end_idx]
        
        # 创建临时文件
        if self._temp_record_path and Path(self._temp_record_path).exists():
            try: Path(self._temp_record_path).unlink()
            except: pass
            
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        self._temp_record_path = path
        
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2) # 16-bit
            wf.setframerate(44100)
            # 转换 float32 到 int16
            audio_int16 = (data * 32767).astype(np.int16)
            wf.writeframes(audio_int16.tobytes())

    def _update_record_status(self):
        duration = time.time() - self._recording_start_time
        self.status_label.setText(f"正在录音: {duration:.1f}s (建议不超过 30s)")
        if duration > 30: # 强制停止
            self._stop_record()

    def _preview_record(self):
        path = self._temp_record_path
        if not path and self._rule:
            # 如果是编辑现有录音且未重新录制
            from live_agent.gui.audio_manager import AudioManager
            mgr = AudioManager()
            path = str(mgr.audio_path(self._rule.id))
        
        if not path or not Path(path).exists():
            return
            
        # 统一使用系统播放器播放
        import platform
        import subprocess
        system = platform.system()
        if system == "Darwin":
            subprocess.Popen(["afplay", path])
        elif system == "Windows":
             subprocess.Popen(["powershell", "-c", f"Add-Type -AssemblyName PresentationCore; $p = New-Object System.Windows.Media.MediaPlayer; $p.Open([Uri]'{Path(path).absolute().as_uri()}'); $p.Play(); Start-Sleep -s 10"])

    def _validate_and_accept(self) -> None:
        keyword = self.keyword_edit.text().strip()
        reply = self.reply_edit.toPlainText().strip()
        reply_type = self.type_combo.currentData()
        
        if not keyword:
            QMessageBox.warning(self, "提示", "关键词不能为空。")
            return
            
        if reply_type == "tts":
            if not reply:
                QMessageBox.warning(self, "提示", "回复文案不能为空。")
                return
        else:
            # 录音模式
            has_record = (self._temp_record_path and Path(self._temp_record_path).exists())
            if not has_record:
                # 检查是否是编辑模式下的旧录音
                if self._rule:
                    from live_agent.gui.audio_manager import AudioManager
                    mgr = AudioManager()
                    if mgr.audio_path(self._rule.id).suffix == ".wav":
                        has_record = True
            
            if not has_record:
                QMessageBox.warning(self, "提示", "请先录音再保存。")
                return

        self.accept()

    def get_rule(self):
        from live_agent.gui.rule_store import Rule
        rule_id = self._rule.id if self._rule else uuid.uuid4().hex[:8]
        
        from live_agent.gui.audio_manager import AudioManager
        mgr = AudioManager()

        # 处理音频文件的切换与持久化
        if self.type_combo.currentData() == "record":
            if self._temp_record_path:
                final_path = mgr._dir / f"{rule_id}.wav"
                # 清理旧的 TTS mp3
                mp3_path = mgr._dir / f"{rule_id}.mp3"
                if mp3_path.exists(): mp3_path.unlink()
                
                import shutil
                shutil.move(self._temp_record_path, final_path)
                self._temp_record_path = None # 防止重复移动
        else:
            # 如果从录音切换回 TTS，需要清理旧的录音 wav
            wav_path = mgr._dir / f"{rule_id}.wav"
            if wav_path.exists():
                try: wav_path.unlink()
                except: pass

        return Rule(
            id=rule_id,
            keyword=self.keyword_edit.text().strip(),
            reply=self.reply_edit.toPlainText().strip(),
            voice=self.voice_combo.currentData(),
            rate=self.rate_combo.currentText(),
            reply_type=self.type_combo.currentData(),
            enabled=getattr(self._rule, "enabled", True) if self._rule else True
        )
