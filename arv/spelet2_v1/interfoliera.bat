@echo off
REM interfoliera.bat
REM Kör interfoliera_pdf.py från SPELET 2-roten (samma mapp som denna .bat).
REM PDF-mappen är SPELET 2\PDF\.

setlocal

REM %~dp0 = mappen där denna .bat-fil ligger, inkl. avslutande backslash
set "ROT=%~dp0"
set "SCRIPT=%ROT%interfoliera_pdf.py"
set "PDF_MAPP=%ROT%PDF"

echo === Interfoliering + Master-PDF ===
echo.

if not exist "%SCRIPT%" (
    echo FEL: %SCRIPT% saknas
    pause
    exit /b 1
)

"C:\Users\niklas.sviden\AppData\Local\Python\pythoncore-3.14-64\python.exe" "%SCRIPT%" "%PDF_MAPP%"

echo.
echo Klart! Tryck valfri tangent...
pause >nul

