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

$dirty = & git -C $worktree status --porcelain
if ($LASTEXITCODE -ne 0) { throw "Could not inspect slice worktree." }
if ($dirty) {
    Write-Host "Local main is current, but the slice worktree has uncommitted changes. It was NOT removed."
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
Run-Git -GitArgs @('-C', $repoRoot, 'fetch', '--prune', 'origin')

Write-Host ""
Write-Host "DONE"
Write-Host "Local main is synchronized with GitHub."
Write-Host "The SLICE-$sliceNumber worktree and local branch were safely removed."
