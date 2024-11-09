@echo off
setlocal enabledelayedexpansion
title PolGen

echo Welcome to the PolGen Installer!
echo.

set "PRINCIPAL=%cd%"
set "MINICONDA_DIR=%UserProfile%\Miniconda3"
set "ENV_DIR=%PRINCIPAL%\env"
set "MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-py310_24.7.1-0-Windows-x86_64.exe"
set "CONDA_EXE=%MINICONDA_DIR%\Scripts\conda.exe"

call :install_miniconda
call :create_conda_env
call :install_dependencies
call :installing_necessary_models

echo PolGen has been installed successfully!
echo To start PolGen, please run 'PolGen.exe'.
echo.
pause
exit /b 0

:install_miniconda
if exist "%MINICONDA_DIR%" (
    echo Miniconda already installed. Skipping installation.
    exit /b 0
)

echo Miniconda not found. Starting download and installation...
powershell -Command "& {Invoke-WebRequest -Uri '%MINICONDA_URL%' -OutFile 'miniconda.exe'}"
if not exist "miniconda.exe" goto :download_error

start /wait "" miniconda.exe /InstallationType=JustMe /RegisterPython=0 /S /D=%MINICONDA_DIR%
if errorlevel 1 goto :install_error

del miniconda.exe
echo Miniconda installation complete.
echo.
exit /b 0

:create_conda_env
echo Creating Conda environment...
call "%MINICONDA_DIR%\_conda.exe" create --no-shortcuts -y -k --prefix "%ENV_DIR%" python=3.10
if errorlevel 1 goto :error
echo Conda environment created successfully.
echo.

if exist "%ENV_DIR%\python.exe" (
    echo Installing specific pip version...
    "%ENV_DIR%\python.exe" -m pip install "pip<24.1"
    if errorlevel 1 goto :error
    echo Pip installation complete.
    echo.
)
exit /b 0

:install_dependencies
echo Installing dependencies...
call "%MINICONDA_DIR%\condabin\conda.bat" activate "%ENV_DIR%" || goto :error
pip install --upgrade setuptools || goto :error
pip install -r "%PRINCIPAL%\requirements.txt" || goto :error
pip install torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 --upgrade --index-url https://download.pytorch.org/whl/cu121 || goto :error
call "%MINICONDA_DIR%\condabin\conda.bat" deactivate
echo Dependencies installation complete.
echo.
exit /b 0

:installing_necessary_models
echo Checking for required models...
set "hubert_base=%PRINCIPAL%\rvc\models\embedders\hubert_base.pt"
set "fcpe=%PRINCIPAL%\rvc\models\predictors\fcpe.pt"
set "rmvpe=%PRINCIPAL%\rvc\models\predictors\rmvpe.pt"

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
    if errorlevel 1 goto :download_error
)
echo.
exit /b 0

:download_error
echo.
echo Download failed. Please check your internet connection and try again.
goto :error

:install_error
echo.
echo Miniconda installation failed.
goto :error

:error
echo.
echo An error occurred during installation. Please check the output above for details.
pause
exit /b 1
