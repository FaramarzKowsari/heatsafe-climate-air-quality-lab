@echo off
setlocal EnableExtensions
title HeatSafe Scientific Pack 08.1 - Final Metadata Harmonization

set "REPO=C:\Faramarz\GitHub\11-HeatSafe\heatsafe-climate-air-quality-lab"
set "PYTHON=%REPO%\.venv\Scripts\python.exe"
set "WORKSPACE=artifacts\local-real-experiments\epa-aqs-alameda-pm25-2025-bulk"
set "SOURCE_RELEASE=artifacts\releases\epa-pm25-2025-first-real-reviewed"
set "OUTPUT=artifacts\releases\epa-airdata-california-pm25-2025-first-real-reviewed"
set "OUTPUT_FULL=%REPO%\%OUTPUT%"
set "LOG=%REPO%\artifacts\logs\scientific-pack-08-1.log"

echo.
echo ==============================================================================
echo HeatSafe Scientific Pack 08.1 - Final Metadata Harmonization
echo ==============================================================================
echo.
echo This step reuses the verified experiment and reviewed candidate.
echo It does not download EPA data, rescan the national file, rerun models,
echo publish to GitHub or Zenodo, or mint a DOI.
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
if not exist "%REPO%\%WORKSPACE%\real-official-experiment-manifest.json" (
  echo ERROR: Verified source workspace not found:
  echo %REPO%\%WORKSPACE%
  goto :fail
)
if not exist "%REPO%\%SOURCE_RELEASE%\release-summary.json" (
  echo ERROR: Scientific Pack 08 source release not found:
  echo %REPO%\%SOURCE_RELEASE%
  goto :fail
)

if not exist "%REPO%\artifacts\logs" mkdir "%REPO%\artifacts\logs"

pushd "%REPO%"
"%PYTHON%" -m heatsafe.research.release_review.cli harmonize ^
  --source-release "%SOURCE_RELEASE%" ^
  --workspace "%WORKSPACE%" ^
  --output "%OUTPUT%" ^
  --release-id "epa-airdata-california-pm25-2025-first-real-reviewed" ^
  --public-experiment-id "epa-airdata-california-pm25-2025-first-real-bulk" ^
  --version "0.1.0" ^
  --source-collection-year 2025 ^
  --local-timezone "America/Los_Angeles" ^
  --overwrite > "%LOG%" 2>&1
set "BUILD_CODE=%ERRORLEVEL%"

if not "%BUILD_CODE%"=="0" (
  type "%LOG%"
  popd
  goto :fail
)

"%PYTHON%" -m heatsafe.research.release_review.cli verify-harmonized "%OUTPUT%" >> "%LOG%" 2>&1
set "VERIFY_CODE=%ERRORLEVEL%"
popd

if not "%VERIFY_CODE%"=="0" (
  type "%LOG%"
  goto :fail
)

echo.
echo ==============================================================================
echo SUCCESS: Final metadata harmonization completed and verified.
echo ==============================================================================
echo.
echo Public release ID:
echo epa-airdata-california-pm25-2025-first-real-reviewed
echo.
echo Public experiment ID:
echo epa-airdata-california-pm25-2025-first-real-bulk
echo.
echo Selected result:
echo San Diego County, California - station 06-073-1201
echo.
echo Harmonized release:
echo %OUTPUT_FULL%
echo.
echo Harmonized ZIP:
echo %REPO%\artifacts\releases\epa-airdata-california-pm25-2025-first-real-reviewed-v0.1.0.zip
echo.
echo Review first:
echo %OUTPUT_FULL%\release-summary.html
echo %OUTPUT_FULL%\metadata\identifier-crosswalk.json
echo %OUTPUT_FULL%\metadata\time-basis.json
echo %OUTPUT_FULL%\REVIEW_CHECKLIST.md
echo.
echo No DOI has been minted.
echo.
start "" "%OUTPUT_FULL%\release-summary.html"
pause
exit /b 0

:fail
echo.
echo ==============================================================================
echo ERROR: Final metadata harmonization did not complete.
echo ==============================================================================
echo.
echo Send this log if it exists:
echo %LOG%
echo.
pause
exit /b 1
