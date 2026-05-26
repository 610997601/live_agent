"""设置对话框 —— 音频输入输出设备选择。"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, 
    QLabel, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt
import sounddevice as sd
from live_agent.utils import GlobalConfig

class SettingsDialog(QDialog):
    def __init__(self, parent=None, is_asr_active=False):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.setMinimumWidth(400)
        self.config = GlobalConfig()
        self.is_asr_active = is_asr_active
        
        self._init_ui()
        self._load_devices()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 输入设备
        layout.addWidget(QLabel("<b>音频输入设备 (麦克风):</b>"))
        self.input_combo = QComboBox()
        self.input_combo.setMinimumHeight(35)
        layout.addWidget(self.input_combo)

        # 输出设备
        layout.addWidget(QLabel("<b>音频输出设备 (扬声器):</b>"))
        self.output_combo = QComboBox()
        self.output_combo.setMinimumHeight(35)
        layout.addWidget(self.output_combo)

        layout.addSpacing(10)
        
        # 按钮
        self.buttons = QDialogButtonBox()
        save_btn = self.buttons.addButton("保存配置", QDialogButtonBox.AcceptRole)
        cancel_btn = self.buttons.addButton("取消", QDialogButtonBox.RejectRole)
        
        self.buttons.accepted.connect(self._save_settings)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _load_devices(self):
        try:
            if not self.is_asr_active:
                try:
                    sd._terminate()
                    sd._initialize()
                except: pass
            
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()
            
            input_saved = self.config.get("audio_input", "default")
            output_saved = self.config.get("audio_output", "default")

            # 添加默认选项
            self.input_combo.addItem("系统默认 (推荐)", "default")
            self.output_combo.addItem("系统默认 (推荐)", "default")

            input_idx = 0
            output_idx = 0

            for i, d in enumerate(devices):
                api_name = hostapis[d['hostapi']]['name']
                name = f"{d['name']} ({api_name})"
                
                if d['max_input_channels'] > 0:
                    self.input_combo.addItem(name, d['name'])
                    if d['name'] == input_saved:
                        input_idx = self.input_combo.count() - 1
                
                if d['max_output_channels'] > 0:
                    self.output_combo.addItem(name, d['name'])
                    if d['name'] == output_saved:
                        output_idx = self.output_combo.count() - 1

            self.input_combo.setCurrentIndex(input_idx)
            self.output_combo.setCurrentIndex(output_idx)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取音频设备列表失败: {e}")

    def _save_settings(self):
        input_name = self.input_combo.currentData()
        output_name = self.output_combo.currentData()
        self.config.set("audio_input", input_name)
        self.config.set("audio_output", output_name)
        self.accept()

def get_audio_devices():
    """返回 (in_idx, out_idx, out_name)"""
    config = GlobalConfig()
    try:
        try:
            sd._terminate()
            sd._initialize()
        except: pass
        
        devices = sd.query_devices()
        in_name = config.get("audio_input", "default")
        out_name = config.get("audio_output", "default")
        
        in_idx = None
        out_idx = None
        target_out_name = None
        
        if in_name == "default": in_idx = None
        if out_name == "default": target_out_name = None

        for i, d in enumerate(devices):
            if d['name'] == in_name and d['max_input_channels'] > 0:
                in_idx = i
            if d['name'] == out_name and d['max_output_channels'] > 0:
                out_idx = i
                target_out_name = d['name']
                
        return in_idx, out_idx, target_out_name
    except:
        return None, None, None
