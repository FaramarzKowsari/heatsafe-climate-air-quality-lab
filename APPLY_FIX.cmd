@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set /p REPO_PATH=Paste the full path of the HeatSafe repository and press Enter: 
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%apply_ruff_ci_fix.ps1" -RepoPath "%REPO_PATH%"
if errorlevel 1 (
  echo.
  echo The operation stopped because of an error. Read the message above.
  pause
  exit /b 1
)
echo.
echo The fix branch was pushed. If a browser opened, click Create pull request.
pause
