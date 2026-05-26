"""规则数据模型与 JSON 持久化存储。"""

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, Signal


from live_agent.utils import get_app_data_dir

@dataclass
class Rule:
    """单条关键词触发规则。"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    keyword: str = ""
    reply: str = ""
    voice: str = "zh-CN-YunxiNeural"
    rate: str = "+0%"
    reply_type: str = "tts"  # "tts" 或 "record"
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "keyword": self.keyword,
            "reply": self.reply,
            "voice": self.voice,
            "rate": self.rate,
            "reply_type": self.reply_type,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Rule":
        return cls(
            id=d.get("id", uuid.uuid4().hex[:8]),
            keyword=d.get("keyword", ""),
            reply=d.get("reply", ""),
            voice=d.get("voice", "zh-CN-YunxiNeural"),
            rate=d.get("rate", "+0%"),
            reply_type=d.get("reply_type", "tts"),
            enabled=d.get("enabled", True),
        )


DEFAULT_RULES = [
    Rule(keyword="上架", reply="货品已经上架了，大家快抢啊", voice="zh-CN-YunxiNeural"),
    Rule(keyword="下架", reply="货品已经下架了，别看了", voice="zh-CN-YunyangNeural"),
    Rule(keyword="秒杀", reply="限时秒杀开始，库存不多手慢无！", voice="zh-CN-YunxiNeural", rate="+30%"),
    Rule(keyword="优惠券", reply="优惠券已经发放，先到先得哦", voice="zh-CN-XiaohanNeural"),
    Rule(keyword="谢谢大家", reply="感谢各位的支持，我们下次直播再见！", voice="zh-CN-XiaoxiaoNeural"),
    Rule(keyword="你是谁", reply="我是直播小助手，随时为您播报商品信息", voice="zh-CN-XiaoyanNeural"),
]


class RuleStore(QObject):
    """规则持久化存储，提供 CRUD 操作并发射变更信号。"""

    rules_changed = Signal()

    def __init__(self, storage_dir: Path | None = None):
        super().__init__()
        if storage_dir is None:
            storage_dir = Path(get_app_data_dir())
        self._dir = Path(storage_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "rules.json"
        self._rules: list[Rule] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            self._rules = [Rule(
                id=r.id, keyword=r.keyword, reply=r.reply,
                voice=r.voice, rate=r.rate,
            ) for r in DEFAULT_RULES]
            self._save()
            return
        data = json.loads(self._path.read_text(encoding="utf-8"))
        self._rules = [Rule.from_dict(r) for r in data.get("rules", [])]

    def _save(self) -> None:
        data = {
            "version": 1,
            "rules": [r.to_dict() for r in self._rules],
        }
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.rules_changed.emit()

    def get_all(self) -> list[Rule]:
        return list(self._rules)

    def get_by_id(self, rule_id: str) -> Rule | None:
        for r in self._rules:
            if r.id == rule_id:
                return r
        return None

    def get_by_keyword(self, keyword: str) -> Rule | None:
        for r in self._rules:
            if r.keyword == keyword:
                return r
        return None

    def get_keyword_replies(self) -> dict[str, str]:
        return {r.keyword: r.reply for r in self._rules}

    def add(self, rule: Rule) -> None:
        self._rules.append(rule)
        self._save()

    def update(self, rule: Rule) -> None:
        for i, r in enumerate(self._rules):
            if r.id == rule.id:
                self._rules[i] = rule
                self._save()
                return

    def delete(self, rule_id: str) -> None:
        self._rules = [r for r in self._rules if r.id != rule_id]
        self._save()

    @property
    def storage_dir(self) -> Path:
        return self._dir
