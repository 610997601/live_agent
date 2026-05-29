import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from live_agent.utils import get_app_data_dir

@dataclass
class CloneVoice:
    """人声复刻素材模型"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    remark: str = ""
    cdn_url: str = ""
    md5: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "remark": self.remark,
            "cdn_url": self.cdn_url,
            "md5": self.md5,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CloneVoice":
        return cls(
            id=d.get("id", uuid.uuid4().hex[:8]),
            name=d.get("name", ""),
            remark=d.get("remark", ""),
            cdn_url=d.get("cdn_url", ""),
            md5=d.get("md5", ""),
        )

class CloneVoiceStore(QObject):
    """管理复刻声音的本地存储 (clone_voices.json)"""
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._dir = Path(get_app_data_dir())
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "clone_voices.json"
        self._voices: list[CloneVoice] = []
        self._load()

    def _load(self):
        if not self._path.exists():
            self._voices = []
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._voices = [CloneVoice.from_dict(v) for v in data.get("voices", [])]
        except Exception as e:
            print(f"[CloneVoiceStore] Load error: {e}")
            self._voices = []

    def _save(self):
        data = {
            "version": 1,
            "voices": [v.to_dict() for v in self._voices],
        }
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.changed.emit()

    def get_all(self) -> list[CloneVoice]:
        return list(self._voices)

    def add(self, voice: CloneVoice):
        # 根据 MD5 去重
        for v in self._voices:
            if v.md5 == voice.md5:
                # 如果 MD5 相同，则更新现有信息（除 ID 外）
                v.name = voice.name
                v.remark = voice.remark
                v.cdn_url = voice.cdn_url
                self._save()
                return
        self._voices.append(voice)
        self._save()

    def update(self, voice: CloneVoice):
        for i, v in enumerate(self._voices):
            if v.id == voice.id:
                self._voices[i] = voice
                self._save()
                return

    def delete(self, voice_id: str):
        self._voices = [v for v in self._voices if v.id != voice_id]
        self._save()

    def import_data(self, external_voices_list: list[dict]):
        """导入外部数据并合并"""
        count = 0
        for d in external_voices_list:
            new_v = CloneVoice.from_dict(d)
            # 根据 MD5 去重合并
            exists = False
            for v in self._voices:
                if v.md5 == new_v.md5:
                    v.name = new_v.name or v.name
                    v.remark = new_v.remark or v.remark
                    v.cdn_url = new_v.cdn_url or v.cdn_url
                    exists = True
                    break
            if not exists:
                self._voices.append(new_v)
                count += 1
        if count > 0:
            self._save()
        return count
