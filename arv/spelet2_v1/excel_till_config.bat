@echo off
REM excel_till_config.bat
REM Körs av master_kortproduktion.jsx som första steg.
REM Läser Bilder\färgschema.xlsx och skapar/uppdaterar utskrift_config.json
REM
REM Synkront: JSX väntar på att detta ska bli klart innan den fortsätter.

setlocal

REM SPELET 2-roten = mappen där denna .bat-fil ligger
set "ROT=%~dp0"
set "SCRIPT=%ROT%excel_till_config.py"

if not exist "%SCRIPT%" (
    echo FEL: %SCRIPT% saknas
    exit /b 1
)

python "%SCRIPT%" "%ROT%"
set RC=%ERRORLEVEL%

if %RC% neq 0 (
    echo excel_till_config.py misslyckades med kod %RC%
    exit /b %RC%
)

exit /b 0

