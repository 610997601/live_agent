@echo off
chcp 65001 > nul
setlocal
echo ===================================================
echo   直播助手 Windows 统一打包脚本 (ASR + Playwright)
echo ===================================================

:: 1. 环境准备与清理
echo [*] 正在清理旧的打包产物...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

:: 2. 关键环境变量设置
:: 强制将 Playwright 浏览器内核安装到虚拟环境目录下，以便 PyInstaller 能够收集
set PLAYWRIGHT_BROWSERS_PATH=0

echo [*] 正在同步依赖环境...
uv sync

echo [*] 正在确保浏览器内核已就绪...
uv run playwright install chromium

:: 3. 运行打包
echo [*] 正在通过 .spec 文件执行打包 (此过程较慢，请耐心等待)...
:: 使用 spec 文件可以更精准地控制 sherpa_onnx 和 playwright 的复杂依赖
uv run pyinstaller --noconfirm --clean 直播助手.spec

echo.
echo ===================================================
echo [OK] 打包完成！
echo产物位置: dist\直播助手
echo运行程序: dist\直播助手\直播助手.exe
echo ===================================================
echo.
echo [!] 注意：
echo 1. 运行前请确保 models/ 目录下已下载完整的语音模型。
echo 2. 如果启动报错，请将 .spec 文件中的 console=False 改为 True 重新打包查看日志。
echo.

pause
endlocal
