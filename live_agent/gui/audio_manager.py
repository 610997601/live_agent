"""音频管理器 —— 预生成 TTS 音频文件并通过系统播放器播放。"""

import platform
import wave
import threading
import numpy as np
import sounddevice as sd
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

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
        
        # 新增：物理隔离的临时文件夹
        self._temp_dir = self._dir / "temp"
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        
        self._tts = EdgeTTS()
        self._current_gen = None
        self._playing = False
        
        # 使用 QtMultimedia 进行播放 (MP3)
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        
        # 信号连接
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        self._player.errorOccurred.connect(self._on_player_error)
        
        self.output_device_index = None # 库索引 (用于 sd 播放 WAV)
        self.output_device_name = None  # 系统名称 (针对 QAudioDevice)

    def audio_path(self, rule_id: str) -> Path:
        """优先返回 .wav (录音)，否则返回 .mp3 (TTS)"""
        wav_path = self._dir / f"{rule_id}.wav"
        if wav_path.exists():
            return wav_path
        return self._dir / f"{rule_id}.mp3"

    def has_audio(self, rule_id: str) -> bool:
        wav_exists = (self._dir / f"{rule_id}.wav").exists()
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
        """根据规则 ID 播放音频文件。"""
        path = self.audio_path(rule_id)
        self.play_path(path, rule_id)

    def play_path(self, path: str | Path, tag: str = "") -> None:
        """通用播放方法，支持直接传入路径。"""
        path = Path(path)
        is_wav = path.suffix == ".wav"
        
        print(f"[DEBUG] AudioManager: 准备播放路径, tag={tag}, path={path}, device_index={self.output_device_index}")
        
        if not path.exists():
            print(f"[DEBUG] AudioManager: 文件不存在: {path}")
            return
        
        if self._playing:
            print(f"[DEBUG] AudioManager: 当前正在播放中，尝试停止旧播放")
            self.stop_current()

        # 封装 WAV 播放到后台线程 (sd 驱动)
        if is_wav:
            def _play_wav_task():
                try:
                    self._playing = True
                    self.playback_started.emit(tag)
                    with wave.open(str(path), 'rb') as wf:
                        data = wf.readframes(wf.getnframes())
                        samples = np.frombuffer(data, dtype=np.int16)
                        if wf.getnchannels() == 1:
                            samples = samples.reshape(-1, 1)
                        sd.play(samples, wf.getframerate(), device=self.output_device_index)
                        sd.wait()
                    print(f"[DEBUG] AudioManager: WAV 后台播放完成")
                except Exception as e:
                    print(f"[DEBUG] AudioManager: WAV 驱动播放失败: {e}")
                finally:
                    self._playing = False
                    self.playback_finished.emit("")

            threading.Thread(target=_play_wav_task, daemon=True).start()
            return
        
        # 对于 MP3，使用 QMediaPlayer
        self._playing = True
        self.playback_started.emit(tag)
        
        # --- 同步设备选择 ---
        if self.output_device_name:
            try:
                from PySide6.QtMultimedia import QMediaDevices
                for device in QMediaDevices.audioOutputs():
                    if device.description() == self.output_device_name:
                        self._audio_output.setDevice(device)
                        break
            except Exception as e:
                print(f"[DEBUG] AudioManager: 设置 Qt 音频输出设备失败: {e}")
        # --------------------

        self._player.setSource(QUrl.fromLocalFile(str(path.absolute())))
        self._player.play()

    def stop_current(self):
        """停止当前播放"""
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.stop()
        sd.stop()
        self._playing = False

    def _on_rule_done(self, rule_id: str) -> None:
        self.rule_audio_ready.emit(rule_id)

    def _on_gen_error(self, rule_id: str, error_msg: str) -> None:
        pass

    def _on_generation_finished(self) -> None:
        if self._current_gen is not None:
            self._current_gen.deleteLater()
            self._current_gen = None
        self.generation_complete.emit()

    def _on_media_status_changed(self, status):
        print(f"[DEBUG] AudioManager: 媒体状态改变: {status}")
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._playing = False
            self.playback_finished.emit("")

    def _on_player_error(self, error, error_string):
        print(f"[DEBUG] AudioManager: QMediaPlayer 错误: {error_string}")
        self._playing = False
        self.playback_finished.emit("")
