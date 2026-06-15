"""dqr_checks.py — Quality checks + data profiling + cleaning for ML.

Combines: dqr_checks (quality) + dqr_analysis (profiling) + dqr_cleaning (clean)
"""

import re
import time
from datetime import datetime

import numpy as np
import pandas as pd

try:
    from .dqr_utils import validate_coords, is_manhattan, haversine_m
except ImportError:
    from dqr_utils import validate_coords, is_manhattan, haversine_m


# ── 常量 ──────────────────────────────────────────────────────

KEY_FIELDS = {
    'venues': ['venue_id', 'venue_type', 'name', 'latitude', 'longitude', 'district'],
    'restroom_profiles': ['venue_id', 'status', 'restroom_type'],
    'healthcare_profiles': ['venue_id', 'facility_type', 'healthcare_category'],
    'emergency_assets': ['venue_id', 'asset_type', 'floor'],
    'venue_source_links': ['venue_id', 'source_name'],
}

VALID_VENUE_TYPES = {'restroom', 'healthcare', 'emergencyasset', 'clinic',
                     'pharmacy', 'hospital', 'dentist', 'laboratory'}
VALID_DISTRICTS = {'downtown', 'midtown_east', 'midtown_west', 'uptown'}
VALID_RESTROOM_STATUS = {'operational', 'not_operational'}
VALID_BUSYNESS_LEVELS = {'quiet', 'moderate', 'busy', 'no_data'}

FK_CHECKS = [
    ('restroom_profiles', 'venue_id'),
    ('healthcare_profiles', 'venue_id'),
    ('emergency_assets', 'venue_id'),
    ('venue_source_links', 'venue_id'),
    ('busyness_scores', 'venue_id'),
]

DQ_WEIGHTS = {
    'Completeness': 0.25,
    'Accuracy':     0.25,
    'Consistency':  0.15,
    'Uniqueness':   0.15,
    'Timeliness':   0.10,
    'Validity':     0.10,
}


# ═══════════════════════════════════════════════════════════════
# Part 1: Quality Checks
# ═══════════════════════════════════════════════════════════════


def check_completeness(data):
    """计算各表核心字段的填充率，返回 {'passed', 'score', '_dataframe'}"""
    results = []
    for table, fields in KEY_FIELDS.items():
        df = data.get(table, pd.DataFrame())
        if df.empty:
            continue
        for field in fields:
            if field in df.columns:
                filled = df[field].notna().sum()
                total = len(df)
                pct = round(filled / total * 100, 1) if total > 0 else 0
                results.append({
                    'table': table, 'field': field,
                    'filled': filled, 'total': total,
                    'completeness_pct': pct,
                })
    completeness_df = pd.DataFrame(results)
    score = round(completeness_df['completeness_pct'].mean(), 1) if not completeness_df.empty else 0
    return {
        'passed': score >= 80,
        'score': score,
        'metrics': {'field_count': len(completeness_df)},
        'issues': [],
        '_dataframe': completeness_df,
    }


def check_accuracy(venues_df):
    """校验坐标范围、venue_id 格式、district 枚举，返回 _coord_valid_mask"""
    issues = []
    coord_valid_mask = None

    if not venues_df.empty and 'latitude' in venues_df.columns:
        coord_results = venues_df.dropna(subset=['latitude', 'longitude']).apply(
            lambda r: validate_coords(r['latitude'], r['longitude']), axis=1)
        coord_valid_mask = coord_results.apply(lambda t: t[0])
        total_coords = len(coord_valid_mask)
        valid_count = int(coord_valid_mask.sum())
        coord_pct = round(valid_count / total_coords * 100, 1) if total_coords > 0 else 0
    else:
        coord_pct = 0

    vid_pct = 0
    if not venues_df.empty and 'venue_id' in venues_df.columns:
        vid_pattern = re.compile(r'^[0-9a-f]{36}$')
        valid_vids = venues_df['venue_id'].dropna().apply(
            lambda x: bool(vid_pattern.match(str(x)))).sum()
        vid_pct = round(valid_vids / len(venues_df) * 100, 1)

    invalid_districts = set()
    if not venues_df.empty and 'district' in venues_df.columns:
        actual_d = set(venues_df['district'].dropna().unique())
        invalid_districts = actual_d - VALID_DISTRICTS

    score = round(np.mean([coord_pct, vid_pct]), 1)
    if invalid_districts:
        issues.append(f'Invalid districts: {invalid_districts}')

    return {
        'passed': score >= 90 and not invalid_districts,
        'score': score,
        'metrics': {'coord_pct': coord_pct, 'vid_pct': vid_pct,
                     'invalid_districts': sorted(invalid_districts)},
        'issues': issues,
        '_coord_valid_mask': coord_valid_mask,
    }


