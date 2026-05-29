# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os

# 获取当前绝对路径
curr_dir = os.path.abspath('.')

# --- 1. 数据文件定义 ---
datas = [
    ('live_agent', 'live_agent'),           # 业务逻辑代码
    ('models/whisper', 'models/whisper'),   # 仅打包生效的 Whisper 模型
    ('ms-playwright', 'ms-playwright'),     # 浏览器驱动
    ('icon.png', '.')                       # 图标
]

binaries = []
hiddenimports = [
    'PySide6', 'PySide6.QtMultimedia', 'sounddevice', 'edge_tts', 
    'pandas', 'openpyxl', 'requests', 'playwright', 'greenlet',
    'faster_whisper', 'ctranslate2'
]

# --- 2. 核心依赖自动收集 ---
# 确保这些重度依赖的 DLL 和元数据被完整抓取
# 移除了 vosk, torch, funasr, sherpa 等多余依赖
for pkg in ['playwright', 'greenlet', 'pandas', 'openpyxl', 'faster_whisper', 'ctranslate2', 'sounddevice', 'requests', 'onnxruntime']:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    ['run_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'vosk', 'funasr', 'sherpa_onnx', 'matplotlib', 'IPython'], # 显式排除已弃用的库
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='直播助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # 保持开启，方便看 ASR 识别日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(curr_dir, 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LiveAssistant',
)
