"""直播语音助手桌面客户端入口。"""

import os
import sys
from pathlib import Path

# --- 运行时环境设置 ---
if getattr(sys, "frozen", False):
    # PyInstaller 打包后的临时目录
    bundle_dir = Path(sys._MEIPASS)
    
    # PyInstaller 6.x 在 onedir 模式下会将数据放入 _internal 文件夹
    browsers_path = bundle_dir / "ms-playwright"
    if not browsers_path.exists():
        browsers_path = bundle_dir / "_internal" / "ms-playwright"
    
    # 强制 Playwright 使用打包进去的浏览器驱动
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)

from live_agent.gui.app import main

if __name__ == "__main__":
    main()
