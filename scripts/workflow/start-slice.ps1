param([string]$Slice)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Run-Git {
    param([string[]]$GitArgs)
    & git @GitArgs
    if ($LASTEXITCODE -ne 0) { throw "git failed: git $($GitArgs -join ' ')" }
}

function Normalize-Slice([string]$Value) {
    if ($Value -match '^(\d{1,4})$') { return $Matches[1].PadLeft(4, '0') }
    throw "Enter a slice number such as 5 or 0005."
}

function Get-PrimarySliceFile([string]$Root, [string]$Number) {
    $allCandidates = @(Get-ChildItem (Join-Path $Root 'docs\slices') -Filter "SLICE-$Number-*.md")
    $candidates = @(
        $allCandidates | Where-Object { $_.Name -notlike '*-acceptance-closure.md' }
    )
    $primary = @(
        $candidates | Where-Object {
            (Get-Content -Raw $_.FullName) -match '(?m)^\*\*Type:\*\*\s*[A-Z_]+\s*$'
        }
    )
    if ($primary.Count -ne 1) {
        $names = if ($candidates.Count -gt 0) { ($candidates.Name -join ', ') } else { '<none>' }
        throw "Expected exactly one primary SLICE-$Number document with a **Type:** header after excluding acceptance-closure documents; found $($primary.Count). Eligible files: $names"
    }
    return $primary[0]
}

