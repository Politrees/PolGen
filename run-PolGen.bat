@echo off
setlocal enabledelayedexpansion
title PolGen
cd /d "%~dp0"

REM ===== Unicode-safe console (fix tqdm/Gradio UnicodeEncodeError) =====
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if not exist env\python.exe (
    echo Error: Virtual environment not found or incomplete.
    echo Please run 'run-PolGen-installer.bat' first to set up the environment.
    pause
    exit /b 1
)

set PYTHON=env\python.exe
set SCRIPT=app.py

call :check_internet_connection
call :running_interface
exit /b 0

:check_internet_connection
echo Checking internet connection...
ping -n 1 google.com >nul 2>&1 && (
    echo Internet connection is available
    set "INTERNET_AVAILABLE=1"
    goto :check_end
)
echo No internet connection detected
set "INTERNET_AVAILABLE=0"
:check_end
echo.
exit /b 0

:running_interface
cls
echo ==== Starting Application ====

if not exist %SCRIPT% (
    echo Critical Error: Main script %SCRIPT% not found!
    pause
    exit /b 1
)

if "%INTERNET_AVAILABLE%"=="0" (
    echo Starting in OFFLINE mode...
    %PYTHON% %SCRIPT% --offline
) else (
    echo Starting in ONLINE mode...
    %PYTHON% %SCRIPT%
)

if errorlevel 1 (
    echo Error: Application failed to start (Error code: %errorlevel%)
    pause
    exit /b 1
)

exit /b 0