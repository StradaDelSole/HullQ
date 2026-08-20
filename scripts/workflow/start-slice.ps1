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
    $candidates = @(Get-ChildItem (Join-Path $Root 'docs\slices') -Filter "SLICE-$Number-*.md")
    $primary = @(
        $candidates | Where-Object {
            (Get-Content -Raw $_.FullName) -match '(?m)^\*\*Type:\*\*\s*[A-Z_]+\s*$'
        }
    )
    if ($primary.Count -ne 1) {
        $names = if ($candidates.Count -gt 0) { ($candidates.Name -join ', ') } else { '<none>' }
        throw "Expected exactly one primary SLICE-$Number document with a **Type:** header; found $($primary.Count). Matching files: $names"
    }
    return $primary[0]
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
Implement SLICE-$sliceNumber.

Read the repository from this synchronized local worktree.
Follow CLAUDE.md and $relativeSliceFile exactly.

Work only on branch:
$branch

Do not modify main.
Do not start another slice.
At completion, push this same branch to GitHub and leave the slice in REVIEW or BLOCKED.
Do not merge to main.
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
Write-Host "START_SLICE did NOT open, close, reload, or switch any VS Code window."
Write-Host "When you are ready, open the worktree in the VS Code window you want Claude to use, then paste the copied prompt."
