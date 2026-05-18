"""
live_agent —— 实时语音识别与交互包。

提供:
    LiveASR — 流式语音识别（Sherpa-ONNX）
    KeywordMatcher — 关键词匹配器
    EdgeTTS — 文字转语音播放（Edge-TTS）
"""

from live_agent.asr import LiveASR
from live_agent.keyword import KeywordMatcher, KeywordHit
from live_agent.tts import EdgeTTS

__all__ = ["LiveASR", "KeywordMatcher", "KeywordHit", "EdgeTTS"]
