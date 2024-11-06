@echo off
setlocal enabledelayedexpansion
title PolGen

if not exist env (
    echo Please run 'run-install.bat' first to set up the environment.
    pause
    exit /b 1
)

call :check_internet_connection
call :installing_necessary_models
call :running_interface

:check_internet_connection
echo Checking internet connection...
ping -n 1 google.com >nul 2>&1
if errorlevel 1 (
    echo No internet connection detected.
    set "INTERNET_AVAILABLE=0"
) else (
    echo Internet connection is available.
    set "INTERNET_AVAILABLE=1"
)
echo.
exit /b 0

:installing_necessary_models
echo Checking for required models...
set "hubert_base=%cd%\rvc\models\embedders\hubert_base.pt"
set "fcpe=%cd%\rvc\models\predictors\fcpe.pt"
set "rmvpe=%cd%\rvc\models\predictors\rmvpe.pt"

if exist "%hubert_base%" (
    if exist "%fcpe%" (
        if exist "%rmvpe%" (
            echo All required models are installed.
        )
    )
) else (
    echo Required models were not found. Installing models...
    echo.
    env\python download_models.py
    if errorlevel 1 goto :error
)
echo.
exit /b 0

:running_interface
echo Running Interface...
if "%INTERNET_AVAILABLE%"=="1" (
    echo Running app.py...
    env\python app.py --open
) else (
    echo Running app_offline.py...
    env\python app_offline.py --open
)

:error
echo.
echo An error occurred during the process. Exiting the script...
pause
exit /b 1