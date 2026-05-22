"""
基于 Microsoft Edge TTS 的文字转语音（TTS）模块。

使用 edge-tts 库，将文字合成为 MP3 音频并通过系统播放器播放。
支持中文和英文，无需 API Key，仅需网络连接。
speak() 方法支持按需切换音色，适配多场景直播语音。
"""

import platform
import subprocess
import tempfile
import threading
from pathlib import Path

import edge_tts


class EdgeTTS:
    """Microsoft Edge 文字转语音播放器。

    使用 edge-tts 将文字合成为 MP3，然后调用系统播放器播放。
    播放操作在独立线程中执行，不会阻塞调用方。
    支持在 speak() 时按需切换音色和语速。

    使用示例:
        tts = EdgeTTS()
        # 默认音色
        tts.speak("货品已经上架了")
        # 临时切换音色
        tts.speak("最后十单，手慢无！", voice="zh-CN-YunxiNeural", rate="+30%")
    """

    DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"  # 晓晓，活泼女声

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        rate: str = "+0%",
        volume: str = "+0%",
    ):
        """初始化 TTS 播放器。

        参数:
            voice: 默认语音角色。常用中文角色:
                   zh-CN-XiaoxiaoNeural  (晓晓·女·活泼温暖)
                   zh-CN-YunxiNeural     (云希·男·阳光有冲劲)
                   zh-CN-YunyangNeural   (云扬·男·专业沉稳)
                   zh-CN-XiaohanNeural   (晓涵·女·温暖甜美)
                   zh-CN-XiaoyanNeural   (晓颜·女·客服口吻)
                   完整列表见: https://aka.ms/speech/tts-voices
            rate: 默认语速，范围 "-50%" ~ "+100%"。
            volume: 默认音量，范围 "-100%" ~ "+100%"。
        """
        self._voice = voice
        self._rate = rate
        self._volume = volume

    def speak(
        self,
        text: str,
        voice: str | None = None,
        rate: str | None = None,
    ) -> None:
        """在后台线程中合成并播放语音，不阻塞调用方。

        参数:
            text: 要朗读的文字内容。
            voice: 临时切换的音色，为 None 则使用默认音色。
            rate: 临时切换的语速，为 None 则使用默认语速。
        """
        v = voice or self._voice
        r = rate or self._rate

        def _run():
            try:
                self._speak_sync(text, voice=v, rate=r)
            except Exception as e:
                print(f"[TTS 错误] {e}")

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def synthesize_to_file(
        self, text: str, voice: str, rate: str, output_path: Path
    ) -> None:
        """合成语音到文件，不播放。用于预生成规则对应的音频文件。"""
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume=self._volume,
        )
        communicate.save_sync(str(output_path))

    def _speak_sync(self, text: str, voice: str, rate: str) -> None:
        """同步合成语音并播放（内部方法）。

        参数:
            text: 要朗读的文字。
            voice: 使用的音色。
            rate: 语速。
        """
        # 创建临时目录存放生成的 MP3 文件
        tmp_dir = Path(tempfile.gettempdir()) / "live_agent_tts"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        mp3_path = tmp_dir / "reply.mp3"

        # 合成语音，保存为 MP3 文件
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume=self._volume,
        )
        communicate.save_sync(str(mp3_path))

        # 根据操作系统选择对应的播放命令
        _play_audio(mp3_path)

        # 播放完成后清理临时文件
        mp3_path.unlink(missing_ok=True)


def _play_audio(path: Path) -> None:
    """使用系统自带播放器播放音频文件。

    参数:
        path: 音频文件路径。
    """
    system = platform.system()
    if system == "Darwin":
        # macOS 内置 afplay 命令
        subprocess.run(
            ["afplay", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif system == "Linux":
        # Linux 优先使用 paplay（PulseAudio），其次 aplay（ALSA）
        subprocess.run(
            ["paplay", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif system == "Windows":
        # Windows 使用 PowerShell 调用 Media.MediaPlayer (支持 MP3)
        # 注意：SoundPlayer 仅支持 WAV，而 edge-tts 生成的是 MP3
        ps_cmd = (
            f"$p = New-Object System.Windows.Media.MediaPlayer; "
            f"$p.Open([Uri]'{path.absolute().as_uri()}'); "
            f"$p.Play(); "
            f"while($p.NaturalDuration.HasTimeSpan -eq $false) {{ Start-Sleep -m 50 }}; "
            f"Start-Sleep -s [math]::Ceiling($p.NaturalDuration.TimeSpan.TotalSeconds)"
        )
        subprocess.run(
            ["powershell", "-c", f"Add-Type -AssemblyName PresentationCore; {ps_cmd}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
