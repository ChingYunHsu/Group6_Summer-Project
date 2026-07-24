#!/usr/bin/env bash
# Run the V2 forecast pipeline and publish to busyness_forecasts.
#
# Must be executed at least once per 12-hour window so forecast rows remain
# current.  Docker startup does not trigger this — it must be scheduled
# explicitly.
#
# SCHEDULING (pick one):
#
#   Cron — refresh every 11 hours so the window never expires between runs.
#   Log is written to a user-writable path; change LOG_FILE below to suit your
#   deployment (systemd unit, CI job, or dedicated log dir with rotation).
#
#     crontab -e
#     Add:  0 */11 * * *  /path/to/Group6_Summer-Project/Data+ML/test/7.13-7.18/run_v2_forecast.sh
#
#   Owner: the user under whose crontab or service unit this runs.
#   Failure alert: monitor exit code — a non-zero exit means the audit gate
#   failed and no data was published. Alert immediately if the scheduler
#   records a failure or no run is observed within 12 hours.
#
#   Manual release command (run from project root):
#     Data+ML/test/7.13-7.18/run_v2_forecast.sh
#
# ENVIRONMENT:
#   Set CLEARPATH_DB_HOST / CLEARPATH_DB_PORT / CLEARPATH_DB_USER /
#   CLEARPATH_DB_PASSWORD / CLEARPATH_DB_NAME if the defaults below are wrong.
#   Override LOG_FILE to redirect output — default is user-writable ~/logs/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

LABELS="$SCRIPT_DIR/output/serpapi_v2_labels_20260716/serpapi_popular_times_weak_labels.csv"
LEGACY_LABELS="$SCRIPT_DIR/output/serpapi_repeat_audit/legacy_cached_baseline.csv"
OUTPUT_DIR="$SCRIPT_DIR/output/v2_pattern_traffic_latest"
PYTHON="$PROJECT_ROOT/.venv-1/bin/python"
LOG_FILE="${LOG_FILE:-$HOME/logs/clearpath_v2_forecast.log}"

mkdir -p "$(dirname "$LOG_FILE")"

if [[ ! -f "$PYTHON" ]]; then
  echo "ERROR: Python not found at $PYTHON" >&2
  exit 1
fi

if [[ ! -f "$LABELS" ]]; then
  echo "ERROR: Labels file not found: $LABELS" >&2
  exit 1
fi

if [[ ! -f "$LEGACY_LABELS" ]]; then
  echo "ERROR: Legacy labels file not found: $LEGACY_LABELS" >&2
  exit 1
fi

{
  echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Starting V2 forecast pipeline"

  cd "$SCRIPT_DIR"
  "$PYTHON" forecast_v2_pattern.py \
    --labels "$LABELS" \
    --legacy-labels "$LEGACY_LABELS" \
    --output-dir "$OUTPUT_DIR" \
    --publish

  echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] V2 forecast pipeline complete"
} 2>&1 | tee -a "$LOG_FILE"
