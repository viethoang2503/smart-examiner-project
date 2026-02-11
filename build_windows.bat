@echo off
REM FocusGuard Windows Build Script
REM Run this on Windows to build .exe files

echo ========================================
echo FocusGuard Windows Build Script
echo ========================================

REM Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [X] Python not found! Please install Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python found

REM Create venv if not exists
if not exist "venv\Scripts\activate.bat" (
    echo.
    echo [*] Creating virtual environment...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo [*] Installing dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pyinstaller -q
echo [OK] Dependencies installed

REM Clean previous builds
echo.
echo [*] Cleaning previous builds...
if exist "dist\FocusGuard_Client" rmdir /s /q "dist\FocusGuard_Client"
if exist "dist\FocusGuard_Server" rmdir /s /q "dist\FocusGuard_Server"
if exist "build" rmdir /s /q "build"

REM Build Client
echo.
echo ========================================
echo Building FocusGuard Client...
echo ========================================
pyinstaller focusguard_client.spec --clean --noconfirm
if %ERRORLEVEL% neq 0 (
    echo [X] Client build failed!
    pause
    exit /b 1
)
echo [OK] Client build complete!

REM Build Server
echo.
echo ========================================
echo Building FocusGuard Server...
echo ========================================
pyinstaller focusguard_server.spec --clean --noconfirm
if %ERRORLEVEL% neq 0 (
    echo [X] Server build failed!
    pause
    exit /b 1
)
echo [OK] Server build complete!

REM Show results
echo.
echo ========================================
echo BUILD COMPLETE!
echo ========================================
echo.
echo Output files:
echo   Client: dist\FocusGuard_Client\FocusGuard_Client.exe
echo   Server: dist\FocusGuard_Server\FocusGuard_Server.exe
echo.
echo To run:
echo   1. Copy the entire dist\FocusGuard_Client folder to target machine
echo   2. Copy the entire dist\FocusGuard_Server folder to server machine
echo   3. Run FocusGuard_Server.exe first
echo   4. Then run FocusGuard_Client.exe on student machines
echo.
pause
