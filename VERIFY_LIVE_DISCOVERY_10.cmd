@echo off
setlocal EnableExtensions
title Verify HeatSafe Public Discovery Files

set "BASE=https://faramarzkowsari.github.io/heatsafe-climate-air-quality-lab"
set "FAILED=0"

echo.
echo ==============================================================================
echo Verify Public Discovery Files
echo ==============================================================================
echo.

for %%U in (
  "%BASE%/"
  "%BASE%/robots.txt"
  "%BASE%/sitemap.xml"
  "%BASE%/sitemap.txt"
  "%BASE%/site.webmanifest"
  "%BASE%/assets/favicon-96.png"
  "%BASE%/assets/heatsafe-social-card.png"
  "%BASE%/dataset/epa-pm25-san-diego-v0-1-0/"
) do (
  powershell -NoProfile -Command ^
    "try{$r=Invoke-WebRequest -UseBasicParsing -Method Head -Uri '%%~U' -TimeoutSec 30; Write-Host ('OK  ' + $r.StatusCode + '  %%~U')}catch{Write-Host ('FAIL  %%~U'); exit 1}"
  if errorlevel 1 set "FAILED=1"
)

echo.
if "%FAILED%"=="1" (
  echo One or more public files are not available yet.
  echo Wait for Deploy documentation pages to finish and run this again.
  pause
  exit /b 1
)

echo ==============================================================================
echo SUCCESS: Public discovery files are reachable.
echo ==============================================================================
echo.
pause
exit /b 0
