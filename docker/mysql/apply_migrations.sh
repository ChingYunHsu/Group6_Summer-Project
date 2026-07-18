#!/usr/bin/env bash
# docker/mysql/apply_migrations.sh
# ----------------------------------------------------------------------------
# Re-apply ClearPath DB init SQL to a RUNNING MySQL container.
#
# Why: MySQL's docker-entrypoint-initdb.d only runs on a FRESH data volume.
# If the volume already exists (e.g. a dev box that booted before 006/007
# were added), new init scripts are silently skipped — leaving
# report_categories / telemetry_audit_log / venue_source_links seed rows
# missing and causing silent mock fallback in the backend (O2, O14).
#
# All init scripts are idempotent (CREATE TABLE IF NOT EXISTS,
# INSERT IGNORE, ON DUPLICATE KEY UPDATE), so re-running them on an
# existing DB is safe. This script is the deployment SOP's migration
# re-apply step.
#
# Usage:
#   docker/mysql/apply_migrations.sh                  # default: apply 006+ on existing volume
#   docker/mysql/apply_migrations.sh --from 001        # apply all files (fresh-server equivalent)
#   docker/mysql/apply_migrations.sh --container foo   # custom container
#   docker/mysql/apply_migrations.sh --dry-run         # list files only
# ----------------------------------------------------------------------------
set -euo pipefail

CONTAINER="clearpath-mysql"
DB="${CLEARPATH_DB_NAME:-clearpath}"
USER="${CLEARPATH_DB_USER:-clearpath_app}"
PASS="${CLEARPATH_DB_PASSWORD:-clearpath_app}"
INIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/init" && pwd)"
DRY_RUN=false
FROM_PREFIX=""   # apply files whose basename starts with this or higher

while [[ $# -gt 0 ]]; do
    case "$1" in
        --container) CONTAINER="$2"; shift 2 ;;
        --db) DB="$2"; shift 2 ;;
        --user) USER="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        --from) FROM_PREFIX="$2"; shift 2 ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

echo "Container : $CONTAINER"
echo "Database  : $DB"
echo "Init dir  : $INIT_DIR"
[[ -n "$FROM_PREFIX" ]] && echo "From       : $FROM_PREFIX (apply files >= this prefix)"
echo

FILES=()
while IFS= read -r f; do
    FILES+=("$f")
done < <(find "$INIT_DIR" -maxdepth 1 -type f -name '*.sql' | sort)
if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "ERROR: no .sql files found in $INIT_DIR" >&2
    exit 1
fi

# Filter by --from prefix (default: 006 — 001-005 run on fresh volumes only).
# 001 has non-idempotent CREATE INDEX statements and should only be applied
# with --from 001 on a known-safe volume.
if [[ -z "$FROM_PREFIX" ]]; then
    FROM_PREFIX="006"
    echo "Defaulting to --from $FROM_PREFIX (skip 001-005, safe for existing volumes)."
    echo "Use --from 001 to apply ALL files (fresh-server equivalent)."
    echo
fi
FILTERED=()
for f in "${FILES[@]}"; do
    base="$(basename "$f")"
    if [[ "$base" > "$FROM_PREFIX" || "$base" == "$FROM_PREFIX" ]]; then
        FILTERED+=("$f")
    fi
done
if [[ ${#FILTERED[@]} -eq 0 ]]; then
    echo "No files with prefix >= $FROM_PREFIX — nothing to apply."
    exit 0
fi
echo "Will apply ${#FILTERED[@]} / ${#FILES[@]} files:"
for f in "${FILTERED[@]}"; do echo "  - $(basename "$f")"; done
echo

if $DRY_RUN; then
    exit 0
fi

# Verify the container is up.
if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo "ERROR: container '$CONTAINER' is not running. Start it with 'docker compose up -d mysql'." >&2
    exit 1
fi

applied=0
for f in "${FILTERED[@]}"; do
    name="$(basename "$f")"
    echo "applying $name ..."
    if docker exec -i "$CONTAINER" \
        sh -c "mysql -u\"$USER\" -p\"$PASS\" \"$DB\"" < "$f"; then
        applied=$((applied + 1))
        echo "  ok: $name"
    else
        echo "  FAIL: $name" >&2
        exit 2
      fi
done

echo
echo "Applied $applied / ${#FILTERED[@]} migration files."

# Smoke check (O14): report_categories must have >= 9 rows after re-apply.
echo
echo "Smoke check: SELECT COUNT(*) FROM report_categories;"
count=$(docker exec "$CONTAINER" \
    sh -c "mysql -u\"$USER\" -p\"$PASS\" \"$DB\" -N -B -e 'SELECT COUNT(*) FROM report_categories;'" 2>/dev/null || echo "0")
echo "  report_categories rows: $count"
if [[ "$count" -lt 9 ]]; then
    echo "  WARN: expected >= 9 report_categories rows (O14). Re-apply 006_seed_report_categories.sql." >&2
    exit 3
fi

# Smoke check (O2): telemetry_audit_log + venue_source_links must exist.
echo "Smoke check: required tables exist;"
missing=0
for t in telemetry_audit_log venue_source_links busyness_scores busyness_forecasts healthcare_prediction_groups healthcare_prediction_group_members; do
    exists=$(docker exec "$CONTAINER" \
        sh -c "mysql -u\"$USER\" -p\"$PASS\" \"$DB\" -N -B -e \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB' AND table_name='$t';\"" 2>/dev/null || echo "0")
    if [[ "$exists" -ne 1 ]]; then
        echo "  MISSING: $t"
        missing=$((missing + 1))
    else
        echo "  ok: $t"
    fi
done
[[ "$missing" -eq 0 ]] || { echo "FAIL: $missing required tables missing (O2)." >&2; exit 4; }

echo
echo "Smoke check: account-deletion foreign keys cascade;"
fk_failures=0
for pair in "user_reports fk_user_report_user" "report_confirmations fk_confirmation_user"; do
    read -r table constraint <<< "$pair"
    delete_rule=$(docker exec "$CONTAINER" \
        sh -c "mysql -u\"$USER\" -p\"$PASS\" \"$DB\" -N -B -e \"SELECT DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_SCHEMA='$DB' AND TABLE_NAME='$table' AND CONSTRAINT_NAME='$constraint';\"" 2>/dev/null || true)
    if [[ "$delete_rule" != "CASCADE" ]]; then
        echo "  FAIL: $table.$constraint DELETE_RULE='${delete_rule:-missing}' (expected CASCADE)"
        fk_failures=$((fk_failures + 1))
    else
        echo "  ok: $table.$constraint ON DELETE CASCADE"
    fi
done
[[ "$fk_failures" -eq 0 ]] || { echo "FAIL: $fk_failures account-deletion foreign keys are not CASCADE." >&2; exit 5; }

echo
echo "All migrations applied and smoke checks passed."
