@echo off
setlocal EnableExtensions
title Install Google Search Console Verification File

set "REPO=C:\Faramarz\GitHub\11-HeatSafe\heatsafe-climate-air-quality-lab"
set "PYTHON=%REPO%\.venv\Scripts\python.exe"
set "SELECTED=%TEMP%\heatsafe-google-verification-file.txt"

echo.
echo ==============================================================================
echo Install Google Search Console HTML Verification File
echo ==============================================================================
echo.
echo Select the googlexxxxxxxxxxxxxxxx.html file downloaded from Search Console.
echo The file name and content will be validated before it is copied.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.OpenFileDialog; $d.Title='Select Google Search Console verification file'; $d.Filter='Google verification HTML (google*.html)|google*.html|HTML files (*.html)|*.html'; if($d.ShowDialog() -eq 'OK'){[IO.File]::WriteAllText('%SELECTED%',$d.FileName)}"

if not exist "%SELECTED%" (
  echo No file was selected.
  goto :fail
)

set /p "GOOGLE_FILE="<"%SELECTED%"
del "%SELECTED%" >nul 2>&1

if not exist "%PYTHON%" (
  where python >nul 2>&1
  if errorlevel 1 (
    echo ERROR: Python was not found.
    goto :fail
  )
  set "PYTHON=python"
)

pushd "%REPO%"
"%PYTHON%" scripts\install_search_console_verification.py "%GOOGLE_FILE%" --site-root docs\site
set "CODE=%ERRORLEVEL%"
popd

if not "%CODE%"=="0" goto :fail

echo.
echo ==============================================================================
echo SUCCESS: Google verification file was installed.
echo ==============================================================================
echo.
echo Commit and push the new google*.html file.
echo Wait for GitHub Pages deployment, open the public verification URL,
echo then click Verify in Google Search Console.
echo.
pause
exit /b 0

:fail
echo.
echo Google verification file was not installed.
echo.
pause
exit /b 1
