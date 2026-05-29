"""直播语音助手桌面客户端入口。"""

import os
import sys
from pathlib import Path

# --- 运行时环境设置 ---
bundle_dir = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent

# 探测顺序：1. 压缩包根目录 2. _internal 目录 (PyInstaller 6) 3. 项目根目录
potential_paths = [
    bundle_dir / "ms-playwright",
    bundle_dir / "_internal" / "ms-playwright",
    Path(os.getcwd()) / "ms-playwright"
]

for p in potential_paths:
    if p.exists():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(p)
        break

from live_agent.gui.app import main

if __name__ == "__main__":
    main()
