$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Repo

$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$Workspace = "artifacts\local-real-experiments\epa-aqs-alameda-pm25-2025-bulk"
$Output = "artifacts\releases\epa-pm25-2025-first-real-reviewed"
$OutputFull = Join-Path $Repo $Output
$ExitCode = 0

try {
    Write-Host ""
    Write-Host "=============================================================================="
    Write-Host "HeatSafe Scientific Pack 08 - Reviewed Release Builder"
    Write-Host "=============================================================================="
    Write-Host ""
    Write-Host "The completed official EPA experiment will be reused."
    Write-Host "No data download, national-file scan, API key, DOI, or upload is involved."
    Write-Host ""

    if (-not (Test-Path $Python)) {
        throw "Local Python environment not found: $Python"
    }
    if (-not (Test-Path (Join-Path $Repo "$Workspace\real-official-experiment-manifest.json"))) {
        throw "Verified official experiment workspace not found: $Workspace"
    }
    if (-not (Test-Path (Join-Path $Repo "$Workspace\experiment\report\report.html"))) {
        throw "Source experiment report was not found."
    }

    Write-Host "Installing or refreshing the local repository package..."
    & $Python -m pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) {
        throw "Local package installation failed with exit code $LASTEXITCODE."
    }

    $OverwriteArgs = @()
    if (Test-Path $OutputFull) {
        Write-Host ""
        $Answer = Read-Host "A previous reviewed release exists. Replace it? Type YES to continue"
        if ($Answer -ne "YES") {
            Write-Host "Cancelled. The previous reviewed release was not changed."
            exit 0
        }
        $OverwriteArgs = @("--overwrite")
    }

    Write-Host ""
    Write-Host "Building the reviewed candidate release..."
    & $Python -m heatsafe.research.release_review.cli build `
        --workspace $Workspace `
        --output $Output `
        @OverwriteArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Reviewed release build failed with exit code $LASTEXITCODE."
    }

    Write-Host ""
    Write-Host "Verifying every reviewed-release checksum..."
    & $Python -m heatsafe.research.release_review.cli verify $Output
    if ($LASTEXITCODE -ne 0) {
        throw "Reviewed release verification failed with exit code $LASTEXITCODE."
    }

    $Summary = Join-Path $OutputFull "release-summary.html"
    $Archive = Join-Path $Repo "artifacts\releases\epa-pm25-2025-first-real-reviewed-v0.1.0.zip"

    Write-Host ""
    Write-Host "=============================================================================="
    Write-Host "SUCCESS: The reviewed candidate research release was created and verified."
    Write-Host "=============================================================================="
    Write-Host ""
    Write-Host "Review summary:"
    Write-Host $Summary
    Write-Host ""
    Write-Host "Reviewed release ZIP:"
    Write-Host $Archive
    Write-Host ""
    Write-Host "No DOI was minted and nothing was uploaded."
    Write-Host "Complete REVIEW_CHECKLIST.md before publication."
    Write-Host ""

    if (Test-Path $Summary) {
        Start-Process $Summary
    }
}
catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    $ExitCode = 1
}

exit $ExitCode
