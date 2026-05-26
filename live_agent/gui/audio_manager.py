"""音频管理器 —— 预生成 TTS 音频文件并通过系统播放器播放。"""

import platform
import wave
import threading
import numpy as np
import sounddevice as sd
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QProcess

from live_agent.tts import EdgeTTS
from live_agent.utils import get_app_data_dir


class AudioManager(QObject):
    """管理规则对应音频文件的生成、存储和播放。"""

    generation_progress = Signal(int, int)
    generation_complete = Signal()
    rule_audio_ready = Signal(str)
    audio_missing = Signal(str)
    playback_started = Signal(str)
    playback_finished = Signal(str)

    def __init__(self, storage_dir: Path | None = None):
        super().__init__()
        if storage_dir is None:
            storage_dir = Path(get_app_data_dir())
        self._dir = Path(storage_dir) / "audio"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._tts = EdgeTTS()
        self._current_gen = None
        self._playing = False
        self._current_play: QProcess | None = None
        
        self.output_device_index = None # 库索引
        self.output_device_name = None  # 系统名称

    def audio_path(self, rule_id: str) -> Path:
        """优先返回 .wav (录音)，否则返回 .mp3 (TTS)"""
        wav_path = self._dir / f"{rule_id}.wav"
        if wav_path.exists():
            return wav_path
        return self._dir / f"{rule_id}.mp3"

    def has_audio(self, rule_id: str) -> bool:
        wav_exists = (self._dir / f"{rule_id}.wav").exists()
        if platform.system() == "Darwin":
            return wav_exists # macOS 必须要求 wav 才能完美支持设备选择
        return wav_exists or (self._dir / f"{rule_id}.mp3").exists()

    def generate_one(self, rule) -> None:
        """为单条规则生成音频。"""
        from live_agent.gui.workers import AudioGenWorker
        worker = AudioGenWorker(
            rules=[rule], tts=self._tts, audio_dir=self._dir,
        )
        worker.rule_done.connect(self._on_rule_done)
        worker.error.connect(self._on_gen_error)
        worker.finished_all.connect(lambda: worker.deleteLater())
        worker.start()

    def generate_all(self, rules: list) -> None:
        """为全部规则批量生成音频。"""
        from live_agent.gui.workers import AudioGenWorker
        if self._current_gen is not None and self._current_gen.isRunning():
            return
        self._current_gen = AudioGenWorker(
            rules=rules, tts=self._tts, audio_dir=self._dir,
        )
        self._current_gen.progress.connect(self.generation_progress.emit)
        self._current_gen.rule_done.connect(self._on_rule_done)
        self._current_gen.error.connect(self._on_gen_error)
        self._current_gen.finished_all.connect(self._on_generation_finished)
        self._current_gen.start()

    def play(self, rule_id: str) -> None:
        """播放预生成的音频文件。"""
        path = self.audio_path(rule_id)
        is_wav = path.suffix == ".wav"
        
        print(f"[DEBUG] AudioManager: 准备播放, rule_id={rule_id}, path={path}, device_index={self.output_device_index}")
        
        if not path.exists():
            print(f"[DEBUG] AudioManager: 文件不存在!")
            self.audio_missing.emit(rule_id)
            return
        
        if self._playing:
            print(f"[DEBUG] AudioManager: 当前正在播放中，跳过请求")
            return

        # 封装 WAV 播放到后台线程，防止 UI 阻塞
        if is_wav:
            def _play_wav_task():
                try:
                    self._playing = True
                    self.playback_started.emit(rule_id)
                    with wave.open(str(path), 'rb') as wf:
                        data = wf.readframes(wf.getnframes())
                        samples = np.frombuffer(data, dtype=np.int16)
                        if wf.getnchannels() == 1:
                            samples = samples.reshape(-1, 1)
                        sd.play(samples, wf.getframerate(), device=self.output_device_index)
                        sd.wait() # 在后台线程等待是安全的
                    print(f"[DEBUG] AudioManager: WAV 后台播放完成")
                except Exception as e:
                    print(f"[DEBUG] AudioManager: WAV 驱动播放失败: {e}")
                finally:
                    self._playing = False
                    self.playback_finished.emit("")

            threading.Thread(target=_play_wav_task, daemon=True).start()
            return
        
        # 对于 MP3，QProcess 本身就是非阻塞的
        self._playing = True
        self._current_play = QProcess()
        self._current_play.finished.connect(self._on_playback_finished)
        self._current_play.errorOccurred.connect(self._on_playback_error)
        self.playback_started.emit(rule_id)
        
        system = platform.system()
        if system == "Darwin":
            args = [str(path)]
            if self.output_device_name:
                args = ["-d", str(self.output_device_name)] + args
            self._current_play.start("afplay", args)
        elif system == "Linux":
            args = [str(path)]
            if self.output_device_name:
                args = ["--device", str(self.output_device_name)] + args
            self._current_play.start("paplay", args)
        elif system == "Windows":
            ps_cmd = (
                f"$p = New-Object System.Windows.Media.MediaPlayer; "
                f"$p.Open([Uri]'{path.absolute().as_uri()}'); "
                f"$p.Play(); "
                f"while($p.NaturalDuration.HasTimeSpan -eq $false) {{ Start-Sleep -m 50 }}; "
                f"Start-Sleep -s [math]::Ceiling($p.NaturalDuration.TimeSpan.TotalSeconds)"
            )
            self._current_play.start("powershell", [
                "-c",
                f"Add-Type -AssemblyName PresentationCore; {ps_cmd}"
            ])

    def _on_rule_done(self, rule_id: str) -> None:
        self.rule_audio_ready.emit(rule_id)

    def _on_gen_error(self, rule_id: str, error_msg: str) -> None:
        pass

    def _on_generation_finished(self) -> None:
        if self._current_gen is not None:
            self._current_gen.deleteLater()
            self._current_gen = None
        self.generation_complete.emit()

    def _on_playback_finished(self, exit_code, exit_status) -> None:
        print(f"[DEBUG] AudioManager: 播放进程结束, exit_code={exit_code}, status={exit_status}")
        self._playing = False
        if self._current_play is not None:
            self._current_play.deleteLater()
            self._current_play = None
        self.playback_finished.emit("")

    def _on_playback_error(self, error) -> None:
        print(f"[DEBUG] AudioManager: 播放进程发生错误: {error}")
        self._playing = False
        if self._current_play is not None:
            self._current_play.deleteLater()
            self._current_play = None
