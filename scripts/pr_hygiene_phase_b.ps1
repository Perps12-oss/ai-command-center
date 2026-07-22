# Close superseded open PRs and delete remote branches that must not be used as SoT.
# Requires: GitHub CLI (gh auth login) with permission to close PRs and delete branches.
# Usage (PowerShell):  Set-Location <repo-root>; .\scripts\pr_hygiene_phase_b.ps1

$ErrorActionPreference = "Stop"
$Repo = if ($env:GITHUB_REPOSITORY) { $env:GITHUB_REPOSITORY } else { "Perps12-oss/ai-command-center" }

function Close-PrWithComment {
    param(
        [int]$Number,
        [string]$Body
    )
    $state = gh pr view $Number --json state --jq .state 2>$null
    if ($state -eq "OPEN") {
        gh pr close $Number --comment $Body
        if ($LASTEXITCODE -ne 0) {
            gh pr close $Number
        }
        Write-Host "Closed PR #$Number"
    }
    else {
        Write-Host "PR #$Number already closed (state: $state)"
    }
}

Close-PrWithComment -Number 75 -Body @"
Superseded by Phase 11 integration on ``main`` (#76–#79). Do not use ``phase-11a-command-center`` as baseline for Phase B UI — see ``docs/audits/REPOSITORY_TRUTH_CANON.md`` and ``docs/agents/DEVIN_UI_HANDOVER.md``.
"@

Close-PrWithComment -Number 66 -Body @"
Timeline undo landed on ``main`` via #74 (``e4bab0c``). This branch is far behind ``main`` and is not mergeable without a full rebase. Closing for hygiene; follow ``docs/architecture/UI_REFURBISHMENT_BACKLOG.md`` on ``main`` for any remaining backlog.
"@

Close-PrWithComment -Number 81 -Body @"
Phase 12 (State Intelligence) is outside the active Phase B UI queue (E00–E13). Parked for hygiene — reopen from ``origin/main`` when Phase 12 is scheduled and constitutional pre-flight is complete. Reference tip: ``cursor/phase-12-state-intelligence-0fbc`` @ ``f285789``.
"@

function Remove-RemoteBranch {
    param([string]$Branch)
    $null = git ls-remote --exit-code origin "refs/heads/$Branch" 2>$null
    if ($LASTEXITCODE -eq 0) {
        git push origin --delete $Branch
        Write-Host "Deleted origin/$Branch"
    }
    else {
        Write-Host "origin/$Branch already absent"
    }
}

Remove-RemoteBranch "phase-11a-command-center"
Remove-RemoteBranch "cursor/state-authority-migration-6a56"
Remove-RemoteBranch "cursor/runtime-first-execution-authority-6a56"

Write-Host ""
Write-Host "Open PRs against main:"
gh pr list --repo $Repo --state open --base main
