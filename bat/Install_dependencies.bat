@echo off
REM EBS Design Document Analysis and Merge Tool - Quick Start

REM Get script directory and project root
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
for %%I in ("%SCRIPT_DIR%") do set PROJECT_ROOT=%%~dpI
set PROJECT_ROOT=%PROJECT_ROOT:~0,-1%

REM Change to project root
cd /d "%PROJECT_ROOT%"

echo ============================================================
echo EBS Merge Tool - Quick Start
echo ============================================================
echo.

REM Install dependencies
echo Install dependencies? (Y/N)
echo (Select N if already installed)
set /p install_deps=
if /i "%install_deps%"=="Y" (
    echo.
    echo Installing...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Installation failed
        pause
        exit /b 1
    )
    echo.
    echo Installation completed
)
echo.

echo ============================================================
echo Setup completed!
echo ============================================================
echo.
echo Run the tool now? (Y/N)
set /p run_now=
if /i "%run_now%"=="Y" (
    echo.
    call "%SCRIPT_DIR%\run_merge.bat"
) else (
    echo.
    echo To run the tool, execute:
    echo   run_extract.bat
    echo.
    echo Or:
    echo   python -m ebs_merger
    echo.
    pause
)
