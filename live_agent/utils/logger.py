import os
import sys
import logging
import datetime
import platform
from pathlib import Path

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
        except:
            # 回退到当前目录
            app_dir = os.path.join(os.getcwd(), "data")
            os.makedirs(app_dir, exist_ok=True)
            
    return app_dir

def setup_logging():
    """初始化全局日志配置，每次启动生成一个独立文件"""
    app_data_dir = Path(get_app_data_dir())
    log_dir = app_data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 清理过旧的日志 (保留最近 10 条)
    try:
        existing_logs = sorted(log_dir.glob("*.log"), key=os.path.getmtime)
        if len(existing_logs) > 10:
            for old_log in existing_logs[:-10]:
                old_log.unlink()
    except:
        pass

    # 生成当前启动的日志文件名: 2026-05-26_14-30-05.log
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"{timestamp}.log"
    
    # 基础配置
    log_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 根记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 如果已经有 handler (防止重复初始化)，先清空
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 文件 Handler
    file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    
    # 控制台 Handler (同时输出到控制台)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO) # 控制台可以设稍微高一点
    root_logger.addHandler(console_handler)

    logging.info(f"=== 软件启动 - 日志文件: {log_file} ===")
    return root_logger

# 快捷获取 logger 的方法
def get_logger(name):
    return logging.getLogger(name)
