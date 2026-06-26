@echo off
REM IFAnalyzer - Build Windows executable with PyInstaller
REM Run this on Windows (PyInstaller cannot cross-compile from Linux/macOS).

REM Get script directory and project root
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
for %%I in ("%SCRIPT_DIR%") do set PROJECT_ROOT=%%~dpI
set PROJECT_ROOT=%PROJECT_ROOT:~0,-1%

cd /d "%PROJECT_ROOT%"

echo ============================================================
echo IFAnalyzer - Build EXE
echo ============================================================
echo Project root: %PROJECT_ROOT%
echo.

REM Pick python launcher
where py >nul 2>nul && (set PY=py) || (set PY=python)

echo Install / update build dependencies? (Y/N)
echo (Select N if already installed)
set /p install_deps=
if /i "%install_deps%"=="Y" (
    echo.
    echo Installing runtime dependencies...
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 ( echo ERROR: pip install failed & pause & exit /b 1 )
    echo Installing PyInstaller...
    %PY% -m pip install pyinstaller
    if errorlevel 1 ( echo ERROR: pip install pyinstaller failed & pause & exit /b 1 )
)
echo.

echo Building (clean)...
%PY% -m PyInstaller --noconfirm --clean ifanalyzer.spec
if errorlevel 1 (
    echo.
    echo ERROR: build failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Build completed
echo ============================================================
echo Output folder: %PROJECT_ROOT%\dist\IFAnalyzer
echo Executable   : %PROJECT_ROOT%\dist\IFAnalyzer\IFAnalyzer.exe
echo.
echo On first run, the app creates input\ output\ and .env next to the exe.
echo Copy .env.example to .env (beside the exe) and fill in SAP AI Core
echo credentials, or set them via the in-app Settings dialog.
echo.
pause
