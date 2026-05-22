import os
import platform
import logging
import json

logger = logging.getLogger("Utils")

def get_app_data_dir():
    """获取跨平台的应用数据存储目录"""
    system = platform.system()
    if system == "Windows":
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    elif system == "Darwin":
        base = os.path.expanduser('~/Library/Application Support')
    else:
        # Linux 遵循 XDG 规范
        base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    
    app_dir = os.path.join(base, "BuyinAssistant")

    if not os.path.exists(app_dir):
        try:
            os.makedirs(app_dir, exist_ok=True)
            logger.info(f"创建应用数据目录: {app_dir}")
        except Exception as e:
            logger.error(f"无法创建数据目录: {e}")
            # 回退到当前目录
            app_dir = os.path.join(os.getcwd(), "data")
            os.makedirs(app_dir, exist_ok=True)
            
    return app_dir

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