def check_database_integrity(venues_df):
    """所有场馆必须有 district，诊断 GPS(0,0) 导致的空 district"""
    issues = []
    if venues_df.empty or 'district' not in venues_df.columns:
        return {'passed': False, 'score': 0, 'metrics': {}, 'issues': ['District column missing']}

    null_district = int(venues_df['district'].isna().sum())
    total = len(venues_df)
    pct = round((1 - null_district / total) * 100, 1) if total else 0

    if null_district > 0:
        issues.append(f'{null_district} venues with null district')
        if 'latitude' in venues_df.columns:
            null_mask = venues_df['district'].isna()
            zero_mask = (venues_df['latitude'] == 0) & (venues_df['longitude'] == 0)
            overlap = int((null_mask & zero_mask).sum())
            if overlap > 0:
                issues.append(f'{overlap}/{null_district} have GPS (0,0)')

    return {'passed': null_district == 0, 'score': pct,
            'metrics': {'null_district': null_district, 'total': total}, 'issues': issues}


def check_fk_orphans(venues_df, data):
    """子表 venue_id 必须在 venues 中存在（外键引用完整性）"""
    issues = []
    venue_ids = set(venues_df['venue_id'].values) if not venues_df.empty and 'venue_id' in venues_df.columns else set()

    for table, fk_col in FK_CHECKS:
        df = data.get(table, pd.DataFrame())
        if df.empty or fk_col not in df.columns:
            continue
        fk_values = set(df[fk_col].dropna().values)
        orphan = fk_values - venue_ids
        if orphan:
            issues.append(f'{table}.{fk_col}: {len(orphan)} orphan')

    return {'passed': len(issues) == 0, 'score': 100.0 if not issues else 0.0,
            'metrics': {}, 'issues': issues}


# ═══════════════════════════════════════════════════════════════
# Part 2: DQ Scoring
# ═══════════════════════════════════════════════════════════════


