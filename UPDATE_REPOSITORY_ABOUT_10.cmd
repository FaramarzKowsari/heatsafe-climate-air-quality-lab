@echo off
setlocal EnableExtensions
title HeatSafe Repository About Updater

set "REPO=FaramarzKowsari/heatsafe-climate-air-quality-lab"
set "ROOT=%~dp0"
set "DESCRIPTION=Open-source environmental intelligence and AI research for extreme heat, PM2.5, air quality, wildfire smoke, urban climate, forecasting, uncertainty, and resilient homes."
set "HOMEPAGE=https://faramarzkowsari.github.io/heatsafe-climate-air-quality-lab/"

echo.
echo ==============================================================================
echo Update GitHub Repository About
echo ==============================================================================
echo.
echo Repository:
echo %REPO%
echo.
echo Description:
echo %DESCRIPTION%
echo.
echo Website:
echo %HOMEPAGE%
echo.
echo Topics:
type "%ROOT%repository-topics.json"
echo.

where gh.exe >nul 2>&1
if errorlevel 1 (
  echo ERROR: GitHub CLI gh.exe was not found.
  echo Use REPOSITORY_ABOUT_VALUES.txt to update About manually.
  goto :fail
)

gh auth status
if errorlevel 1 (
  echo ERROR: GitHub CLI is not authenticated.
  echo Run: gh auth login
  goto :fail
)

set /p "CONFIRM=Type APPLY-ABOUT to update the repository About section: "
if /I not "%CONFIRM%"=="APPLY-ABOUT" (
  echo Cancelled.
  goto :fail
)

gh repo edit "%REPO%" ^
  --description "%DESCRIPTION%" ^
  --homepage "%HOMEPAGE%"
if errorlevel 1 goto :fail

gh api ^
  --method PUT ^
  -H "Accept: application/vnd.github+json" ^
  -H "X-GitHub-Api-Version: 2022-11-28" ^
  "repos/%REPO%/topics" ^
  --input "%ROOT%repository-topics.json"
if errorlevel 1 goto :fail

echo.
echo ==============================================================================
echo SUCCESS: Repository About was updated.
echo ==============================================================================
echo.
start "" "https://github.com/%REPO%"
pause
exit /b 0

:fail
echo.
echo Repository About was not changed.
echo.
pause
exit /b 1
