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

    DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"

    @staticmethod
    async def get_voices():
        """从 Edge TTS 获取当前所有可用的中文音色。"""
        try:
            voices = await edge_tts.list_voices()
            # 过滤中文音色 (zh-CN)
            zh_voices = [v for v in voices if v["Locale"].startswith("zh-CN")]
            if not zh_voices:
                raise Exception("未找到中文音色")
            return zh_voices
        except Exception as e:
            print(f"[DEBUG] 获取在线音色失败: {e}, 使用本地备份列表")
            # 极简保底备份，确保断网也能运行
            return [
                {"ShortName": "zh-CN-XiaoxiaoNeural", "FriendlyName": "晓晓 (备份)"},
                {"ShortName": "zh-CN-YunxiNeural", "FriendlyName": "云希 (备份)"},
                {"ShortName": "zh-CN-YunyangNeural", "FriendlyName": "云扬 (备份)"},
            ]

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
        """合成语音到文件。在 macOS 下会自动转换为 WAV 以支持硬件索引播放。"""
        import platform
        import subprocess
        system = platform.system()

        if system == "Darwin" and output_path.suffix == ".wav":
            # macOS 特处理：先生成临时 MP3 再转 WAV
            tmp_mp3 = output_path.with_suffix(".mp3.tmp")
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=self._volume,
            )
            communicate.save_sync(str(tmp_mp3))
            
            # 校验 MP3 是否生成成功且非空
            if not tmp_mp3.exists() or tmp_mp3.stat().st_size == 0:
                print(f"[DEBUG] TTS 合成失败: 无法生成有效的 MP3 文件 (voice={voice})")
                if tmp_mp3.exists(): tmp_mp3.unlink()
                return

            try:
                subprocess.run([
                    "afconvert", "-f", "WAVE", "-d", "LEI16@44100",
                    str(tmp_mp3), str(output_path)
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[DEBUG] TTS 转换成功: {output_path.name} ({output_path.stat().st_size} bytes)")
            except Exception as conv_err:
                print(f"[DEBUG] WAV 转换失败: {conv_err}")
            finally:
                if tmp_mp3.exists(): tmp_mp3.unlink()
        else:
            # 正常生成（MP3）
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=self._volume,
            )
            communicate.save_sync(str(output_path))
            if output_path.exists():
                print(f"[DEBUG] TTS 合成成功: {output_path.name} ({output_path.stat().st_size} bytes)")

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
