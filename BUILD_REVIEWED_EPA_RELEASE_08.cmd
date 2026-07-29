@echo off
setlocal EnableExtensions
title HeatSafe Scientific Pack 08 - Reviewed Release Builder

cd /d "%~dp0"

echo.
echo ==============================================================================
echo HeatSafe Scientific Pack 08 - Reviewed Release Builder
echo ==============================================================================
echo.
echo This reuses the completed local EPA experiment.
echo It does not download data, request a key, publish, upload, or mint a DOI.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0BUILD_REVIEWED_EPA_RELEASE_08.ps1"
set "CODE=%ERRORLEVEL%"

echo.
if "%CODE%"=="0" (
  echo The reviewed-release builder finished.
) else (
  echo ERROR: The reviewed-release builder stopped with exit code %CODE%.
)
echo.
pause
exit /b %CODE%