function Assert-ProductExecutionChecks([string]$Number, [string]$Text, [string]$FileName) {
    if ([int]$Number -lt 39) { return }

    $requiredChecks = @(
        'ONE-CAPABILITY CHECK',
        'VISIBLE-RESULT CHECK',
        'PRODUCT EXECUTION PLAN ALIGNMENT'
    )

    foreach ($check in $requiredChecks) {
        $pattern = "(?m)^\*\*$([regex]::Escape($check)):\*\*\s*PASS\s*$"
        if ($Text -notmatch $pattern) {
            throw "SLICE-$Number cannot start: $FileName must contain '**$check:** PASS' for post-0038 work. Prepare/review the slice against docs/PRODUCT_EXECUTION_PLAN.md before starting Claude."
        }
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not $Slice) { $Slice = Read-Host 'Slice number (example: 0005)' }
$sliceNumber = Normalize-Slice $Slice

Write-Host ""
Write-Host "Preparing SLICE-$sliceNumber..."

$dirty = & git -C $repoRoot status --porcelain
if ($LASTEXITCODE -ne 0) { throw "This folder is not a valid Git checkout." }
if ($dirty) { throw "Main checkout has local changes. Commit/stash them before starting a slice." }

Run-Git -GitArgs @('-C', $repoRoot, 'fetch', '--prune', 'origin')
Run-Git -GitArgs @('-C', $repoRoot, 'switch', 'main')
Run-Git -GitArgs @('-C', $repoRoot, 'pull', '--ff-only', 'origin', 'main')
Run-Git -GitArgs @('-C', $repoRoot, 'worktree', 'prune')

$sliceFile = Get-PrimarySliceFile -Root $repoRoot -Number $sliceNumber
$sliceText = Get-Content -Raw $sliceFile.FullName
$statusMatch = [regex]::Match($sliceText, '(?m)^\*\*Status:\*\*\s*([A-Z_]+)\s*$')
if (-not $statusMatch.Success) {
    throw "Could not read the status from $($sliceFile.Name)."
}
$sliceStatus = $statusMatch.Groups[1].Value
if ($sliceStatus -ne 'READY') {
    throw "SLICE-$sliceNumber is '$sliceStatus', not READY. Do not start Claude yet; ask the project master to prepare/authorize this slice first."
}

Assert-ProductExecutionChecks -Number $sliceNumber -Text $sliceText -FileName $sliceFile.Name

$slug = $sliceFile.BaseName -replace "^SLICE-$sliceNumber-", ''
$branch = "slice/$sliceNumber-$slug"
$repoName = Split-Path $repoRoot -Leaf
$parent = Split-Path $repoRoot -Parent
$worktree = Join-Path $parent "$repoName-slice-$sliceNumber"

if (Test-Path $worktree) {
    $current = (& git -C $worktree branch --show-current).Trim()
    if ($current -ne $branch) {
        throw "Worktree already exists at $worktree on branch '$current', expected '$branch'."
    }
    Write-Host "Existing worktree found. Reusing it."
} else {
    & git -C $repoRoot show-ref --verify --quiet "refs/heads/$branch"
    $localExists = ($LASTEXITCODE -eq 0)

    & git -C $repoRoot ls-remote --exit-code --heads origin "refs/heads/$branch" *> $null
    $remoteExists = ($LASTEXITCODE -eq 0)

    if ($localExists) {
        Run-Git -GitArgs @('-C', $repoRoot, 'worktree', 'add', $worktree, $branch)
    } elseif ($remoteExists) {
        Run-Git -GitArgs @('-C', $repoRoot, 'branch', '--track', $branch, "origin/$branch")
        Run-Git -GitArgs @('-C', $repoRoot, 'worktree', 'add', $worktree, $branch)
    } else {
        Run-Git -GitArgs @('-C', $repoRoot, 'worktree', 'add', '-b', $branch, $worktree, 'origin/main')
    }
}

$relativeSliceFile = "docs/slices/$($sliceFile.Name)"
$prompt = @"
Implement SLICE-$sliceNumber on branch `$branch`.

TOKEN/CONTEXT DISCIPLINE:
- This slice should run in a fresh Claude conversation.
- Read CLAUDE.md, then read $relativeSliceFile FIRST.
- Read only controlling artifacts explicitly named by the slice and implementation files needed for the concrete task.
- Do NOT preload README, PROJECT_CONTEXT, PROJECT_STATE, full REQUIREMENTS, OPEN_QUESTIONS, slice INDEX, ROADMAP, or unrelated history merely for orientation.
- Prefer targeted search/narrow reads over whole large files.
- Use the synchronized local checkout; do not repeatedly fetch ordinary local files through GitHub/API tooling.
- Do not restate the contract or narrate routine exploration.
- If this same-slice session becomes very large, ask the operator to run /compact before continuing; preserve the slice contract, decisions, changed files, validation state and unresolved blockers, not exploratory history/logs.

EXECUTION:
- Follow CLAUDE.md and $relativeSliceFile exactly.
- For SLICE-0039 and later, comply with docs/PRODUCT_EXECUTION_PLAN.md and preserve the slice's PASS product-execution checks.
- Work only on `$branch`; do not modify main or another branch.
- Do not broaden scope or start another slice.
- Push this same branch to GitHub at completion.
- Leave the slice in REVIEW or BLOCKED; never mark DONE and never merge to main.

FINAL OPERATOR HANDOFF:
- Your FINAL response MUST use the completion-report structure in docs/slices/SLICE_TEMPLATE.md.
- Keep it concise but complete: summarize results; do not paste full logs, diffs, repeated acceptance text, or project-history recaps unless needed to explain a failure/blocker.
- Include changed files, requirements/research addressed, tests/fixtures, local validation commands + summarized results, exact final branch HEAD SHA, remote/external verification state, unresolved findings/ambiguities/scope deviations, next action, and agent declaration.
- Observe required remote CI on that exact final HEAD when the slice requires remote CI.
- After observing final exact-head CI, do NOT commit merely to record the CI result unless the slice explicitly requires it.
- After the final handoff, stop.
"@

try {
    Set-Clipboard -Value $prompt
    Write-Host "Claude prompt copied to clipboard."
} catch {
    Write-Host "Could not copy prompt to clipboard; it is printed below."
    Write-Host $prompt
}

Write-Host ""
Write-Host "READY"
Write-Host "Worktree: $worktree"
Write-Host "Branch:   $branch"
Write-Host ""
Write-Host "TOKEN-EFFICIENT CLAUDE START:"
Write-Host "1. Open this slice worktree in the intended VS Code window."
Write-Host "2. Start a fresh Claude conversation. If reusing the current Claude Code session, run /clear first."
Write-Host "3. Paste the copied prompt only; do not paste the previous slice report/history."
Write-Host "4. During a long same-slice session, use /context and /compact when directed by the project master."
Write-Host ""
Write-Host "START_SLICE did NOT open, close, reload, or switch any VS Code window."
