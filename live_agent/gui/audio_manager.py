"""音频管理器 —— 预生成 TTS 音频文件并通过系统播放器播放。"""

import platform
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QProcess

from live_agent.tts import EdgeTTS


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
            storage_dir = Path.home() / ".live_agent"
        self._dir = Path(storage_dir) / "audio"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._tts = EdgeTTS()
        self._current_gen = None
        self._playing = False
        self._current_play: QProcess | None = None

    def audio_path(self, rule_id: str) -> Path:
        return self._dir / f"{rule_id}.mp3"

    def has_audio(self, rule_id: str) -> bool:
        return self.audio_path(rule_id).exists()

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
        if not path.exists():
            self.audio_missing.emit(rule_id)
            return
        if self._playing:
            return
        self._playing = True
        self._current_play = QProcess()
        self._current_play.finished.connect(self._on_playback_finished)
        self.playback_started.emit(rule_id)
        system = platform.system()
        if system == "Darwin":
            self._current_play.start("afplay", [str(path)])
        elif system == "Linux":
            self._current_play.start("paplay", [str(path)])
        elif system == "Windows":
            self._current_play.start("powershell", [
                "-c",
                f"(New-Object Media.SoundPlayer '{path}').PlaySync()"
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

    def _on_playback_finished(self) -> None:
        self._playing = False
        if self._current_play is not None:
            self._current_play.deleteLater()
            self._current_play = None
        self.playback_finished.emit("")
