@echo off
REM === ÅKEPOL - skapa Outlook-utkast ===
REM Dubbelklicka denna fil för att köra skapa_utkast.ps1
REM
REM Argument du kan skicka in (annars körs alla 51):
REM   skapa mail.bat                  -> alla 51 utkast
REM   skapa mail.bat -DryRun          -> visa bara, skapa inget
REM   skapa mail.bat -TestOne         -> bara första mottagaren
REM   skapa mail.bat -OnlyId M15      -> en specifik mottagare

chcp 65001 > nul
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\skapa_utkast.ps1" %*

echo.
echo ===========================================
pause

