!include "MUI2.nsh"

; ---------------------------------------------------------------------------
; AI Database Architect - NSIS installer script (x64 desktop build)
; ---------------------------------------------------------------------------
!define APP_NAME        "AI Database Architect"
!define APP_SHORT_NAME  "AIDatabaseArchitect"
!define VERSION         "1.1.0"
!define PUBLISHER       "sleepy-ailurus"
!define SRC_EXE         "${__FILEDIR__}\backend\dist_pwv\AIDatabaseArchitect.exe"
!define ICO             "${__FILEDIR__}\icon\show.ico"
!define OUT_FILE        "${__FILEDIR__}\Installer\AIDatabaseArchitect-x64-Setup.exe"

Name          "${APP_NAME}"
OutFile       "${OUT_FILE}"
InstallDir    "$LOCALAPPDATA\${APP_SHORT_NAME}"
RequestExecutionLevel user
SetCompressor lzma

; UI settings
!define MUI_ICON   "${ICO}"
!define MUI_UNICON "${ICO}"
!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "SimpChinese"

; ---------------------------------------------------------------------------
; Install section
; ---------------------------------------------------------------------------
Section "Install"
  SetOutPath "$INSTDIR"
  File "${SRC_EXE}"

  ; Write the uninstaller executable
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Start menu + desktop shortcuts
  CreateDirectory "$SMPROGRAMS\${APP_SHORT_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_SHORT_NAME}\${APP_NAME}.lnk" \
                 "$INSTDIR\${APP_SHORT_NAME}.exe" "" "${ICO}" 0
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" \
                 "$INSTDIR\${APP_SHORT_NAME}.exe" "" "${ICO}" 0

  ; Register in "Apps & features" / Add or Remove Programs
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_SHORT_NAME}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_SHORT_NAME}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_SHORT_NAME}" "DisplayIcon" "${ICO}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_SHORT_NAME}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_SHORT_NAME}" "DisplayVersion" "${VERSION}"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_SHORT_NAME}" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_SHORT_NAME}" "NoRepair" 1
SectionEnd

; ---------------------------------------------------------------------------
; Uninstall section
; ---------------------------------------------------------------------------
Section "Uninstall"
  Delete "$INSTDIR\${APP_SHORT_NAME}.exe"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir  "$INSTDIR"

  Delete "$SMPROGRAMS\${APP_SHORT_NAME}\${APP_NAME}.lnk"
  RMDir  "$SMPROGRAMS\${APP_SHORT_NAME}"
  Delete "$DESKTOP\${APP_NAME}.lnk"

  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_SHORT_NAME}"
SectionEnd
