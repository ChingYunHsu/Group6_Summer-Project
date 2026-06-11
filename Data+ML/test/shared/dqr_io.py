"""
dqr_io.py — Input/output helpers for the DQR pipeline.

Handles DB reads, CSV exports, and the audit report.
"""

from pathlib import Path
from datetime import datetime

import pandas as pd


# ── Database I/O ──────────────────────────────────────────────

def query_table(table, conn, extra=''):
    """Query a single table into a DataFrame."""
    sql = f'SELECT * FROM {table} {extra}'
    return pd.read_sql(sql, conn)


def load_dqr_tables(conn, table_names):
    """Load multiple tables into a dict of DataFrames.

    Returns
    -------
    dict[str, DataFrame]
        Keyed by table name.  Failed loads yield an empty DataFrame.
    """
    data = {}
    for table in table_names:
        try:
            df = query_table(table, conn)
            data[table] = df
            print(f'{table:30s} → {len(df):>6,} rows, {len(df.columns):>2} cols')
        except Exception as e:
            print(f'{table:30s} → ERROR: {e}')
            data[table] = pd.DataFrame()
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
    """Write all DQR output CSVs in one call.

    Only non-None DataFrames are written.
    """
    output_dir = Path(output_dir)

    exports = {
        'venues_clean.csv':          venues_clean,
        'traffic_hourly.csv':        traffic_clean,
        'weather_current.csv':       weather_clean,
        'dqr_field_summary.csv':     field_summary,
        'dqr_record_analysis.csv':   record_analysis,
        'dqr_outliers.csv':          anomalies,
        'dqr_gps_duplicates.csv':    gps_duplicates,
    }

    for filename, df in exports.items():
        filepath = output_dir / filename
        if df is not None and not df.empty:
            df.to_csv(filepath, index=False)
            print(f'{filename:30s} → {len(df):>6,} rows')
        else:
            # Overwrite stale file with empty CSV to prevent residual data
            if filepath.exists():
                filepath.unlink()
                print(f'{filename:30s} → deleted (no data)')


# ── Audit Report ─────────────────────────────────────────────

def build_audit_report(
    *,
    total_score,
    grade,
    tables_loaded,
    total_rows,
    venues_df,
    venues_clean,
    anomaly_df=None,
    gps_duplicates_df=None,
    actions_df=None,
    output_dir,
):
    """Generate the audit log CSV and return the DataFrame.

    Required: total_score, grade, tables_loaded, total_rows,
              venues_df, venues_clean, output_dir
    Optional: anomaly_df, gps_duplicates_df, actions_df
    """
    anomaly_df = anomaly_df if anomaly_df is not None else pd.DataFrame()
    gps_duplicates_df = gps_duplicates_df if gps_duplicates_df is not None else pd.DataFrame()
    actions_df = actions_df if actions_df is not None else pd.DataFrame()

    audit = pd.DataFrame([
        {'metric': 'dqr_total_score', 'value': f'{total_score:.1f}/100 ({grade})'},
        {'metric': 'tables_analyzed', 'value': tables_loaded},
        {'metric': 'total_records', 'value': total_rows},
        {'metric': 'venues_total', 'value': len(venues_df)},
        {'metric': 'venues_clean', 'value': len(venues_clean)},
        {'metric': 'anomalies_detected', 'value': len(anomaly_df)},
        {'metric': 'gps_duplicates', 'value': len(gps_duplicates_df)},
        {'metric': 'action_items', 'value': len(actions_df)},
        {'metric': 'timestamp', 'value': datetime.now().isoformat()},
    ])

    output_path = Path(output_dir) / 'dqr_report.csv'
    audit.to_csv(output_path, index=False)
    print(audit.to_string(index=False))
    print(f'\n→ Saved: dqr_report.csv')
    return audit
