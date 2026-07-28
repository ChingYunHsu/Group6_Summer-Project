"""dqr_io.py — data read/write utilities.

Functions:
  1. Database reads (SQL query → DataFrame)
  2. CSV export (bulk write DQR artifacts)
  3. Audit report (generate summary CSV)
"""

from pathlib import Path
from datetime import datetime

import pandas as pd


# ── Database I/O ──────────────────────────────────────────────

def query_table(table, conn, extra=''):
    """Query a single table, return DataFrame."""
    sql = f'SELECT * FROM {table} {extra}'  # extra for appending filter conditions
    return pd.read_sql(sql, conn)


def load_dqr_tables(conn, table_names):
    """Batch load multiple tables, return empty DataFrame on failure (do not interrupt pipeline).

    Returns:
        dict[str, DataFrame]: table name → DataFrame mapping
    """
    data = {}  # table name → DataFrame
    for table in table_names:
        try:
            df = query_table(table, conn)
            data[table] = df
            print(f'{table:30s} \u2192 {len(df):>6,} rows, {len(df.columns):>2} cols')
        except Exception as e:
            print(f'{table:30s} \u2192 ERROR: {e}')
            data[table] = pd.DataFrame()  # Return empty DataFrame on failure
    return data


# ── CSV Export ────────────────────────────────────────────────

def export_dqr_artifacts(
    output_dir,
    *,
    venues_clean=None,
    traffic_clean=None,
    weather_clean=None,
    field_summary=None,
    record_analysis=None,
    anomalies=None,
    gps_duplicates=None,
):
    """Batch export DQR artifacts as CSV files. Only non-empty DataFrames are written."""
    output_dir = Path(output_dir)

    # filename → DataFrame mapping (None means skip export)
    exports = {
        'venues_clean.csv':          venues_clean,       # Cleaned venue data
        'traffic_hourly.csv':        traffic_clean,      # Traffic flow data
        'weather_current.csv':       weather_clean,      # Weather data
        'dqr_field_summary.csv':     field_summary,      # Column-level profile
        'dqr_record_analysis.csv':   record_analysis,    # Row-level quality scores
        'dqr_outliers.csv':          anomalies,          # Coordinate anomaly records
        'dqr_gps_duplicates.csv':    gps_duplicates,     # GPS duplicate pairs
    }

    for filename, df in exports.items():
        filepath = output_dir / filename
        if df is not None and not df.empty:
            df.to_csv(filepath, index=False)
            print(f'{filename:30s} → {len(df):>6,} rows')
        else:
            # Remove stale files to prevent residual data
            if filepath.exists():
                filepath.unlink()
                print(f'{filename:30s} → deleted (no data)')


# ── Audit Report ─────────────────────────────────────────────

def build_audit_report(
    *,
    total_score,    # DQ total score
    grade,          # Grade (Excellent/Good/Fair/Poor)
    tables_loaded,  # Number of tables successfully loaded
    total_rows,     # Total rows across all tables
    venues_df,      # Raw venues data
    venues_clean,   # Cleaned venues data
    anomaly_df=None,        # Coordinate anomaly records
    gps_duplicates_df=None, # GPS duplicate pairs
    actions_df=None,        # Improvement suggestions
    output_dir,     # Output directory
):
    """Generate audit summary CSV with DQ score, data volume, anomaly count, and other key metrics."""
    anomaly_df = anomaly_df if anomaly_df is not None else pd.DataFrame()
    gps_duplicates_df = gps_duplicates_df if gps_duplicates_df is not None else pd.DataFrame()
    actions_df = actions_df if actions_df is not None else pd.DataFrame()

    # Build audit DataFrame (one row per metric)
    audit = pd.DataFrame([
        {'metric': 'dqr_total_score', 'value': f'{total_score:.1f}/100 ({grade})'},  # DQ total score
        {'metric': 'tables_analyzed', 'value': tables_loaded},   # Tables analyzed
        {'metric': 'total_records', 'value': total_rows},        # Total rows
        {'metric': 'venues_total', 'value': len(venues_df)},     # Total venues
        {'metric': 'venues_clean', 'value': len(venues_clean)},  # Cleaned venues
        {'metric': 'anomalies_detected', 'value': len(anomaly_df)},  # Anomalies detected
        {'metric': 'gps_duplicates', 'value': len(gps_duplicates_df)},  # GPS duplicates
        {'metric': 'action_items', 'value': len(actions_df)},   # Action items
        {'metric': 'timestamp', 'value': datetime.now().isoformat()},  # Generation timestamp
    ])

    output_path = Path(output_dir) / 'dqr_report.csv'  # Audit report file
    audit.to_csv(output_path, index=False)
    print(audit.to_string(index=False))
    print(f'\n→ Saved: dqr_report.csv')
    return audit
