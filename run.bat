@echo off
REM ================================
REM Check Internet connection
REM ================================
ping -n 1 8.8.8.8 >nul 2>&1
if errorlevel 1 (
    echo ❌ No Internet connection. Please check your network and try again.
    pause
    exit /b
) else (
    echo ✅ Internet connection is available.
)

REM ================================
REM Activate virtual environment (venv)
REM ================================
call env\Scripts\activate

REM ================================
REM Run main.py
REM ================================
echo ▶ Starting main.py ...
python main.py

REM ================================
REM Wait before closing window
REM ================================
echo Program finished. Press any key to exit.
pause