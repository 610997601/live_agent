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
set PLAYWRIGHT_BROWSERS_PATH=0

echo [*] Syncing dependencies with uv...
uv sync

echo [*] Ensuring browser kernel is ready...
uv run playwright install chromium

:: 3. Packaging
echo [*] Running PyInstaller with build.spec...
echo [!] This process may take several minutes, please wait...
uv run pyinstaller --noconfirm --clean build.spec

echo.
echo ===================================================
echo [OK] Build Finished!
echo Result location: dist\直播助手\
echo Executable:      dist\直播助手\直播助手.exe
echo ===================================================
echo.
echo [Note]:
echo 1. Ensure models/ directory contains full ASR models before running.
echo 2. If app fails to start, change 'console=False' to 'True' in build.spec and rebuild to see logs.
echo.

pause
endlocal
