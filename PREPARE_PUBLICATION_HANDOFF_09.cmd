@echo off
setlocal EnableExtensions
title HeatSafe Scientific Pack 09 - Publication Handoff

set "REPO=C:\Faramarz\GitHub\11-HeatSafe\heatsafe-climate-air-quality-lab"
set "PYTHON=%REPO%\.venv\Scripts\python.exe"
set "RELEASE=artifacts\releases\epa-airdata-california-pm25-2025-first-real-reviewed"
set "OUTPUT=artifacts\publication\epa-pm25-2025-v0.1.0-handoff"
set "OUTPUT_FULL=%REPO%\%OUTPUT%"
set "LOG=%REPO%\artifacts\logs\scientific-pack-09.log"

echo.
echo ==============================================================================
echo HeatSafe Scientific Pack 09 - Publication Handoff and Draft Creation
echo ==============================================================================
echo.
echo This stage prepares drafts only.
echo It does not publish GitHub, publish Zenodo, or mint a DOI.
echo.

if not exist "%REPO%\.git\config" (
  echo ERROR: Repository not found:
  echo %REPO%
  goto :fail
)
if not exist "%PYTHON%" (
  echo ERROR: Local Python environment not found:
  echo %PYTHON%
  goto :fail
)
if not exist "%REPO%\%RELEASE%\release-summary.json" (
  echo ERROR: Harmonized release not found:
  echo %REPO%\%RELEASE%
  goto :fail
)
if not exist "%REPO%\artifacts\logs" mkdir "%REPO%\artifacts\logs"

pushd "%REPO%"
"%PYTHON%" -m heatsafe.research.release_review.cli prepare-publication ^
  --harmonized-release "%RELEASE%" ^
  --output "%OUTPUT%" ^
  --repository "FaramarzKowsari/heatsafe-climate-air-quality-lab" ^
  --tag "epa-pm25-2025-v0.1.0" ^
  --overwrite > "%LOG%" 2>&1
set "BUILD_CODE=%ERRORLEVEL%"

if not "%BUILD_CODE%"=="0" (
  type "%LOG%"
  popd
  goto :fail
)

"%PYTHON%" -m heatsafe.research.release_review.cli verify-publication "%OUTPUT%" >> "%LOG%" 2>&1
set "VERIFY_CODE=%ERRORLEVEL%"
popd

if not "%VERIFY_CODE%"=="0" (
  type "%LOG%"
  goto :fail
)

echo.
echo ==============================================================================
echo SUCCESS: Draft-only publication handoff created and verified.
echo ==============================================================================
echo.
echo Handoff folder:
echo %OUTPUT_FULL%
echo.
echo Review:
echo %OUTPUT_FULL%\PUBLICATION_READINESS.html
echo %OUTPUT_FULL%\GITHUB_RELEASE_NOTES.md
echo %OUTPUT_FULL%\ZENODO_DRAFT_FORM_GUIDE.md
echo %OUTPUT_FULL%\PUBLICATION_SEQUENCE.md
echo.
echo Draft helpers:
echo %OUTPUT_FULL%\CREATE_GITHUB_DRAFT_RELEASE_09.cmd
echo %OUTPUT_FULL%\OPEN_ZENODO_DRAFT_09.cmd
echo.
echo Do not publish either draft.
echo.
start "" "%OUTPUT_FULL%\PUBLICATION_READINESS.html"
pause
exit /b 0

:fail
echo.
echo ==============================================================================
echo ERROR: Scientific Pack 09 handoff did not complete.
echo ==============================================================================
echo.
echo Send this log if it exists:
echo %LOG%
echo.
pause
exit /b 1
