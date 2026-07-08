#!/usr/bin/env bash
# ============================================================================
# run_forecast_v2.sh — forecast-v2 生产部署流水线
# ============================================================================
# 串联 4 步: external_feature_ingest → feature_pipeline → model → writer
#
# 用法:
#   ./run_forecast_v2.sh              # dry-run (默认, 不写 DB)
#   ./run_forecast_v2.sh --execute    # 全量执行 (拉取外部API → 训练 → 写入DB)
#   ./run_forecast_v2.sh --ingest-only  # 只拉取外部特征
#   ./run_forecast_v2.sh --features-only  # 只构建特征 (不训练)
#
# 环境变量:
#   CLEARPATH_DB_HOST / CLEARPATH_DB_PORT / CLEARPATH_DB_USER
#   CLEARPATH_DB_PASSWORD / CLEARPATH_DB_NAME
#   MTA_API_KEY_FILE — MTA GTFS-RT API key 文件路径 (可选)
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output"
EXECUTE=false
INGEST_ONLY=false
FEATURES_ONLY=false

# ── Args ──────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --execute) EXECUTE=true ;;
        --ingest-only) INGEST_ONLY=true ;;
        --features-only) FEATURES_ONLY=true ;;
        *) echo "Unknown arg: $arg"; exit 1 ;;
    esac
done

mkdir -p "$OUTPUT_DIR"

# ── API URLs ──────────────────────────────────────────────────────
WEATHER_URL="https://api.open-meteo.com/v1/forecast?latitude=40.7128&longitude=-74.0060&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m&forecast_days=2&timezone=America%2FNew_York"
HOLIDAY_URL="https://date.nager.at/api/v4/Holidays/US/2026"
GBFS_STATUS_URL="https://gbfs.lyft.com/gbfs/2.3/bkn/en/station_status.json"
GBFS_INFO_URL="https://gbfs.lyft.com/gbfs/2.3/bkn/en/station_information.json"

INGEST_FLAGS=""
MODEL_FLAGS=""
WRITER_FLAGS="--dry-run"

if $EXECUTE; then
    INGEST_FLAGS="--execute"
    WRITER_FLAGS="--execute"
fi

# ════════════════════════════════════════════════════════════════════
# Step 1: External Feature Ingest
# ════════════════════════════════════════════════════════════════════
echo "============================================"
echo "Step 1/4: External Feature Ingest"
echo "============================================"

echo "[1a] weather..."
python3 external_feature_ingest.py --source weather --api-url "$WEATHER_URL" $INGEST_FLAGS 2>&1 | tail -3

echo "[1b] holiday..."
python3 external_feature_ingest.py --source holiday --api-url "$HOLIDAY_URL" $INGEST_FLAGS 2>&1 | tail -3

echo "[1c] gbfs (Citi Bike)..."
python3 external_feature_ingest.py --source gbfs --api-url "$GBFS_STATUS_URL" --station-info-url "$GBFS_INFO_URL" $INGEST_FLAGS 2>&1 | tail -3

# MTA GTFS-RT: 需要 API key, 无则跳过
if [ -n "${MTA_API_KEY_FILE:-}" ] && [ -f "$MTA_API_KEY_FILE" ]; then
    echo "[1d] mta_gtfs_rt..."
    python3 external_feature_ingest.py --source mta_gtfs_rt \
        --api-url "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs" \
        --api-key-file "$MTA_API_KEY_FILE" \
        $INGEST_FLAGS 2>&1 | tail -3
else
    echo "[1d] mta_gtfs_rt: skipped (MTA_API_KEY_FILE not set or not found)"
fi

echo "Step 1 done."
echo

if $INGEST_ONLY; then
    echo "=== --ingest-only: stopping after Step 1 ==="
    exit 0
fi

# ════════════════════════════════════════════════════════════════════
# Step 2: Feature Pipeline (从 DB 构建 training + prediction features)
# ════════════════════════════════════════════════════════════════════
echo "============================================"
echo "Step 2/4: Feature Pipeline (live DB mode)"
echo "============================================"

python3 forecast_v2_feature_pipeline.py \
    --live-db \
    --output-dir "$OUTPUT_DIR" \
    2>&1 | tail -20

echo "Step 2 done: $OUTPUT_DIR/forecast_v2_{training,prediction}_features.csv"
echo

if $FEATURES_ONLY; then
    echo "=== --features-only: stopping after Step 2 ==="
    exit 0
fi

# ════════════════════════════════════════════════════════════════════
# Step 3: Model Training + Prediction Curve
# ════════════════════════════════════════════════════════════════════
echo "============================================"
echo "Step 3/4: Model Training"
echo "============================================"

python3 forecast_v2_model.py \
    --features "$OUTPUT_DIR/forecast_v2_training_features.csv" \
    --pred-features "$OUTPUT_DIR/forecast_v2_prediction_features.csv" \
    --output-dir "$OUTPUT_DIR" \
    2>&1 | tail -25

CURVE_CSV="$OUTPUT_DIR/prediction_curve_v2.csv"
echo "Step 3 done: $CURVE_CSV"
echo

# ════════════════════════════════════════════════════════════════════
# Step 4: Write to busyness_forecasts
# ════════════════════════════════════════════════════════════════════
echo "============================================"
echo "Step 4/4: Write to DB"
echo "============================================"

python3 forecast_v2_writer.py \
    --csv "$CURVE_CSV" \
    --model-version forecast-v2 \
    $WRITER_FLAGS \
    2>&1 | tail -15

echo
echo "============================================"
echo "Pipeline complete."
echo "  --execute=$EXECUTE"
echo "  Output: $OUTPUT_DIR"
echo "============================================"
