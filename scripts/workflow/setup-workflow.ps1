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

gh auth status 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Fail "GitHub CLI is not logged in. Run 'gh auth login' once, then run SETUP_WORKFLOW.bat again."
}

$remote = (git remote get-url origin).Trim()
if ($LASTEXITCODE -ne 0) {
    Fail "Could not read the origin remote."
}

if ($remote -notmatch "StradaDelSole/HullQ(\.git)?$") {
    Fail "This does not look like the canonical StradaDelSole/HullQ checkout. origin=$remote"
}

$rulesetName = "HullQ main protection"

$payloadObject = @{
    name = $rulesetName
    target = "branch"
    enforcement = "active"
    bypass_actors = @()
    conditions = @{
        ref_name = @{
            include = @("refs/heads/main")
            exclude = @()
        }
    }
    rules = @(
        @{
            type = "deletion"
        },
        @{
            type = "non_fast_forward"
        },
        @{
            type = "required_linear_history"
        },
        @{
            type = "pull_request"
            parameters = @{
                allowed_merge_methods = @("squash", "rebase")
                dismiss_stale_reviews_on_push = $false
                require_code_owner_review = $false
                require_last_push_approval = $false
                required_approving_review_count = 0
                required_review_thread_resolution = $false
            }
        },
        @{
            type = "required_status_checks"
            parameters = @{
                do_not_enforce_on_create = $false
                strict_required_status_checks_policy = $true
                required_status_checks = @(
                    @{ context = "quality (ubuntu-latest)" },
                    @{ context = "quality (windows-latest)" },
                    @{ context = "dependency audit" }
                )
            }
        }
    )
}

$payload = $payloadObject | ConvertTo-Json -Depth 10 -Compress

Write-Host "Checking existing GitHub rulesets..."
$existingJson = gh api "repos/StradaDelSole/HullQ/rulesets" 2>$null
if ($LASTEXITCODE -ne 0) {
    Fail "Could not read repository rulesets. GitHub CLI needs repository Administration access."
}

$existing = @($existingJson | ConvertFrom-Json)
$match = $existing | Where-Object { $_.name -eq $rulesetName } | Select-Object -First 1

if ($null -eq $match) {
    Write-Host "Creating main protection ruleset..."
    $payload | gh api --method POST "repos/StradaDelSole/HullQ/rulesets" --input - | Out-Null
} else {
    Write-Host "Updating existing main protection ruleset..."
    $payload | gh api --method PUT "repos/StradaDelSole/HullQ/rulesets/$($match.id)" --input - | Out-Null
}

if ($LASTEXITCODE -ne 0) {
    Fail "GitHub rejected the ruleset request. Your account/plan or gh authorization may not allow repository rulesets. No local files were changed."
}

Write-Host ""
Write-Host "SUCCESS" -ForegroundColor Green
Write-Host "GitHub main is now protected with:"
Write-Host "  - changes must go through a pull request"
Write-Host "  - zero formal GitHub approvals required"
Write-Host "  - required Ubuntu CI"
Write-Host "  - required Windows CI"
Write-Host "  - required dependency audit"
Write-Host "  - branch must be up to date before merge"
Write-Host "  - force pushes blocked"
Write-Host "  - main deletion blocked"
Write-Host "  - linear history required (squash/rebase merge)"
Write-Host ""
Write-Host "You only need to run SETUP_WORKFLOW.bat once. Running it again is safe and updates the same ruleset."
