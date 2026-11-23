@echo off
REM ═══════════════════════════════════════════════════════════════════════
REM  synka_skript_till_indesign.bat
REM
REM  Kopierar alla .jsx-filer från denna mapp (Mallar Indesign) till
REM  InDesigns Scripts Panel-mapp så att uppdaterade skript blir
REM  tillgängliga via skript-panelen i InDesign.
REM
REM  Kör efter ändringar i scripten. Ingen omstart av InDesign krävs —
REM  Scripts Panel ser nya/uppdaterade filer direkt.
REM ═══════════════════════════════════════════════════════════════════════

set "KÄLLA=%~dp0"
set "MÅL=%APPDATA%\Adobe\InDesign\Version 21.0\sv_SE\Scripts\Scripts Panel\PMOPOLY_scripts"

if not exist "%MÅL%" (
    echo Skapar målmapp: %MÅL%
    mkdir "%MÅL%"
)

echo.
echo Kopierar .jsx-filer:
echo   FRAN: %KÄLLA%
echo   TILL: %MÅL%
echo.

xcopy /Y /D "%KÄLLA%*.jsx" "%MÅL%\"

echo.
echo Klart. Tryck en tangent för att stänga.
pause >nul