def compute_dq_scores(venues_df, data, anomaly_df, gps_duplicates_df, coord_valid_mask=None):
    """计算六维度加权评分，返回 dict[str, float]"""
    scores = {}
    n = len(venues_df) if not venues_df.empty else 1

    fill_rates = [venues_df[f].notna().mean() for f in KEY_FIELDS.get('venues', []) if f in venues_df.columns]
    scores['Completeness'] = round(np.mean(fill_rates) * 100, 1) if fill_rates else 0

    if coord_valid_mask is not None and len(coord_valid_mask) > 0:
        scores['Accuracy'] = round(coord_valid_mask.mean() * 100, 1)
    elif 'latitude' in venues_df.columns:
        valid = venues_df.dropna(subset=['latitude', 'longitude']).apply(
            lambda r: validate_coords(r['latitude'], r['longitude']), axis=1)
        valid_n = sum(1 for ok, _ in valid if ok)
        total_coords = len(valid) if len(valid) > 0 else 1
        scores['Accuracy'] = round(valid_n / total_coords * 100, 1)
    else:
        scores['Accuracy'] = 0
    anomaly_ratio = min(len(anomaly_df) / max(n, 1), 0.5)
    scores['Accuracy'] = round(max(scores['Accuracy'] - anomaly_ratio * 100, 0), 1)

    if 'borough' in venues_df.columns:
        consistent = venues_df['borough'].str.lower() == 'manhattan'
        scores['Consistency'] = round(consistent.mean() * 100, 1)
    else:
        scores['Consistency'] = 50

    if 'venue_id' in venues_df.columns:
        dup_rate = venues_df['venue_id'].duplicated().mean()
        scores['Uniqueness'] = round((1 - dup_rate) * 100, 1)
    else:
        scores['Uniqueness'] = 0
    gps_ratio = min(len(gps_duplicates_df) / max(n, 1), 0.5)
    scores['Uniqueness'] = round(max(scores['Uniqueness'] - gps_ratio * 100, 0), 1)

    if 'updated_at' in venues_df.columns:
        dates = pd.to_datetime(venues_df['updated_at'], errors='coerce').dropna()
        if len(dates) > 0:
            scores['Timeliness'] = 95 if (dates.max() - dates.min()).days < 365 else 70
        else:
            scores['Timeliness'] = 50
    else:
        scores['Timeliness'] = 50

    if 'venue_type' in venues_df.columns:
        compliance = venues_df['venue_type'].isin(VALID_VENUE_TYPES).mean()
        scores['Validity'] = round(compliance * 100, 1)
    else:
        scores['Validity'] = 0

    return scores


def compute_total_score(scores, weights=None):
    """加权总分 + 等级判定 (Excellent/Good/Fair/Poor)"""
    weights = weights or DQ_WEIGHTS
    total = sum(scores[k] * weights[k] for k in weights)
    if total >= 90:
        grade = 'Excellent'
    elif total >= 80:
        grade = 'Good'
    elif total >= 70:
        grade = 'Fair'
    else:
        grade = 'Poor'
    return total, grade


# ═══════════════════════════════════════════════════════════════
# Part 3: Data Profiling
# ═══════════════════════════════════════════════════════════════


def column_profile(df, table_name):
    """单表列级画像：dtype, non_null, unique, min/max/mean/mode"""
    results = []
    for col in df.columns:
        s = df[col]
        total = len(s)
        non_null = s.notna().sum()
        missing_pct = round((1 - non_null / total) * 100, 1) if total > 0 else 0
        nunique = s.nunique()
        mode_val = s.mode().iloc[0] if not s.mode().empty else None
        min_val = max_val = mean_val = std_val = None
        if pd.api.types.is_numeric_dtype(s):
            min_val = s.min()
            max_val = s.max()
            mean_val = round(s.mean(), 2) if s.notna().any() else None
            std_val = round(s.std(), 2) if s.notna().sum() > 1 else None
        results.append({
            'table': table_name, 'column': col,
            'dtype': str(s.dtype), 'non_null': non_null, 'total': total,
            'missing_pct': missing_pct, 'nunique': nunique,
            'mode': str(mode_val)[:50] if mode_val is not None else None,
            'min': min_val, 'max': max_val, 'mean': mean_val, 'std': std_val,
        })
    return pd.DataFrame(results)


def build_all_profiles(data):
    """全表列级画像"""
    frames = [column_profile(df, name) for name, df in data.items()
              if not df.empty and len(df) > 0]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_record_analysis(venues_df):
    """行级质量评分：每条记录的 0-1 分数"""
    if venues_df.empty:
        return pd.DataFrame()
    record_fields = ['venue_id', 'venue_type', 'name', 'latitude', 'longitude', 'district']
    record_analysis = venues_df[record_fields].copy()
    record_analysis['null_field_count'] = record_analysis[record_fields].isnull().sum(axis=1)
    record_analysis['record_quality_score'] = record_analysis[record_fields].notna().mean(axis=1)
    return record_analysis


