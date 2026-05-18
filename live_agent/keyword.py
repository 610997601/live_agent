"""
关键词匹配器模块。

在流式识别的增量文字中检测预设关键词，命中时触发 TTS 语音回复。
同一个关键词在一次连续对话中只触发一次，避免重复播报。
"""


class KeywordMatcher:
    """流式关键词匹配器。

    识别结果是增量追加的，每次 check() 检查当前累积文字中是否包含关键词。
    命中后记录已触发状态，直到识别被重置才允许再次匹配。

    使用示例:
        rules = {
            "上架": "货品已经上架了，大家快抢啊",
            "下架": "货品已经下架了，别看了",
        }
        matcher = KeywordMatcher(rules)

        # 在 ASR 回调中调用
        match = matcher.check("我要上架这个")
        if match:
            print(f"命中: {match.keyword} → {match.reply}")
    """

    def __init__(self, rules: dict[str, str]):
        """初始化关键词匹配器。

        参数:
            rules: 关键词 → 回复文案 的映射字典。
                   例如 {"上架": "货品已上架", "下架": "货品已下架"}
        """
        self._rules = rules
        # 记录本轮对话中已触发过的关键词，防止同一句话反复触发
        self._triggered: set[str] = set()
        # 记录上一次的文字内容，用于检测是否发生了重置
        self._last_text = ""

    def check(self, text: str) -> "KeywordHit | None":
        """检查当前识别文字中是否包含关键词。

        流式场景下文字是增量追加的（例如 "我" → "我要" → "我要上架"），
        每次文字更新都会调用此方法。同一个关键词在一轮对话中只触发一次。

        参数:
            text: 当前累积的完整识别文字。

        返回:
            命中时返回 KeywordHit 对象，未命中返回 None。
        """
        # 如果文字被清空或缩短（新的一轮识别开始），重置触发记录
        if len(text) < len(self._last_text) or not text:
            self._triggered.clear()

        self._last_text = text

        if not text:
            return None

        # 遍历所有关键词规则，检查是否命中
        for keyword, reply in self._rules.items():
            if keyword in text and keyword not in self._triggered:
                self._triggered.add(keyword)
                return KeywordHit(keyword=keyword, reply=reply)

        return None

    def update_rules(self, rules: dict[str, str]) -> None:
        """动态替换所有关键词规则并重置触发状态。"""
        self._rules = dict(rules)
        self.reset()

    def get_rules(self) -> dict[str, str]:
        """返回当前规则的副本。"""
        return dict(self._rules)

    def reset(self) -> None:
        """重置触发记录，新一轮对话开始。"""
        self._triggered.clear()
        self._last_text = ""


class KeywordHit:
    """关键词命中结果。

    属性:
        keyword: 命中的关键词。
        reply: 对应的 TTS 回复文案。
    """

    def __init__(self, keyword: str, reply: str):
        self.keyword = keyword
        self.reply = reply
