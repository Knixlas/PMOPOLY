@echo off
echo ========================================
echo   PMOPOLY - Husbyggspelet Online
echo ========================================
echo.

cd /d %~dp0

REM Install dependencies if needed
pip install -r backend\requirements.txt --quiet 2>nul

echo Starting server on http://localhost:8000
echo.
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