def detect_coordinate_anomalies(data):
    """检测 venues 和 pedestrian_ramps 中超出曼哈顿范围或 GPS(0,0) 的记录"""
    anomalies = []
    venues_df = data.get('venues', pd.DataFrame())
    if not venues_df.empty and 'latitude' in venues_df.columns:
        for _, row in venues_df.iterrows():
            lat, lng = row.get('latitude'), row.get('longitude')
            if pd.isna(lat) or pd.isna(lng):
                continue
            lat, lng = float(lat), float(lng)
            if not is_manhattan(lat, lng):
                anomalies.append({'table': 'venues', 'venue_id': row.get('venue_id', ''),
                                  'type': 'outside_manhattan', 'lat': lat, 'lng': lng})
            if lat == 0 and lng == 0:
                anomalies.append({'table': 'venues', 'venue_id': row.get('venue_id', ''),
                                  'type': 'zero_coordinates', 'lat': lat, 'lng': lng})
    pr = data.get('pedestrian_ramps', pd.DataFrame())
    if not pr.empty and 'latitude' in pr.columns:
        for _, row in pr.iterrows():
            lat, lng = row.get('latitude'), row.get('longitude')
            if pd.isna(lat) or pd.isna(lng):
                continue
            if not is_manhattan(float(lat), float(lng)):
                anomalies.append({'table': 'pedestrian_ramps', 'ramp_id': row.get('ramp_id', ''),
                                  'type': 'outside_manhattan', 'lat': float(lat), 'lng': float(lng)})
    return pd.DataFrame(anomalies)


