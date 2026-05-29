@echo off
chcp 65001 > nul
setlocal

echo ===================================================
echo   Live Assistant Windows Build Script
echo ===================================================

:: 1. Cleanup
echo [*] Cleaning old builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

:: 2. Environment Setup
:: Force Playwright to install browsers in the project directory
set PLAYWRIGHT_BROWSERS_PATH=ms-playwright

echo [*] Syncing dependencies with uv...
uv sync

echo [*] Ensuring browser kernel is ready...
uv run playwright install chromium

echo [*] Ensuring ASR models are ready...
uv run python -c "from live_agent.asr import _download_model; from pathlib import Path; _download_model(Path('models'))"

:: 3. Packaging
echo [*] Running PyInstaller with build.spec...
echo [!] This process may take several minutes, please wait...
uv run pyinstaller --noconfirm --clean build.spec

echo.
echo ===================================================
echo [OK] Build Finished!
echo Result location: dist\LiveAssistant\
echo Executable:      dist\LiveAssistant\直播助手.exe
echo ===================================================
echo.
echo [Note]:
echo 1. Browser drivers and ASR models are now bundled in the dist folder.
echo 2. If app fails to start, change 'console=False' to 'True' in build.spec and rebuild to see logs.
echo.

pause
endlocal
