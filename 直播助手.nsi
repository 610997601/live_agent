; 直播助手.nsi
; 直播助手 Windows 安装包脚本

!define APP_NAME "直播助手"
!define COMP_NAME "hsuanyuen"
!define WEB_SITE "https://github.com/hsuanyuen/live_agent"
!define VERSION "1.0.0"
!define EXE_NAME "直播助手.exe"

; --- 基础设置 ---
Name "${APP_NAME}"
OutFile "直播助手_安装包_v${VERSION}.exe"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "Install_Dir"
RequestExecutionLevel admin

; --- 引入界面宏 ---
!include "MUI2.nsh"
!define MUI_ABORTWARNING

; --- 界面定制 ---
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

; --- 安装程序段 ---
Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    File /r "dist\直播助手\*.*"
    
    WriteRegStr HKLM "Software\${APP_NAME}" "Install_Dir" "$INSTDIR"
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; 创建快捷方式
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${EXE_NAME}"
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${EXE_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\卸载${APP_NAME}.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

; --- 卸载程序段 ---
Section "Uninstall"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    RMDir /r "$SMPROGRAMS\${APP_NAME}"
    RMDir /r "$INSTDIR"
    DeleteRegKey HKLM "Software\${APP_NAME}"
SectionEnd
