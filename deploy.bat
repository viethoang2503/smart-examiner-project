@echo off
REM FocusGuard Deployment Script for Windows
REM Deploys server and client

setlocal EnableDelayedExpansion

set PROJECT_DIR=%~dp0
set VENV_DIR=%PROJECT_DIR%venv

echo ========================================
echo FocusGuard Deployment Script (Windows)
echo ========================================

REM Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [X] Python not found!
    exit /b 1
)
echo [OK] Python found

REM Create virtual environment
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo.
    echo [*] Creating virtual environment...
    python -m venv "%VENV_DIR%"
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment exists
)

REM Activate venv
call "%VENV_DIR%\Scripts\activate.bat"

REM Install dependencies
echo.
echo [*] Installing dependencies...
pip install --upgrade pip -q
pip install -r "%PROJECT_DIR%requirements.txt" -q
echo [OK] Dependencies installed

REM Parse argument
if "%1"=="" set ARG=server
if not "%1"=="" set ARG=%1

if "%ARG%"=="server" goto :start_server
if "%ARG%"=="client" goto :start_client
if "%ARG%"=="install" goto :install_only
goto :usage

:install_only
echo.
echo [*] Initializing database...
python "%PROJECT_DIR%init_database.py" 2>nul || python -c "from server.database import init_db; init_db()"
echo.
echo [OK] Installation complete!
echo     Run: deploy.bat server
echo     Or:  deploy.bat client
goto :eof

:start_server
echo.
echo [*] Initializing database...
python "%PROJECT_DIR%init_database.py" 2>nul || python -c "from server.database import init_db; init_db()"
echo.
echo [*] Starting FocusGuard Server...
echo     URL: http://localhost:8000
echo     Press Ctrl+C to stop
echo.
python "%PROJECT_DIR%run_server.py"
goto :eof

:start_client
echo.
echo [*] Starting FocusGuard Client...
python "%PROJECT_DIR%run_client.py"
goto :eof

:usage
echo Usage: deploy.bat {server^|client^|install}
exit /b 1
