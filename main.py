"""
Live Agent —— 基于 Sherpa-ONNX 的流式语音识别入口。

运行后将打开默认麦克风，实时将用户语音转为文字并逐字输出到终端。
当识别到预设关键词时，自动使用 Edge-TTS 合成并播放回复语音。
支持不同关键词使用不同音色，适配电商直播场景。
按 Ctrl+C 停止识别并退出。
"""

import signal
import sys
from dataclasses import dataclass

from live_agent import LiveASR, KeywordMatcher, EdgeTTS


# ---------------------------------------------------------------------------
# 关键词规则配置 —— 按需修改
# ---------------------------------------------------------------------------
# 每个规则可单独配置:
#   reply: TTS 回复文案
#   voice: 音色（可选，默认 zh-CN-XiaoxiaoNeural 晓晓·女声）
#   rate:  语速（可选，如 "+20%" 加快, "-10%" 减慢）
#
# 常用音色:
#   zh-CN-XiaoxiaoNeural  晓晓  女声 活泼温暖 —— 带货主力
#   zh-CN-YunxiNeural     云希  男声 阳光有冲劲 —— 限时秒杀
#   zh-CN-YunyangNeural   云扬  男声 专业沉稳 —— 产品介绍
#   zh-CN-XiaohanNeural   晓涵  女声 温暖甜美 —— 情感营销
#   zh-CN-XiaoyanNeural   晓颜  女声 客服口吻 —— 答疑互动


@dataclass
class Rule:
    """单条关键词规则。"""
    reply: str
    voice: str = "zh-CN-YunxiNeural"
    rate: str | None = None


RULES: dict[str, Rule] = {
    "上架": Rule(
        reply="货品已经上架了，大家快抢啊",
        voice="zh-CN-YunxiNeural",
    ),
    "下架": Rule(
        reply="货品已经下架了，别看了",
        voice="zh-CN-YunyangNeural",
    ),
    "秒杀": Rule(
        reply="限时秒杀开始，库存不多手慢无！",
        voice="zh-CN-YunxiNeural",
        rate="+30%",
    ),
    "优惠券": Rule(
        reply="优惠券已经发放，先到先得哦",
        voice="zh-CN-XiaohanNeural",
    ),
    "谢谢大家": Rule(
        reply="感谢各位的支持，我们下次直播再见！",
        voice="zh-CN-XiaoxiaoNeural",
    ),
    "你是谁": Rule(
        reply="我是直播小助手，随时为您播报商品信息",
        voice="zh-CN-XiaoyanNeural",
    ),
}


def main():
    """主函数：串接 ASR → 关键词匹配 → TTS 播报。"""

    # 提取 reply 文案给 KeywordMatcher 做匹配
    keyword_replies = {
        keyword: rule.reply for keyword, rule in RULES.items()
    }

    asr = LiveASR(model_dir="models")
    matcher = KeywordMatcher(keyword_replies)

    # 只需一个 EdgeTTS 实例，speak() 方法支持按需切换音色
    tts = EdgeTTS()

    def on_text(text: str):
        """ASR 识别结果回调。"""
        print(f"\r{text}", end="", flush=True)

        hit = matcher.check(text)
        if hit:
            rule = RULES[hit.keyword]
            voice_name = rule.voice.split("-")[-1].replace("Neural", "")
            print(f"\n[命中] {hit.keyword} → [{voice_name}] {rule.reply}")
            tts.speak(text=rule.reply, voice=rule.voice, rate=rule.rate)

    def on_interrupt(signum, frame):
        print("\n正在停止...")
        asr.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_interrupt)

    print("Live ASR 已启动，请对着麦克风说话。按 Ctrl+C 停止。")
    print(f"当前关键词 ({len(RULES)} 条):")
    for kw, rule in RULES.items():
        voice_name = rule.voice.split("-")[-1].replace("Neural", "")
        print(f"  \"{kw}\" → [{voice_name}] {rule.reply}")
    print()
    asr.start(callback=on_text)
    signal.pause()


if __name__ == "__main__":
    main()
