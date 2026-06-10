@echo off
setlocal enabledelayedexpansion
set VENV_DIR=venv
set SCRIPT_NAME=SnakeMan.py

set LOG_FILE=startup.log

echo.
echo ========================================
echo      Apps Distributor Launcher
echo ========================================
echo.
echo Initializing...

REM 1. Create venv if missing
if not exist "%VENV_DIR%" (
    echo Configuring new environment...
    python -m venv %VENV_DIR%
)

REM 2. Activate the virtual environment
echo Activating...
call %VENV_DIR%\Scripts\activate.bat

REM 3. Install dependencies
echo Installing tools...
#python.exe -m pip install --upgrade pip
python -m pip install --disable-pip-version-check -q pygame
python -m pip install --disable-pip-version-check -q pyyaml

REM 4. Verification Step
echo Verifying tools...

python -c "import pygame" >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo Error: Failed to install pygame. Retrying...
    python -m pip install pygame
)

python -c "import pyyaml" >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo Error: Failed to install pyyaml. Retrying...
    python -m pip install pyyaml
)



REM 5. Pre-flight downloads

REM 6. Launch
echo.
echo Launching %SCRIPT_NAME%...
if not exist "%SCRIPT_NAME%" (
    echo Error: %SCRIPT_NAME% not found
    call %VENV_DIR%\Scripts\deactivate
    exit /b 1
)

python %SCRIPT_NAME% %*
set EXIT_CODE=%ERRORLEVEL%

REM 7. Teardown
echo.
call %VENV_DIR%\Scripts\deactivate

if %EXIT_CODE% EQU 0 (
    echo Session ended cleanly
) else (
    echo Warning: Script exited with code %EXIT_CODE%
)

exit /b %EXIT_CODE%
pause