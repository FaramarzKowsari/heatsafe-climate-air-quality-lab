@echo off
setlocal EnableExtensions
title HeatSafe Scientific Pack 09.1 - Reserved DOI Injection

set "REPO=C:\Faramarz\GitHub\11-HeatSafe\heatsafe-climate-air-quality-lab"
set "PYTHON=%REPO%\.venv\Scripts\python.exe"
set "SOURCE_RELEASE=artifacts\releases\epa-airdata-california-pm25-2025-first-real-reviewed"
set "SOURCE_HANDOFF=artifacts\publication\epa-pm25-2025-v0.1.0-handoff"
set "RELEASE_OUTPUT=artifacts\releases\epa-airdata-california-pm25-2025-first-real-reviewed-doi-final"
set "HANDOFF_OUTPUT=artifacts\publication\epa-pm25-2025-v0.1.0-doi-final-handoff"
set "DOI=10.5281/zenodo.21710054"
set "LOG=%REPO%\artifacts\logs\scientific-pack-09-1.log"

echo.
echo ==============================================================================
echo HeatSafe Scientific Pack 09.1 - Reserved DOI Injection
echo ==============================================================================
echo.
echo Reserved DOI:
echo %DOI%
echo.
echo This operation does not publish Zenodo or GitHub.
echo It rebuilds DOI-aware files and checksums only.
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
if not exist "%REPO%\%SOURCE_RELEASE%\release-summary.json" (
  echo ERROR: Harmonized release not found:
  echo %REPO%\%SOURCE_RELEASE%
  goto :fail
)
if not exist "%REPO%\%SOURCE_HANDOFF%\PUBLICATION_HANDOFF.json" (
  echo ERROR: Publication handoff not found:
  echo %REPO%\%SOURCE_HANDOFF%
  goto :fail
)

if not exist "%REPO%\artifacts\logs" mkdir "%REPO%\artifacts\logs"

pushd "%REPO%"
"%PYTHON%" -m heatsafe.research.release_review.cli finalize-reserved-doi ^
  --harmonized-release "%SOURCE_RELEASE%" ^
  --publication-handoff "%SOURCE_HANDOFF%" ^
  --release-output "%RELEASE_OUTPUT%" ^
  --handoff-output "%HANDOFF_OUTPUT%" ^
  --reserved-doi "%DOI%" ^
  --overwrite > "%LOG%" 2>&1
set "FINALIZE_CODE=%ERRORLEVEL%"

if not "%FINALIZE_CODE%"=="0" (
  type "%LOG%"
  popd
  goto :fail
)

"%PYTHON%" -m heatsafe.research.release_review.cli verify-doi-release ^
  "%RELEASE_OUTPUT%" ^
  --reserved-doi "%DOI%" >> "%LOG%" 2>&1
set "RELEASE_VERIFY=%ERRORLEVEL%"

"%PYTHON%" -m heatsafe.research.release_review.cli verify-doi-handoff ^
  "%HANDOFF_OUTPUT%" ^
  --reserved-doi "%DOI%" >> "%LOG%" 2>&1
set "HANDOFF_VERIFY=%ERRORLEVEL%"
popd

if not "%RELEASE_VERIFY%"=="0" (
  type "%LOG%"
  goto :fail
)
if not "%HANDOFF_VERIFY%"=="0" (
  type "%LOG%"
  goto :fail
)

echo.
echo ==============================================================================
echo SUCCESS: Reserved DOI injection completed and verified.
echo ==============================================================================
echo.
echo Reserved DOI:
echo %DOI%
echo.
echo DOI-aware release:
echo %REPO%\%RELEASE_OUTPUT%
echo.
echo DOI-aware ZIP:
echo %REPO%\artifacts\releases\epa-airdata-california-pm25-2025-first-real-reviewed-v0.1.0-doi-final.zip
echo.
echo DOI-aware publication handoff:
echo %REPO%\%HANDOFF_OUTPUT%
echo.
echo Open first:
echo %REPO%\%HANDOFF_OUTPUT%\DOI_FINALIZATION_READINESS.html
echo.
echo IMPORTANT:
echo Replace the old ZIP and SHA256SUMS in the existing Zenodo draft.
echo Resolve all three Basic information errors.
echo Save draft and Preview.
echo Do not press Publish yet.
echo.
start "" "%REPO%\%HANDOFF_OUTPUT%\DOI_FINALIZATION_READINESS.html"
pause
exit /b 0

:fail
echo.
echo ==============================================================================
echo ERROR: Reserved DOI finalization did not complete.
echo ==============================================================================
echo.
echo Send this log:
echo %LOG%
echo.
pause
exit /b 1
