"""后台工作线程 —— ASR 识别和 TTS 音频生成。"""

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from live_agent.asr import LiveASR
from live_agent.tts import EdgeTTS


class AsrWorker(QThread):
    """在后台线程运行流式语音识别，通过信号桥接回调到主线程。"""

    text_recognized = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, model_dir: str = "models"):
        super().__init__()
        self._model_dir = model_dir
        self._asr: LiveASR | None = None

    def run(self) -> None:
        try:
            self._asr = LiveASR(model_dir=self._model_dir)
            self._asr.start(callback=self._on_text)
            self.exec()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _on_text(self, text: str) -> None:
        self.text_recognized.emit(text)

    def stop(self) -> None:
        if self._asr is not None:
            self._asr.stop()
        self.quit()
        if not self.wait(3000):
            self.terminate()


class AudioGenWorker(QThread):
    """在后台线程生成 TTS 音频文件。"""

    progress = Signal(int, int)
    rule_done = Signal(str)
    error = Signal(str, str)
    finished_all = Signal()

    def __init__(self, rules: list, tts: EdgeTTS, audio_dir: Path):
        super().__init__()
        self._rules = rules
        self._tts = tts
        self._audio_dir = Path(audio_dir)

    def run(self) -> None:
        total = len(self._rules)
        for i, rule in enumerate(self._rules):
            try:
                path = self._audio_dir / f"{rule.id}.mp3"
                self._tts.synthesize_to_file(
                    text=rule.reply,
                    voice=rule.voice,
                    rate=rule.rate,
                    output_path=path,
                )
                self.rule_done.emit(rule.id)
            except Exception as e:
                self.error.emit(rule.id, str(e))
            self.progress.emit(i + 1, total)
        self.finished_all.emit()
