#!/usr/bin/env bash
# Close superseded open PRs and delete remote branches that must not be used as SoT.
# Run locally with: gh auth login (repo scope) && ./scripts/pr_hygiene_phase_b.sh
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-Perps12-oss/ai-command-center}"

comment_and_close() {
  local num="$1"
  local body="$2"
  if gh pr view "$num" --json state --jq .state 2>/dev/null | grep -q OPEN; then
    gh pr close "$num" --comment "$body" || gh pr close "$num"
    echo "Closed PR #$num"
  else
    echo "PR #$num already closed"
  fi
}

comment_and_close 75 "$(cat <<'EOF'
Superseded by Phase 11 integration on `main` (#76–#79). Do not use `phase-11a-command-center` as baseline for Phase B UI — see `docs/audits/REPOSITORY_TRUTH_CANON.md` and `docs/agents/DEVIN_UI_HANDOVER.md`.
EOF
)"

comment_and_close 66 "$(cat <<'EOF'
Timeline undo landed on `main` via #74 (`e4bab0c`). This branch is far behind `main` and is not mergeable without a full rebase. Closing for hygiene; follow `docs/architecture/UI_REFURBISHMENT_BACKLOG.md` on `main` for any remaining backlog.
EOF
)"

comment_and_close 81 "$(cat <<'EOF'
Phase 12 (State Intelligence) is outside the active Phase B UI queue (E00–E13). Parked for hygiene — reopen from `origin/main` when Phase 12 is scheduled and constitutional pre-flight is complete. Reference tip: `cursor/phase-12-state-intelligence-0fbc` @ `f285789`.
EOF
)"

delete_branch() {
  local branch="$1"
  if git ls-remote --exit-code origin "refs/heads/${branch}" >/dev/null 2>&1; then
    git push origin --delete "${branch}"
    echo "Deleted origin/${branch}"
  else
    echo "origin/${branch} already absent"
  fi
}

# Must not remain as mistaken SoT
delete_branch phase-11a-command-center

# Merged or superseded integration branches (safe after #80 / execution authority on main)
delete_branch cursor/state-authority-migration-6a56
delete_branch cursor/runtime-first-execution-authority-6a56

# Keep cursor/phase-12-state-intelligence-0fbc until Phase 12 is restarted from main.
# Review feature/planner-evolution-phase-c0-constitution with owner before deleting.

echo ""
echo "Open PRs against main:"
gh pr list --repo "$REPO" --state open --base main
