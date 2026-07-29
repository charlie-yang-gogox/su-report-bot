#!/usr/bin/env bash
#
# Single entry point for every report run — local, cloud routine, or CI.
#
# Usage:
#   scripts/run_reports.sh daily    # main.py (Jira) + main_linear.py (Linear)
#   scripts/run_reports.sh weekly   # gen_weekly_report.py + gen_weekly_report_linear.py
#
# Contract:
#   - Both trackers always run. One tracker failing never stops the other, so a Jira
#     outage cannot silently swallow the Linear team's report.
#   - Exit code is non-zero if ANY tracker failed, so the scheduler surfaces it.
#   - Secrets come from the process environment. When a .env exists in the repo root
#     (local development), python-dotenv loads it instead and the precheck is skipped.
#   - cwd is forced to the repo root: lib/logger.py writes to the relative path logs/.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

MODE="${1:-}"
case "$MODE" in
  daily)
    STEPS=("Jira daily:main.py" "Linear daily:main_linear.py")
    ;;
  weekly)
    STEPS=("Jira weekly:gen_weekly_report.py" "Linear weekly:gen_weekly_report_linear.py")
    ;;
  *)
    echo "usage: $(basename "$0") <daily|weekly>" >&2
    exit 2
    ;;
esac

# --- Environment precheck -----------------------------------------------------
# Both modes need the same credentials: the daily and weekly scripts read the same
# variables, they differ only in which report they build.
#
# LINEAR_ORG_SLUG is required rather than optional: main_linear.py falls back to a
# bare https://linear.app base URL, which produces a report where every ticket link
# is broken. A broken report is worse than a loud failure.
if [[ -f .env ]]; then
  echo "==> .env present — skipping env precheck (python-dotenv will load it)"
else
  REQUIRED=(
    SLACK_TOKEN
    JIRA_USER_NAME JIRA_API_TOKEN JIRA_USERS
    NOTION_TOKEN NOTION_DATABASE_ID
    LINEAR_API_TOKEN LINEAR_ORG_SLUG LINEAR_USERS LINEAR_NOTION_DATABASE_ID
  )
  MISSING=()
  for var in "${REQUIRED[@]}"; do
    [[ -n "${!var:-}" ]] || MISSING+=("$var")
  done
  if (( ${#MISSING[@]} > 0 )); then
    echo "ERROR: missing required environment variables:" >&2
    printf '  - %s\n' "${MISSING[@]}" >&2
    echo "Set them in the runtime environment, or place a .env in the repo root." >&2
    exit 1
  fi
  echo "==> Env precheck passed (${#REQUIRED[@]} variables present)"
fi

# --- Dependencies -------------------------------------------------------------
echo "==> Installing dependencies"
if ! python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt; then
  # Debian-based sandboxes mark the system Python as externally managed (PEP 668).
  echo "==> pip install failed; retrying with --break-system-packages"
  python3 -m pip install --quiet --disable-pip-version-check --break-system-packages \
    -r requirements.txt || {
    echo "ERROR: dependency install failed" >&2
    exit 1
  }
fi

# --- Run ----------------------------------------------------------------------
FAILED=()
for step in "${STEPS[@]}"; do
  label="${step%%:*}"
  script="${step#*:}"
  echo "==> [$(date '+%Y-%m-%d %H:%M:%S')] $label ($script)"
  if python3 "$script"; then
    echo "==> $label OK"
  else
    rc=$?
    echo "==> $label FAILED (exit $rc)" >&2
    FAILED+=("$label")
  fi
done

echo "==> Summary ($MODE): $(( ${#STEPS[@]} - ${#FAILED[@]} ))/${#STEPS[@]} succeeded"
if (( ${#FAILED[@]} > 0 )); then
  printf '    failed: %s\n' "${FAILED[@]}" >&2
  exit 1
fi
