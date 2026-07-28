$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Repo

$ExitCode = 0
$Bstr = [IntPtr]::Zero
$PlainKey = $null

try {
    Write-Host ""
    Write-Host "=============================================================================="
    Write-Host "HeatSafe First Real Official-Data Experiment"
    Write-Host "US EPA AQS Alameda County PM2.5 - 2025"
    Write-Host "=============================================================================="
    Write-Host ""
    Write-Host "Credentials are kept only in this PowerShell process."
    Write-Host "They are not written to repository files, plans, snapshots, or reports."
    Write-Host ""

    $Python = Join-Path $Repo ".venv\Scripts\python.exe"

    if (-not (Test-Path $Python)) {
        Write-Host "Creating local Python virtual environment..."
        $Launcher = Get-Command py -ErrorAction SilentlyContinue

        if ($Launcher) {
            & py -3 -m venv .venv
        }
        else {
            & python -m venv .venv
        }

        if ($LASTEXITCODE -ne 0) {
            throw "Python virtual environment creation failed with exit code $LASTEXITCODE."
        }
    }

    if (-not (Test-Path $Python)) {
        throw "Python virtual environment could not be created."
    }

    Write-Host "Installing or refreshing HeatSafe development dependencies..."
    & $Python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "pip upgrade failed with exit code $LASTEXITCODE."
    }

    & $Python -m pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) {
        throw "HeatSafe dependency installation failed with exit code $LASTEXITCODE."
    }

    $Workspace = Join-Path $Repo "artifacts\local-real-experiments\epa-aqs-alameda-pm25-2025"
    $Overwrite = $false

    if (Test-Path $Workspace) {
        Write-Host ""
        $Answer = Read-Host "A previous local run exists. Replace it? Type YES to continue"
        if ($Answer -ne "YES") {
            Write-Host "Cancelled. The previous workspace was not changed."
            exit 0
        }
        $Overwrite = $true
    }

    Write-Host ""
    $Email = Read-Host "EPA AQS account email"
    if ([string]::IsNullOrWhiteSpace($Email)) {
        throw "EPA AQS account email cannot be empty."
    }

    $SecureKey = Read-Host "EPA AQS API key" -AsSecureString
    $Bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureKey)
    $PlainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Bstr)

    if ([string]::IsNullOrWhiteSpace($PlainKey)) {
        throw "EPA AQS API key cannot be empty."
    }

    $env:EPA_AQS_EMAIL = $Email.Trim()
    $env:EPA_AQS_KEY = $PlainKey

    $RunArgs = @(
        "-m",
        "heatsafe.research.official_experiment.cli",
        "run",
        "--config",
        "examples/real-experiments/epa-aqs-alameda-pm25-2025.json",
        "--workspace",
        "artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025",
        "--repository-root",
        "."
    )

    if ($Overwrite) {
        $RunArgs += "--overwrite"
    }

    Write-Host ""
    Write-Host "Running official acquisition, snapshot freeze, station selection, and benchmark..."
    & $Python @RunArgs

    if ($LASTEXITCODE -ne 0) {
        throw "The real official-data experiment returned exit code $LASTEXITCODE."
    }

    $VerifyArgs = @(
        "-m",
        "heatsafe.research.official_experiment.cli",
        "verify",
        "artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025"
    )

    Write-Host ""
    Write-Host "Verifying snapshot and experiment checksums..."
    & $Python @VerifyArgs

    if ($LASTEXITCODE -ne 0) {
        throw "Verification returned exit code $LASTEXITCODE."
    }

    $Report = Join-Path $Workspace "experiment\report\report.html"

    Write-Host ""
    Write-Host "=============================================================================="
    Write-Host "SUCCESS: First real official-data experiment completed."
    Write-Host "=============================================================================="
    Write-Host "Report:"
    Write-Host $Report
    Write-Host ""
    Write-Host "The local workspace is excluded from Git tracking."
    Write-Host "Review the report and station-selection record before any release or DOI."
    Write-Host ""

    if (Test-Path $Report) {
        Start-Process $Report
    }
    else {
        throw "The experiment completed, but the HTML report was not found."
    }
}
catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    $ExitCode = 1
}
finally {
    Remove-Item Env:EPA_AQS_EMAIL -ErrorAction SilentlyContinue
    Remove-Item Env:EPA_AQS_KEY -ErrorAction SilentlyContinue

    if ($Bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Bstr)
    }

    $PlainKey = $null
}

exit $ExitCode
