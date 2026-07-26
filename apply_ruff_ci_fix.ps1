param(
    [Parameter(Mandatory = $false)]
    [string]$RepoPath = ""
)

$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceRoot = Join-Path $PackageRoot "replacement-files"
$Branch = "fix/ruff-ci"
$Title = "fix: resolve Ruff CI violations"
$BodyFile = Join-Path $PackageRoot "PR_BODY.md"

if ([string]::IsNullOrWhiteSpace($RepoPath)) {
    $RepoPath = (Get-Location).Path
}
$RepoPath = (Resolve-Path $RepoPath).Path

if (-not (Test-Path (Join-Path $RepoPath ".git"))) {
    throw "The selected path is not a Git repository: $RepoPath"
}
if (-not (Test-Path (Join-Path $RepoPath "pyproject.toml"))) {
    throw "pyproject.toml was not found. Select the HeatSafe repository root."
}

Push-Location $RepoPath
try {
    $pending = git status --porcelain
    if ($LASTEXITCODE -ne 0) { throw "git status failed." }
    if ($pending) {
        throw "The repository has uncommitted changes. Commit or discard them before applying this fix."
    }

    git fetch origin
    if ($LASTEXITCODE -ne 0) { throw "git fetch origin failed." }

    git switch main
    if ($LASTEXITCODE -ne 0) { throw "Could not switch to main." }

    git pull --ff-only origin main
    if ($LASTEXITCODE -ne 0) { throw "Could not update main with a fast-forward pull." }

    $branchExists = git branch --list $Branch
    if ($branchExists) {
        git switch $Branch
    } else {
        git switch -c $Branch
    }
    if ($LASTEXITCODE -ne 0) { throw "Could not create or switch to $Branch." }

    $Files = @(
        "scripts/check_links.py",
        "scripts/check_secrets.py",
        "scripts/generate_demo_data.py",
        "scripts/package_release.py",
        "tests/test_core.py",
        "tests/test_data_and_connectors.py",
        "tests/test_research.py"
    )

    foreach ($relative in $Files) {
        $source = Join-Path $SourceRoot ($relative -replace "/", "\")
        $destination = Join-Path $RepoPath ($relative -replace "/", "\")
        if (-not (Test-Path $source)) { throw "Missing replacement file: $source" }
        Copy-Item -Force $source $destination
    }

    Write-Host "Running lightweight local verification..." -ForegroundColor Cyan
    if (Get-Command python -ErrorAction SilentlyContinue) {
        python -m compileall -q src tests scripts
        if ($LASTEXITCODE -ne 0) { throw "Python compilation failed." }
        python scripts/check_links.py
        if ($LASTEXITCODE -ne 0) { throw "Link check failed." }
        python scripts/check_secrets.py
        if ($LASTEXITCODE -ne 0) { throw "Secret check failed." }

        if (Get-Command pytest -ErrorAction SilentlyContinue) {
            $env:PYTHONPATH = "src"
            pytest -q
            if ($LASTEXITCODE -ne 0) { throw "pytest failed." }
        } else {
            Write-Host "pytest is not installed locally; GitHub Actions will run the full test suite." -ForegroundColor Yellow
        }
    } else {
        Write-Host "Python was not found; GitHub Actions will perform verification." -ForegroundColor Yellow
    }

    git add -- scripts/check_links.py scripts/check_secrets.py scripts/generate_demo_data.py scripts/package_release.py tests/test_core.py tests/test_data_and_connectors.py tests/test_research.py
    if ($LASTEXITCODE -ne 0) { throw "git add failed." }

    $staged = git diff --cached --name-only
    if (-not $staged) {
        Write-Host "No changes were found. The fix may already be applied." -ForegroundColor Yellow
    } else {
        git commit -m $Title
        if ($LASTEXITCODE -ne 0) { throw "git commit failed." }
    }

    git push -u origin $Branch
    if ($LASTEXITCODE -ne 0) { throw "git push failed." }

    if (Get-Command gh -ErrorAction SilentlyContinue) {
        gh pr create --base main --head $Branch --title $Title --body-file $BodyFile
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Pull request created successfully." -ForegroundColor Green
        } else {
            Write-Host "The branch was pushed, but GitHub CLI could not create the PR." -ForegroundColor Yellow
        }
    } else {
        $url = "https://github.com/FaramarzKowsari/heatsafe-climate-air-quality-lab/compare/main...$Branch?expand=1"
        Write-Host "GitHub CLI is not installed. Opening the ready-to-create Pull Request page:" -ForegroundColor Cyan
        Write-Host $url
        Start-Process $url
    }
}
finally {
    Pop-Location
}
