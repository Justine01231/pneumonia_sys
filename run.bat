@echo off
echo ========================================
echo MediScan Pneumonia Detection System
echo ========================================
echo.

REM Check if virtual environment exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo No virtual environment found.
    echo Run setup first: python -m venv venv
    echo.
)

echo Starting Flask server...
echo.
python app.py

pause
