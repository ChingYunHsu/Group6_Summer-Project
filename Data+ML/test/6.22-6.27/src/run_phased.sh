#!/bin/bash
# Phased execution wrapper for 500-call budget
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.serpapi_key"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found."
    echo "  echo 'YOUR_KEY' > $ENV_FILE"
    exit 1
fi

export SERPAPI_API_KEY=$(cat "$ENV_FILE" | tr -d '[:space:]')
cd "$SCRIPT_DIR"

PHASE="${1:-A}"
BUDGET="${2:-250}"

echo "=== Phased Search Execution ==="
echo "Phase: $PHASE"
echo "Budget: $BUDGET"
echo ""

/opt/anaconda3/bin/python run_phased_search.py \
    --phase "$PHASE" \
    --budget "$BUDGET" \
    --live --confirm-live-api \
    --sleep-s 1.2 \
    "${@:3}"
