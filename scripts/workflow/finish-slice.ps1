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

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not $Slice) { $Slice = Read-Host 'Finished slice number (example: 0005)' }
$sliceNumber = Normalize-Slice $Slice

Write-Host ""
Write-Host "Finishing SLICE-$sliceNumber..."

Run-Git -GitArgs @('-C', $repoRoot, 'fetch', '--prune', 'origin')
Run-Git -GitArgs @('-C', $repoRoot, 'switch', 'main')
Run-Git -GitArgs @('-C', $repoRoot, 'pull', '--ff-only', 'origin', 'main')

$sliceFile = Get-PrimarySliceFile -Root $repoRoot -Number $sliceNumber

$slug = $sliceFile.BaseName -replace "^SLICE-$sliceNumber-", ''
$branch = "slice/$sliceNumber-$slug"
$repoName = Split-Path $repoRoot -Leaf
$parent = Split-Path $repoRoot -Parent
$worktree = Join-Path $parent "$repoName-slice-$sliceNumber"

if (-not (Test-Path $worktree)) {
    Write-Host "Local main is current. No slice worktree exists, so there is nothing else to clean up."
    exit 0
}

$statusLines = @(& git -C $worktree status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0) { throw "Could not inspect slice worktree." }

if ($statusLines.Count -gt 0) {
    $hasUntracked = @($statusLines | Where-Object { $_ -like '??*' }).Count -gt 0

    & git -C $worktree diff --ignore-space-at-eol --quiet --
    $hasSubstantiveUnstaged = ($LASTEXITCODE -ne 0)

    & git -C $worktree diff --cached --ignore-space-at-eol --quiet --
    $hasSubstantiveStaged = ($LASTEXITCODE -ne 0)

    if (-not $hasUntracked -and -not $hasSubstantiveUnstaged -and -not $hasSubstantiveStaged) {
        Write-Host "Only line-ending / end-of-line whitespace normalization changes were detected."
        Write-Host "Restoring those non-semantic working-copy changes to the committed state."
        Run-Git -GitArgs @('-C', $worktree, 'restore', '--staged', '--worktree', '--', '.')
        $statusLines = @(& git -C $worktree status --porcelain=v1 --untracked-files=all)
        if ($LASTEXITCODE -ne 0) { throw "Could not re-inspect slice worktree after normalization cleanup." }
    }
}

if ($statusLines.Count -gt 0) {
    Write-Host "Local main is current, but the slice worktree has substantive uncommitted/untracked changes."
    Write-Host "It was NOT removed. Review these paths first:"
    foreach ($line in $statusLines) { Write-Host "  $line" }
    exit 0
}

$gh = Get-Command gh -ErrorAction SilentlyContinue
if (-not $gh) {
    Write-Host "Local main is current."
    Write-Host "GitHub CLI (gh) is not installed, so safe automatic cleanup was skipped."
    Write-Host "Nothing was deleted. START_SLICE can still be used normally."
    exit 0
}

$mergedJson = & gh pr list --repo StradaDelSole/HullQ --head $branch --state merged --limit 1 --json number,mergedAt,url 2>$null
if ($LASTEXITCODE -ne 0 -or -not $mergedJson -or $mergedJson.Trim() -eq '[]') {
    Write-Host "Local main is current, but no merged PR for '$branch' was confirmed."
    Write-Host "Worktree was NOT removed."
    exit 0
}

Run-Git -GitArgs @('-C', $repoRoot, 'worktree', 'remove', $worktree)
& git -C $repoRoot show-ref --verify --quiet "refs/heads/$branch"
if ($LASTEXITCODE -eq 0) {
    Run-Git -GitArgs @('-C', $repoRoot, 'branch', '-D', $branch)
}
Run-Git -GitArgs @('-C', $repoRoot, 'worktree', 'prune')

& git -C $repoRoot ls-remote --exit-code --heads origin "refs/heads/$branch" *> $null
if ($LASTEXITCODE -eq 0) {
    & gh api --method DELETE "repos/StradaDelSole/HullQ/git/refs/heads/$branch" *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "The merged remote slice branch was removed."
    } else {
        Write-Host "Remote slice branch cleanup could not be completed automatically; local cleanup is still complete."
    }
}

Run-Git -GitArgs @('-C', $repoRoot, 'fetch', '--prune', 'origin')

Write-Host ""
Write-Host "DONE"
Write-Host "Local main is synchronized with GitHub."
Write-Host "The SLICE-$sliceNumber worktree and local branch were safely removed."
