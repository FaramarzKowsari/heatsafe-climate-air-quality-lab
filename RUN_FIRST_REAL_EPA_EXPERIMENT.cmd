@echo off
setlocal EnableExtensions
title HeatSafe First Real EPA Experiment

cd /d "%~dp0"

echo.
echo ==============================================================================
echo HeatSafe First Real Official-Data Experiment
echo ==============================================================================
echo.
echo A secure PowerShell prompt will request your free EPA AQS credentials.
echo Credential values will not be written to the repository.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_FIRST_REAL_EPA_EXPERIMENT.ps1"
set "CODE=%ERRORLEVEL%"

echo.
if "%CODE%"=="0" (
  echo The runner finished.
) else (
  echo ERROR: The runner stopped with exit code %CODE%.
)
echo.
pause
exit /b %CODE%
