$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Repo

Write-Host ""
Write-Host "=============================================================================="
Write-Host "HeatSafe First Real Official-Data Experiment"
Write-Host "US EPA AQS Alameda County PM2.5 — 2025"
Write-Host "=============================================================================="
Write-Host ""
Write-Host "Credentials are kept only in this PowerShell process."
Write-Host "They are not written to repository files, plans, snapshots or reports."
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
}

if (-not (Test-Path $Python)) {
    throw "Python virtual environment could not be created."
}

Write-Host "Installing or refreshing HeatSafe development dependencies..."
& $Python -m pip install --upgrade pip
& $Python -m pip install -e ".[dev]"

$email = Read-Host "EPA AQS account email"
$secureKey = Read-Host "EPA AQS API key" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

$Workspace = Join-Path $Repo "artifacts\local-real-experiments\epa-aqs-alameda-pm25-2025"
$OverwriteArgs = @()
if (Test-Path $Workspace) {
    Write-Host ""
    $answer = Read-Host "A previous local run exists. Replace it? Type YES to continue"
    if ($answer -ne "YES") {
        Write-Host "Cancelled. The previous workspace was not changed."
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        exit 0
    }
    $OverwriteArgs = @("--overwrite")
}

try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    $env:EPA_AQS_EMAIL = $email
    $env:EPA_AQS_KEY = $plainKey

    Write-Host ""
    Write-Host "Running official acquisition, snapshot freeze, station selection and benchmark..."
    & $Python -m heatsafe.research.official_experiment.cli run `
        --config "examples/real-experiments/epa-aqs-alameda-pm25-2025.json" `
        --workspace "artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025" `
        --repository-root "." `
        @OverwriteArgs

    if ($LASTEXITCODE -ne 0) {
        throw "The real official-data experiment returned exit code $LASTEXITCODE."
    }

    Write-Host ""
    Write-Host "Verifying snapshot and experiment checksums..."
    & $Python -m heatsafe.research.official_experiment.cli verify `
        "artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025"

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
}
finally {
    Remove-Item Env:EPA_AQS_EMAIL -ErrorAction SilentlyContinue
    Remove-Item Env:EPA_AQS_KEY -ErrorAction SilentlyContinue
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    $plainKey = $null
}
