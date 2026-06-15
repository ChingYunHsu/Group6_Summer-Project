"""dqr_io.py — 数据读写工具。

功能：
  1. 数据库读取（SQL 查询 → DataFrame）
  2. CSV 导出（批量写入 DQR 产物）
  3. 审计报告（生成汇总 CSV）
"""

from pathlib import Path
from datetime import datetime

import pandas as pd


# ── Database I/O ──────────────────────────────────────────────

def query_table(table, conn, extra=''):
    """查询单张表，返回 DataFrame。"""
    sql = f'SELECT * FROM {table} {extra}'  # extra 用于追加过滤条件
    return pd.read_sql(sql, conn)


def load_dqr_tables(conn, table_names):
    """批量加载多张表，失败时返回空 DataFrame（不中断流程）。

    Returns:
        dict[str, DataFrame]: 表名 → DataFrame 的映射
    """
    data = {}  # 表名 → DataFrame
    for table in table_names:
        try:
            df = query_table(table, conn)
            data[table] = df
            print(f'{table:30s} \u2192 {len(df):>6,} rows, {len(df.columns):>2} cols')
        except Exception as e:
            print(f'{table:30s} \u2192 ERROR: {e}')
            data[table] = pd.DataFrame()  # 失败时放空表
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
    """批量导出 DQR 产物为 CSV 文件。只有非空的 DataFrame 才会写入。"""
    output_dir = Path(output_dir)

    # 文件名 → DataFrame 的映射（None 表示不导出）
    exports = {
        'venues_clean.csv':          venues_clean,       # 清洗后的场馆数据
        'traffic_hourly.csv':        traffic_clean,      # 交通流量数据
        'weather_current.csv':       weather_clean,      # 天气数据
        'dqr_field_summary.csv':     field_summary,      # 列级画像
        'dqr_record_analysis.csv':   record_analysis,    # 行级质量评分
        'dqr_outliers.csv':          anomalies,          # 坐标异常记录
        'dqr_gps_duplicates.csv':    gps_duplicates,     # GPS 重复对
    }

    for filename, df in exports.items():
        filepath = output_dir / filename
        if df is not None and not df.empty:
            df.to_csv(filepath, index=False)
            print(f'{filename:30s} → {len(df):>6,} rows')
        else:
            # 删除过期文件，防止残留数据
            if filepath.exists():
                filepath.unlink()
                print(f'{filename:30s} → deleted (no data)')


# ── Audit Report ─────────────────────────────────────────────

def build_audit_report(
    *,
    total_score,    # DQ 总分
    grade,          # 等级（Excellent/Good/Fair/Poor）
    tables_loaded,  # 成功加载的表数量
    total_rows,     # 所有表总行数
    venues_df,      # venues 原始数据
    venues_clean,   # venues 清洗后数据
    anomaly_df=None,        # 坐标异常记录
    gps_duplicates_df=None, # GPS 重复对
    actions_df=None,        # 改进建议
    output_dir,     # 输出目录
):
    """生成审计摘要 CSV，包含 DQ 评分、数据量、异常数等关键指标。"""
    anomaly_df = anomaly_df if anomaly_df is not None else pd.DataFrame()
    gps_duplicates_df = gps_duplicates_df if gps_duplicates_df is not None else pd.DataFrame()
    actions_df = actions_df if actions_df is not None else pd.DataFrame()

    # 构建审计 DataFrame（每行一个指标）
    audit = pd.DataFrame([
        {'metric': 'dqr_total_score', 'value': f'{total_score:.1f}/100 ({grade})'},  # DQ 总分
        {'metric': 'tables_analyzed', 'value': tables_loaded},   # 分析的表数
        {'metric': 'total_records', 'value': total_rows},        # 总行数
        {'metric': 'venues_total', 'value': len(venues_df)},     # 场馆总数
        {'metric': 'venues_clean', 'value': len(venues_clean)},  # 清洗后场馆数
        {'metric': 'anomalies_detected', 'value': len(anomaly_df)},  # 异常数
        {'metric': 'gps_duplicates', 'value': len(gps_duplicates_df)},  # 重复对数
        {'metric': 'action_items', 'value': len(actions_df)},   # 改进建议数
        {'metric': 'timestamp', 'value': datetime.now().isoformat()},  # 生成时间
    ])

    output_path = Path(output_dir) / 'dqr_report.csv'  # 审计报告文件
    audit.to_csv(output_path, index=False)
    print(audit.to_string(index=False))
    print(f'\n→ Saved: dqr_report.csv')
    return audit
