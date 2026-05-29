"""后台工作线程 —— ASR 识别和 TTS 音频生成。"""

import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from live_agent.asr import LiveASR
from live_agent.tts import EdgeTTS


class AsrWorker(QThread):
    """在后台线程运行流式语音识别，通过信号桥接回调到主线程。"""

    text_recognized = Signal(str)
    state_changed = Signal(str) # 新增：状态变化信号
    error_occurred = Signal(str)

    def __init__(self, model_dir: str = "models", device=None):
        super().__init__()
        self._model_dir = model_dir
        self._device = device
        self._asr: LiveASR | None = None

    def run(self) -> None:
        try:
            self._asr = LiveASR(model_dir=self._model_dir)
            self._asr.start(
                callback=self._on_text, 
                state_callback=self._on_state,
                device=self._device
            )
            self.exec()
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"[AsrWorker] 崩溃:\n{error_trace}")
            self.error_occurred.emit(f"{e}\n\n详细堆栈:\n{error_trace}")

    def _on_text(self, text: str) -> None:
        self.text_recognized.emit(text)

    def _on_state(self, state: str) -> None:
        self.state_changed.emit(state)

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
        import platform
        system = platform.system()
        total = len(self._rules)
        for i, rule in enumerate(self._rules):
            # 兼容对象和字典
            is_dict = isinstance(rule, dict)
            rule_id = rule.get("id") if is_dict else getattr(rule, "id", "")
            reply = rule.get("reply") if is_dict else getattr(rule, "reply", "")
            voice = rule.get("voice") if is_dict else getattr(rule, "voice", "")
            rate = rule.get("rate") if is_dict else getattr(rule, "rate", "")
            reply_type = rule.get("reply_type") if is_dict else getattr(rule, "reply_type", "tts")

            # 录音类型不需要生成 TTS
            if reply_type == "record":
                self.progress.emit(i + 1, total)
                continue
            
            try:
                # macOS 下生成目标改为 .wav，其他平台保持 .mp3
                ext = ".wav" if system == "Darwin" else ".mp3"
                path = self._audio_dir / f"{rule_id}{ext}"

                self._tts.synthesize_to_file(
                    text=reply,
                    voice=voice,
                    rate=rate,
                    output_path=path,
                )

                self.rule_done.emit(rule_id)
            except Exception as e:
                self.error.emit(rule_id, str(e))
            self.progress.emit(i + 1, total)
        self.finished_all.emit()


class VoiceFetchWorker(QThread):
    """在后台线程获取 Edge TTS 音色列表。"""
    finished = Signal(list)

    def run(self) -> None:
        import asyncio
        try:
            from live_agent.tts import EdgeTTS
            voices = asyncio.run(EdgeTTS.get_voices())
            self.finished.emit(voices)
        except Exception as e:
            print(f"[DEBUG] VoiceFetchWorker 失败: {e}")
            self.finished.emit([])

class CosUploadWorker(QThread):
    """后台上传文件到腾讯 COS"""
    finished = Signal(str, str, bool, str) # cdn_url, md5, success, error_msg

    def __init__(self, file_path: Path, prefix: str = "ai-montage/dev"):
        super().__init__()
        self.file_path = file_path
        self.prefix = prefix

    def run(self):
        from live_agent.utils.cos_utils import upload_to_cos
        try:
            cdn_url, md5 = upload_to_cos(self.file_path, self.prefix)
            self.finished.emit(cdn_url, md5, True, "")
        except Exception as e:
            self.finished.emit("", "", False, str(e))

class DownloadWorker(QThread):
    """后台下载 URL 到本地文件"""
    finished = Signal(str, bool, str) # local_path, success, error_msg

    def __init__(self, url: str, dest_path: Path):
        super().__init__()
        self.url = url
        self.dest_path = dest_path

    def run(self):
        from live_agent.utils.cos_utils import download_from_url
        try:
            success = download_from_url(self.url, self.dest_path)
            if success:
                self.finished.emit(str(self.dest_path), True, "")
            else:
                self.finished.emit("", False, "下载失败 (状态码非 200)")
        except Exception as e:
            self.finished.emit("", False, str(e))

class VoiceCloneApiWorker(QThread):
    """调用声音复刻 API"""
    finished = Signal(str, bool, str) # result_url, success, error_msg

    def __init__(self, spk_audio: str, text: str):
        super().__init__()
        self.spk_audio = spk_audio
        self.text = text

    def run(self):
        import requests
        import json
        url = "https://metis-api.ad-saas.com/voice/all_in_one"
        headers = {"Content-Type": "application/json"}
        payload = {
            "spk_audio": self.spk_audio,
            "text": self.text
        }
        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
            data = resp.json()
            if data.get("code") == 0:
                result_url = data["data"]["url"]
                self.finished.emit(result_url, True, "")
            else:
                self.finished.emit("", False, data.get("msg", "API 业务错误"))
        except Exception as e:
            self.finished.emit("", False, str(e))
