"""直播语音助手桌面客户端入口。"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# --- 运行时环境与配置加载 ---
frozen = getattr(sys, "frozen", False)
bundle_dir = Path(sys._MEIPASS) if frozen else Path(__file__).parent
exe_dir = Path(sys.executable).parent if frozen else Path(os.getcwd())

# 优先级顺序加载 .env (Plan B 核心): 1. EXE 所在目录 2. 打包内部目录 3. 当前工作目录
env_paths = [exe_dir / ".env", bundle_dir / ".env", Path(os.getcwd()) / ".env"]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(str(env_path))
        break

# 探测并强制设置 Playwright 浏览器路径
potential_browser_paths = [
    bundle_dir / "ms-playwright",
    bundle_dir / "_internal" / "ms-playwright",
    exe_dir / "ms-playwright",
    Path(os.getcwd()) / "ms-playwright"
]

for p in potential_browser_paths:
    if p.exists():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(p)
        break

from live_agent.gui.app import main

if __name__ == "__main__":
    main()
