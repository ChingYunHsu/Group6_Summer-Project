#!/usr/bin/env bash
# Apply or verify the repeatable report_categories seed on an existing MySQL volume.
# Usage: docker/mysql/scripts/ensure_report_categories.sh [--apply|--verify]
set -euo pipefail

MODE="${1:---verify}"
case "$MODE" in
  --apply|--verify) ;;
  *) echo "usage: $0 [--apply|--verify]" >&2; exit 64 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SEED_SQL="$REPO_ROOT/docker/mysql/init/006_seed_report_categories.sql"
CONTAINER="${CONTAINER:-clearpath-mysql}"
DB_NAME="${CLEARPATH_DB_NAME:-clearpath}"
DB_USER="${CLEARPATH_DB_USER:-clearpath_app}"
DB_PASSWORD="${CLEARPATH_DB_PASSWORD:-clearpath_app}"
EXPECTED_IDS="closed_early,elevator_broken,entrance_closed,large_crowd,long_waiting_time,protest_or_blockage,ramp_blocked,toilet_out_of_order,wheelchair_lift_broken"

fail() { echo "FAIL: $*" >&2; exit 1; }
mysql_query() {
  docker exec -i "$CONTAINER" mysql -N -s -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "$1" 2>/dev/null
}

[[ -f "$SEED_SQL" ]] || fail "seed file not found: $SEED_SQL"
[[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)" == "true" ]] \
  || fail "MySQL container '$CONTAINER' is not running"

if [[ "$MODE" == "--apply" ]]; then
  echo "Applying repeatable report_categories seed to $CONTAINER/$DB_NAME"
  docker exec -i "$CONTAINER" mysql -u"$DB_USER" -p"$DB_PASSWORD" < "$SEED_SQL" \
    || fail "seed application failed"
fi

count="$(mysql_query "SELECT COUNT(*) FROM report_categories WHERE is_active = TRUE;")"
[[ "$count" == "9" ]] || fail "expected 9 active report categories, found '$count'"

ids="$(mysql_query "SELECT GROUP_CONCAT(category_id ORDER BY category_id SEPARATOR ',') FROM report_categories WHERE is_active = TRUE;")"
[[ "$ids" == "$EXPECTED_IDS" ]] || fail "report category ids differ from frozen contract: '$ids'"

echo "PASS: report_categories has the frozen 9 active categories"
