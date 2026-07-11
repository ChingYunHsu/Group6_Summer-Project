#!/usr/bin/env bash
# telemetry_smoke.sh — O2 acceptance: prove run_live_telemetry.py --execute
# writes live-telemetry rows to the compose MySQL and that the realtime read
# path (backend/src/api/realtime.py) returns them.
#
# Source-agnostic: uses locally-generated mock payloads (source_name=live_capacity,
# v_1001/v_1002) that resolve via the venue_source_links seed to the seeded venue
# 'seed-restroom-bryant-park-001'. No external feed required.
#
# Usage:
#   bash Data+ML/test/6.15-6.20/scripts/telemetry_smoke.sh
#
# Env overrides: CONTAINER (default clearpath-mysql), PYTHON (default repo .venv).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"          # Data+ML/test/6.15-6.20
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"  # repo root

CONTAINER="${CONTAINER:-clearpath-mysql}"
DB_NAME="clearpath"
DB_USER="clearpath_app"
DB_PASS="clearpath_app"
# venue_source_links seed maps live_capacity v_1001 -> bryant-park, v_1002 -> bellevue.
SEED_VENUES="'seed-restroom-bryant-park-001','seed-healthcare-bellevue-001'"
MODEL_VERSION="live-telemetry-v1"

if [[ -n "${PYTHON:-}" ]]; then
  PY="$PYTHON"
elif [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PY="$REPO_ROOT/.venv/bin/python"
else
  PY="python3"
fi

fail() { echo "FAIL: $*" >&2; exit 1; }
sql()  { docker exec -i "$CONTAINER" mysql -N -s -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "$1" 2>/dev/null; }

echo "== [1/6] Ensure compose MySQL is up =="
if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "-- starting mysql via docker compose"
  ( cd "$REPO_ROOT" && docker compose up -d mysql )
fi
echo "-- waiting for mysql to accept connections"
for i in $(seq 1 60); do
  if docker exec "$CONTAINER" mysqladmin ping -u"$DB_USER" -p"$DB_PASS" --silent >/dev/null 2>&1; then
    echo "-- mysql ready"; break
  fi
  [[ "$i" == "60" ]] && fail "mysql did not become ready in 60s"
  sleep 1
done

echo "== [2/6] Assert dependency tables exist (O2) =="
TABLE_COUNT="$(sql "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME' AND table_name IN ('telemetry_audit_log','venue_source_links');")"
[[ "$TABLE_COUNT" == "2" ]] || fail "expected 2 dependency tables, found '$TABLE_COUNT' (telemetry_audit_log / venue_source_links)"
echo "-- telemetry_audit_log + venue_source_links present"

echo "== [3/6] Write clean 2-row payload JSONL =="
# Two valid payloads for the two distinct seeded venues (v_1001->bryant-park,
# v_1002->bellevue). No invalid line, so rc==0 is meaningful.
NOW_MIN="$(date -u +%Y-%m-%dT%H:%M:00)"
PAYLOADS="$(mktemp -t telemetry_smoke_XXXX.jsonl)"
trap 'rm -f "$PAYLOADS"' EXIT
cat > "$PAYLOADS" <<EOF
{"source_name":"live_capacity","source_venue_id":"v_1001","observed_at":"$NOW_MIN","load_percent":72,"avg_wait_minutes":14,"ttl_seconds":300}
{"source_name":"live_capacity","source_venue_id":"v_1002","observed_at":"$NOW_MIN","load_percent":30,"avg_wait_minutes":3,"ttl_seconds":300}
EOF
echo "-- wrote 2 payloads (v_1001, v_1002 @ $NOW_MIN)"

echo "== [4/6] Run run_live_telemetry.py --execute =="
BEFORE_AUDIT="$(sql "SELECT COUNT(*) FROM telemetry_audit_log;")"
set +e
CLEARPATH_DB_HOST=127.0.0.1 CLEARPATH_DB_PORT=3306 \
CLEARPATH_DB_USER="$DB_USER" CLEARPATH_DB_PASSWORD="$DB_PASS" CLEARPATH_DB_NAME="$DB_NAME" \
  "$PY" "$RUNNER_DIR/src/run_live_telemetry.py" --payloads "$PAYLOADS" --execute
RC=$?
set -e
[[ "$RC" == "0" ]] || fail "runner exited $RC (expected 0: 0 rejected, 0 unmatched)"
echo "-- runner exited 0"

echo "== [5/6] Verify busyness_scores + telemetry_audit_log =="
FRESH_ROWS="$(sql "SELECT COUNT(*) FROM busyness_scores WHERE model_version='$MODEL_VERSION' AND venue_id IN ($SEED_VENUES) AND created_at >= (NOW() - INTERVAL 5 MINUTE);")"
[[ "${FRESH_ROWS:-0}" -ge 2 ]] || fail "expected >=2 fresh busyness_scores rows for the seeded venues, found '${FRESH_ROWS:-0}'"
echo "-- busyness_scores: $FRESH_ROWS fresh live-telemetry rows across the 2 seeded venues"

read -r A_SUCCESS A_INGESTED A_UNMATCHED <<<"$(sql "SELECT success, ingested, unmatched FROM telemetry_audit_log ORDER BY audit_id DESC LIMIT 1;")"
AFTER_AUDIT="$(sql "SELECT COUNT(*) FROM telemetry_audit_log;")"
[[ "$AFTER_AUDIT" -gt "$BEFORE_AUDIT" ]] || fail "no new telemetry_audit_log row appended"
[[ "$A_SUCCESS" == "1" ]]     || fail "latest audit row success=$A_SUCCESS (expected 1)"
[[ "$A_INGESTED" == "2" ]]    || fail "latest audit row ingested=$A_INGESTED (expected 2)"
[[ "$A_UNMATCHED" == "0" ]]   || fail "latest audit row unmatched=$A_UNMATCHED (expected 0)"
echo "-- telemetry_audit_log: success=1 ingested=2 unmatched=0 (rows $BEFORE_AUDIT -> $AFTER_AUDIT)"

echo "== [6/6] Verify realtime read path (realtime.py shape) =="
# Mirrors: SELECT ... FROM busyness_scores WHERE model_version=%s AND created_at >= since
REALTIME_ROWS="$(sql "SELECT COUNT(*) FROM busyness_scores WHERE model_version='$MODEL_VERSION' AND created_at >= (NOW() - INTERVAL 5 MINUTE);")"
[[ "${REALTIME_ROWS:-0}" -ge 2 ]] || fail "realtime read query returned '${REALTIME_ROWS:-0}' rows (expected >=2)"
echo "-- realtime read path returns $REALTIME_ROWS live-telemetry rows"

echo
echo "PASS: O2 live --execute path verified (busyness_scores + audit + realtime read)."