def detect_gps_duplicates(dfs_dict, threshold_m=30):
    """跨表 GPS 重复检测（网格预过滤 + haversine 精确计算）"""
    from math import cos, radians
    t0 = time.perf_counter()
    GRID_LAT = threshold_m / 111_320 * 1.1
    MIN_COS = cos(radians(40.88))
    GRID_LNG = threshold_m / (111_320 * MIN_COS) * 1.1
    R = 6_371_000

    table_grids = {}
    for name, df in dfs_dict.items():
        if df.empty or 'latitude' not in df.columns:
            continue
        mask = df['latitude'].notna() & df['longitude'].notna()
        sub = df.loc[mask]
        if sub.empty:
            continue
        id_col = 'venue_id' if 'venue_id' in sub.columns else 'ramp_id'
        name_col = 'name' if 'name' in sub.columns else sub.columns[0]
        lats = sub['latitude'].astype(float).values
        lngs = sub['longitude'].astype(float).values
        ids = sub[id_col].astype(str).values
        names = sub[name_col].astype(str).str[:50].values
        grid = {}
        for k in range(len(lats)):
            gi, gj = int(lats[k] // GRID_LAT), int(lngs[k] // GRID_LNG)
            key = (gi, gj)
            if key not in grid:
                grid[key] = {'lat': [], 'lng': [], 'ids': [], 'names': []}
            grid[key]['lat'].append(lats[k])
            grid[key]['lng'].append(lngs[k])
            grid[key]['ids'].append(ids[k])
            grid[key]['names'].append(names[k])
        table_grids[name] = {k: {col: np.array(v) for col, v in cell.items()} for k, cell in grid.items()}

    table_names = list(table_grids.keys())
    duplicates = []
    total_candidates = 0

    for i in range(len(table_names)):
        for j in range(i + 1, len(table_names)):
            ga, gb = table_grids[table_names[i]], table_grids[table_names[j]]
            for (gi, gj), a_cell in ga.items():
                cand_lat, cand_lng, cand_ids, cand_names = [], [], [], []
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        b_cell = gb.get((gi + di, gj + dj))
                        if b_cell is not None:
                            cand_lat.append(b_cell['lat'])
                            cand_lng.append(b_cell['lng'])
                            cand_ids.append(b_cell['ids'])
                            cand_names.append(b_cell['names'])
                if not cand_lat:
                    continue
                b_lat = np.concatenate(cand_lat)
                b_lng = np.concatenate(cand_lng)
                b_ids = np.concatenate(cand_ids)
                b_names_arr = np.concatenate(cand_names)
                total_candidates += len(a_cell['lat']) * len(b_lat)
                a_lat_r = np.radians(a_cell['lat'])
                a_lng_r = np.radians(a_cell['lng'])
                b_lat_r = np.radians(b_lat)
                b_lng_r = np.radians(b_lng)
                dlat = b_lat_r[np.newaxis, :] - a_lat_r[:, np.newaxis]
                dlng = b_lng_r[np.newaxis, :] - a_lng_r[:, np.newaxis]
                hav = (np.sin(dlat / 2) ** 2
                       + np.cos(a_lat_r[:, np.newaxis]) * np.cos(b_lat_r[np.newaxis, :])
                       * np.sin(dlng / 2) ** 2)
                dists = R * 2 * np.arctan2(np.sqrt(hav), np.sqrt(1 - hav))
                rows_idx, cols_idx = np.where(dists < threshold_m)
                for r, c in zip(rows_idx, cols_idx):
                    duplicates.append({
                        'table_a': table_names[i], 'id_a': a_cell['ids'][r],
                        'name_a': a_cell['names'][r], 'table_b': table_names[j],
                        'id_b': b_ids[c], 'name_b': b_names_arr[c],
                        'distance_m': round(float(dists[r, c]), 1),
                    })

    elapsed = time.perf_counter() - t0
    print(f'GPS duplicates: {len(duplicates)} pairs found in {elapsed:.2f}s')
    return pd.DataFrame(duplicates)


# ═══════════════════════════════════════════════════════════════
# Part 4: Cleaning
# ═══════════════════════════════════════════════════════════════


def clean_venues(venues_df, coord_valid_mask=None, quality_scores=None):
    """清洗 venues：去空行、过滤异常坐标、修复 borough、附加质量分数"""
    if venues_df.empty:
        return venues_df.copy()
    clean = venues_df.copy()
    clean = clean.dropna(how='all')

    # Step 1: 过滤异常坐标
    if coord_valid_mask is not None and len(coord_valid_mask) == len(clean):
        valid_mask = coord_valid_mask.values if hasattr(coord_valid_mask, 'values') else coord_valid_mask
        removed = int((~valid_mask).sum())
        clean = clean[valid_mask]
        print(f'  Coords: removed {removed} invalid records (cached mask)')
    elif 'latitude' in clean.columns and 'longitude' in clean.columns:
        clean['lat_valid'] = clean.apply(
            lambda r: validate_coords(r.get('latitude'), r.get('longitude'))[0], axis=1)
        removed = int((~clean['lat_valid']).sum())
        clean = clean[clean['lat_valid']].drop(columns=['lat_valid'])
        print(f'  Coords: removed {removed} invalid records')

    # Step 2: 修复 borough（坐标在曼哈顿但 borough 不是 Manhattan 的，统一修正）
    if 'borough' in clean.columns and 'latitude' in clean.columns:
        fixed = 0
        for idx, row in clean.iterrows():
            if pd.notna(row.get('latitude')) and pd.notna(row.get('longitude')):
                if is_manhattan(float(row['latitude']), float(row['longitude'])):
                    if row.get('borough') != 'Manhattan':
                        clean.at[idx, 'borough'] = 'Manhattan'
                        fixed += 1
        if fixed > 0:
            print(f'  Borough: fixed {fixed} records → Manhattan')

    # Step 3: 附加质量分数
    if quality_scores is not None and len(quality_scores) == len(clean):
        clean['quality_score'] = quality_scores.values
    else:
        key_fields = ['venue_id', 'venue_type', 'name', 'latitude', 'longitude', 'district']
        clean['quality_score'] = clean.apply(
            lambda r: sum(1 for f in key_fields
                          if pd.notna(r.get(f)) and str(r.get(f, '')).strip()) / len(key_fields), axis=1)

    print(f'  Kept: {len(clean)} records (quality_score mean={clean["quality_score"].mean():.2f})')
    return clean


# ═══════════════════════════════════════════════════════════════
# Part 5: Action Items & ML Usability
# ═══════════════════════════════════════════════════════════════


def build_action_items(venues_df, data, scores):
    """自动生成优先级改进建议"""
    actions = []
    if not venues_df.empty and 'latitude' in venues_df.columns:
        null_coords = int(venues_df['latitude'].isna().sum())
        if null_coords > 0:
            actions.append({'priority': 'P0', 'issue': f'{null_coords} venues with null coordinates',
                            'recommendation': 'Geocode or remove records without coordinates', 'owner': 'Data+ML'})
    if not venues_df.empty and 'district' in venues_df.columns:
        null_district = int(venues_df['district'].isna().sum())
        if null_district > 0:
            actions.append({'priority': 'P1', 'issue': f'{null_district} venues with null district',
                            'recommendation': 'Apply gps_to_district() to fill missing districts', 'owner': 'Data+ML'})
    if not venues_df.empty and 'venue_type' in venues_df.columns:
        for vt, cnt in venues_df['venue_type'].value_counts().items():
            if cnt < 5:
                actions.append({'priority': 'P2', 'issue': f'venue_type={vt} has only {cnt} records',
                                'recommendation': 'Review if data was loaded correctly', 'owner': 'Data+ML'})
    ecc = data.get('external_context_cache', pd.DataFrame())
    if not ecc.empty and 'expires_at' in ecc.columns:
        expired = pd.to_datetime(ecc['expires_at'], errors='coerce') < pd.Timestamp.now()
        if expired.sum() > 0:
            actions.append({'priority': 'P1', 'issue': f'{int(expired.sum())} expired cache entries',
                            'recommendation': 'Refresh external_context_cache entries', 'owner': 'Backend'})
    if scores.get('Completeness', 0) < 80:
        actions.append({'priority': 'P0', 'issue': f'Completeness score {scores["Completeness"]}% < 80%',
                        'recommendation': 'Audit and fill missing fields', 'owner': 'Data+ML'})
    if scores.get('Accuracy', 0) < 90:
        actions.append({'priority': 'P1', 'issue': f'Accuracy score {scores["Accuracy"]}% < 90%',
                        'recommendation': 'Review coordinate and format validation failures', 'owner': 'Data+ML'})
    if not actions:
        actions.append({'priority': '-', 'issue': 'No issues found',
                        'recommendation': 'Data quality is acceptable', 'owner': '-'})
    return pd.DataFrame(actions)


def assess_ml_usability(venues_clean, traffic_clean, weather_clean, scores, grade):
    """ML 可用性评估：场馆数、坐标完整率、DQ 分数"""
    return {
        'venues_count': len(venues_clean) if not venues_clean.empty else 0,
        'venue_types': int(venues_clean['venue_type'].nunique()) if not venues_clean.empty else 0,
        'coord_complete_pct': round(venues_clean['latitude'].notna().mean() * 100, 0) if not venues_clean.empty and 'latitude' in venues_clean.columns else 0,
        'district_count': int(venues_clean['district'].nunique()) if not venues_clean.empty and 'district' in venues_clean.columns else 0,
        'quality_score_mean': round(venues_clean['quality_score'].mean(), 2) if not venues_clean.empty and 'quality_score' in venues_clean.columns else 0,
        'traffic_rows': len(traffic_clean) if not traffic_clean.empty else 0,
        'traffic_segments': int(traffic_clean['segmentid'].nunique()) if not traffic_clean.empty else 0,
        'weather_condition': weather_clean.iloc[0]['condition'] if not weather_clean.empty else 'N/A',
        'dq_score': scores, 'dq_grade': grade,
    }
