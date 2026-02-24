@echo off
chcp 65001 >nul
echo ========================================
echo Excel Interface Analyzer
echo ========================================
echo.
REM Get script directory and project root
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
for %%I in ("%SCRIPT_DIR%") do set PROJECT_ROOT=%%~dpI
set PROJECT_ROOT=%PROJECT_ROOT:~0,-1%

REM Change to project root
cd /d "%PROJECT_ROOT%"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python first.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo [ERROR] .env file not found.
    echo Please create .env file with SAP AI Core credentials.
    pause
    exit /b 1
)

REM Check if input folder exists
if not exist input (
    echo [WARNING] input folder not found. Creating it...
    mkdir input
)

REM Check if output folder exists
if not exist output (
    echo Creating output folder...
    mkdir output
)

REM Check if there are Excel files in input folder
dir /b input\*.xlsx input\*.xls input\*.xlsm >nul 2>&1
if errorlevel 1 (
    echo [WARNING] No Excel files found in input folder.
    echo Please place your Interface design Excel files in the input folder.
    pause
    exit /b 1
)

echo Starting analysis...
echo.
python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Analysis failed. Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Analysis completed successfully!
echo Check the output folder for results.
echo ========================================
pause
