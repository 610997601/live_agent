import os
import json
from .logger import get_logger, get_app_data_dir

logger = get_logger("Utils")

class ConfigManager:
    """管理本地持久化配置 (如定时弹幕规则)，支持根据 outer_id 隔离"""
    def __init__(self, outer_id):
        self.base_dir = get_app_data_dir()
        self.account_dir = os.path.join(self.base_dir, outer_id)
        os.makedirs(self.account_dir, exist_ok=True)
        self.danmu_file = os.path.join(self.account_dir, "danmu_rules.json")

    def save_danmu_rules(self, rules):
        try:
            with open(self.danmu_file, 'w', encoding='utf-8') as f:
                json.dump(rules, f, ensure_ascii=False, indent=4)
            logger.debug(f"已保存定时弹幕规则: {self.danmu_file}")
        except Exception as e:
            logger.error(f"保存弹幕规则失败: {e}")

    def load_danmu_rules(self):
        if not os.path.exists(self.danmu_file):
            return []
        try:
            with open(self.danmu_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取弹幕规则失败: {e}")
            return []

class GlobalConfig:
    """管理全局应用配置 (如音视频设备选择)"""
    _cached_voices = []

    def __init__(self):
        self.base_dir = get_app_data_dir()
        self._path = os.path.join(self.base_dir, "config.json")
        self._config = {
            "audio_input": "",
            "audio_output": ""
        }
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._config.update(data)
            except Exception as e:
                logger.error(f"读取全局配置失败: {e}")

    def _save(self):
        try:
            with open(self._path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"保存全局配置失败: {e}")

    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        self._config[key] = value
        self._save()

    @classmethod
    def set_voices(cls, voices):
        cls._cached_voices = voices

    @classmethod
    def get_voices(cls):
        # 如果缓存为空，返回一个极简的保底列表
        if not cls._cached_voices:
            return [
                {"ShortName": "zh-CN-XiaoxiaoNeural", "FriendlyName": "晓晓 (本地)"},
                {"ShortName": "zh-CN-YunxiNeural", "FriendlyName": "云希 (本地)"},
                {"ShortName": "zh-CN-YunyangNeural", "FriendlyName": "云扬 (本地)"},
            ]
        return cls._cached_voices
