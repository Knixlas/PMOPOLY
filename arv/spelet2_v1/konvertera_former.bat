@echo off
REM Konverterar PDF-formerna i Bilder\nya former\ till PNG med transparent bakgrund.
REM Output hamnar i Bilder\nya former\png\
REM
REM Kräver pymupdf och pillow — installeras automatiskt vid första körning.

cd /d "%~dp0"

REM Installera Python-paket om de saknas (tyst om redan installerat)
python -c "import fitz" 2>nul
if errorlevel 1 (
    echo Installerar pymupdf...
    python -m pip install pymupdf
)

python -c "import PIL" 2>nul
if errorlevel 1 (
    echo Installerar pillow...
    python -m pip install pillow
)

python konvertera_former_till_png.py
pause

