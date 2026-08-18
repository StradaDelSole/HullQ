$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
Set-Location $repoRoot

Write-Host "HullQ workflow setup" -ForegroundColor Cyan
Write-Host "Repository: $repoRoot"
Write-Host ""

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail "Git is not installed or not available in PATH."
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Fail "GitHub CLI (gh) is not installed. Install GitHub CLI once, then run SETUP_WORKFLOW.bat again."
}

try {
    gh auth status 2>$null | Out-Null
} catch {
    Fail "GitHub CLI is not logged in. Run 'gh auth login' once, then run SETUP_WORKFLOW.bat again."
}

$remote = (git remote get-url origin).Trim()
if ($LASTEXITCODE -ne 0) {
    Fail "Could not read the origin remote."
}

if ($remote -notmatch "StradaDelSole/HullQ(\.git)?$") {
    Fail "This does not look like the canonical StradaDelSole/HullQ checkout. origin=$remote"
}

Write-Host "Applying protection to GitHub main..."

$payload = @{
    required_status_checks = @{
        strict = $true
        contexts = @(
            "quality (ubuntu-latest)",
            "quality (windows-latest)",
            "dependency audit"
        )
    }
    enforce_admins = $true
    required_pull_request_reviews = @{
        dismiss_stale_reviews = $false
        require_code_owner_reviews = $false
        required_approving_review_count = 0
        require_last_push_approval = $false
    }
    restrictions = $null
    required_linear_history = $true
    allow_force_pushes = $false
    allow_deletions = $false
    block_creations = $false
    required_conversation_resolution = $false
    lock_branch = $false
    allow_fork_syncing = $true
} | ConvertTo-Json -Depth 8

$temp = New-TemporaryFile
try {
    Set-Content -Path $temp -Value $payload -Encoding utf8
    gh api --method PUT "repos/StradaDelSole/HullQ/branches/main/protection" --input $temp.FullName | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Fail "GitHub rejected the branch-protection request. Your account/plan may not allow this setting. No local files were changed."
    }
} finally {
    Remove-Item $temp -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "SUCCESS" -ForegroundColor Green
Write-Host "main is now protected with:"
Write-Host "  - pull-request-only changes"
Write-Host "  - required Ubuntu CI"
Write-Host "  - required Windows CI"
Write-Host "  - required dependency audit"
Write-Host "  - branch must be up to date before merge"
Write-Host "  - force pushes blocked"
Write-Host "  - branch deletion blocked"
Write-Host ""
Write-Host "You only need to run SETUP_WORKFLOW.bat once."
