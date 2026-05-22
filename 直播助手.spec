# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# 定义需要全量收集的重度依赖包
datas = [
    ('live_agent', 'live_agent'), 
    ('models', 'models')
]
binaries = []
hiddenimports = [
    'PySide6', 'sherpa_onnx', 'sounddevice', 'edge_tts', 
    'pandas', 'openpyxl', 'requests', 'playwright', 'greenlet'
]

# 核心：收集那些在打包时容易丢失动态库或元数据的包
for pkg in ['playwright', 'greenlet', 'pandas', 'openpyxl', 'sherpa_onnx', 'sounddevice', 'requests']:
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
    excludes=[],
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
    console=False, # 设置为 True 可查看 Windows 下的报错日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='直播助手',
)
