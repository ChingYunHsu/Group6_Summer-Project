"""
dqr_analysis.py — Heavy analysis functions for the DQR pipeline.

Column profiling, anomaly detection, GPS duplicate detection,
action items, and ML usability assessment.
"""

import time
from datetime import datetime

import numpy as np
import pandas as pd

from dqr_utils import is_manhattan


# ── Column profiling ──────────────────────────────────────────

def column_profile(df, table_name):
    """Column-level profiling: dtype, non-null rate, unique, min/max/mode."""
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
    """Column profiling across all non-empty tables."""
    frames = [column_profile(df, name) for name, df in data.items()
              if not df.empty and len(df) > 0]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# ── Record-level analysis ────────────────────────────────────

def build_record_analysis(venues_df):
    """Per-record quality score for the venues table."""
    if venues_df.empty:
        return pd.DataFrame()

    record_fields = ['venue_id', 'venue_type', 'name', 'latitude', 'longitude', 'district']
    record_analysis = venues_df[record_fields].copy()
    record_analysis['null_field_count'] = record_analysis[record_fields].isnull().sum(axis=1)
    record_analysis['record_quality_score'] = record_analysis[record_fields].notna().mean(axis=1)
    return record_analysis


# ── Coordinate anomaly detection ─────────────────────────────

def detect_coordinate_anomalies(data):
    """Find venues and ramps outside Manhattan or with zero coordinates."""
    anomalies = []

    # Venues
    venues_df = data.get('venues', pd.DataFrame())
    if not venues_df.empty and 'latitude' in venues_df.columns:
        for _, row in venues_df.iterrows():
            lat, lng = row.get('latitude'), row.get('longitude')
            if pd.isna(lat) or pd.isna(lng):
                continue
            lat, lng = float(lat), float(lng)
            if not is_manhattan(lat, lng):
                anomalies.append({
                    'table': 'venues', 'venue_id': row.get('venue_id', ''),
                    'type': 'outside_manhattan', 'lat': lat, 'lng': lng,
                })
            if lat == 0 and lng == 0:
                anomalies.append({
                    'table': 'venues', 'venue_id': row.get('venue_id', ''),
                    'type': 'zero_coordinates', 'lat': lat, 'lng': lng,
                })

    # Pedestrian ramps
    pr = data.get('pedestrian_ramps', pd.DataFrame())
    if not pr.empty and 'latitude' in pr.columns:
        for _, row in pr.iterrows():
            lat, lng = row.get('latitude'), row.get('longitude')
            if pd.isna(lat) or pd.isna(lng):
                continue
            if not is_manhattan(float(lat), float(lng)):
                anomalies.append({
                    'table': 'pedestrian_ramps',
                    'ramp_id': row.get('ramp_id', ''),
                    'type': 'outside_manhattan',
                    'lat': float(lat), 'lng': float(lng),
                })

    return pd.DataFrame(anomalies)


# ── GPS duplicate detection ──────────────────────────────────

def detect_gps_duplicates(dfs_dict, threshold_m=30):
    """Detect GPS duplicates across tables using a lat/lng grid pre-filter.

    Grid size ~ threshold_m in degrees, so each venue only compares against
    ramps in the same or 8 neighbouring cells.  Haversine is then computed
    with numpy broadcasting only on the small candidate subsets.

    The longitude grid is scaled by cos(lat) to account for convergence of
    meridians — without this, points within threshold_m in longitude can
    land in non-adjacent cells at high latitudes.
    """
    t0 = time.perf_counter()

    # Grid cell sizes: lat uses 111_320 m/°, lng uses 111_320*cos(lat) m/°
    # Use cos(40.88°) as the conservative (smallest cos) for Manhattan's range
    # so all points within threshold are guaranteed to land in adjacent cells.
    from math import cos, radians
    GRID_LAT = threshold_m / 111_320 * 1.1
    MIN_COS = cos(radians(40.88))  # ~0.756, worst case for Manhattan
    GRID_LNG = threshold_m / (111_320 * MIN_COS) * 1.1
    R = 6_371_000

    # Collect per-table points with grid keys
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
            gi = int(lats[k] // GRID_LAT)
            gj = int(lngs[k] // GRID_LNG)
            key = (gi, gj)
            if key not in grid:
                grid[key] = {'lat': [], 'lng': [], 'ids': [], 'names': []}
            grid[key]['lat'].append(lats[k])
            grid[key]['lng'].append(lngs[k])
            grid[key]['ids'].append(ids[k])
            grid[key]['names'].append(names[k])

        table_grids[name] = {
            k: {col: np.array(v) for col, v in cell.items()}
            for k, cell in grid.items()
        }

    # Cross-table grid comparison
    table_names = list(table_grids.keys())
    duplicates = []
    total_candidates = 0

    for i in range(len(table_names)):
        for j in range(i + 1, len(table_names)):
            ga = table_grids[table_names[i]]
            gb = table_grids[table_names[j]]

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

                # Vectorized haversine
                a_lat_r = np.radians(a_cell['lat'])
                a_lng_r = np.radians(a_cell['lng'])
                b_lat_r = np.radians(b_lat)
                b_lng_r = np.radians(b_lng)

                dlat = b_lat_r[np.newaxis, :] - a_lat_r[:, np.newaxis]
                dlng = b_lng_r[np.newaxis, :] - a_lng_r[:, np.newaxis]
                hav = (np.sin(dlat / 2) ** 2
                       + np.cos(a_lat_r[:, np.newaxis])
                       * np.cos(b_lat_r[np.newaxis, :])
                       * np.sin(dlng / 2) ** 2)
                dists = R * 2 * np.arctan2(np.sqrt(hav), np.sqrt(1 - hav))

                rows_idx, cols_idx = np.where(dists < threshold_m)
                for r, c in zip(rows_idx, cols_idx):
                    duplicates.append({
                        'table_a': table_names[i],
                        'id_a':    a_cell['ids'][r],
                        'name_a':  a_cell['names'][r],
                        'table_b': table_names[j],
                        'id_b':    b_ids[c],
                        'name_b':  b_names_arr[c],
                        'distance_m': round(float(dists[r, c]), 1),
                    })

    elapsed = time.perf_counter() - t0
    brute_force = sum(
        len(dfs_dict[a]['latitude'].dropna()) * len(dfs_dict[b]['latitude'].dropna())
        for a, b in [(ta, tb) for i, ta in enumerate(table_names) for tb in table_names[i+1:]]
        if not dfs_dict[a].empty and not dfs_dict[b].empty
    ) if len(table_names) >= 2 else 0
    print(f'Grid pre-filter: {brute_force:>13,} brute-force → {total_candidates:>12,} candidates '
          f'({total_candidates/max(brute_force,1)*100:.2f}%)')
    print(f'Execution time:  {elapsed:.2f}s')

    return pd.DataFrame(duplicates)


# ── Action items ─────────────────────────────────────────────

def build_action_items(venues_df, data, scores):
    """Auto-generate prioritised action items from check results."""
    actions = []

    if not venues_df.empty and 'latitude' in venues_df.columns:
        null_coords = int(venues_df['latitude'].isna().sum())
        if null_coords > 0:
            actions.append({
                'priority': 'P0',
                'issue': f'{null_coords} venues with null coordinates',
                'recommendation': 'Geocode or remove records without coordinates',
                'owner': 'Data+ML',
            })

    if not venues_df.empty and 'district' in venues_df.columns:
        null_district = int(venues_df['district'].isna().sum())
        if null_district > 0:
            actions.append({
                'priority': 'P1',
                'issue': f'{null_district} venues with null district',
                'recommendation': 'Apply gps_to_district() to fill missing districts',
                'owner': 'Data+ML',
            })

    if not venues_df.empty and 'venue_type' in venues_df.columns:
        for vt, cnt in venues_df['venue_type'].value_counts().items():
            if cnt < 5:
                actions.append({
                    'priority': 'P2',
                    'issue': f'venue_type={vt} has only {cnt} records',
                    'recommendation': 'Review if data was loaded correctly',
                    'owner': 'Data+ML',
                })

    ecc = data.get('external_context_cache', pd.DataFrame())
    if not ecc.empty and 'expires_at' in ecc.columns:
        expired = pd.to_datetime(ecc['expires_at'], errors='coerce') < pd.Timestamp.now()
        if expired.sum() > 0:
            actions.append({
                'priority': 'P1',
                'issue': f'{int(expired.sum())} expired cache entries',
                'recommendation': 'Refresh external_context_cache entries',
                'owner': 'Backend',
            })

    if scores.get('Completeness', 0) < 80:
        actions.append({
            'priority': 'P0',
            'issue': f'Completeness score {scores["Completeness"]}% < 80%',
            'recommendation': 'Audit and fill missing fields',
            'owner': 'Data+ML',
        })
    if scores.get('Accuracy', 0) < 90:
        actions.append({
            'priority': 'P1',
            'issue': f'Accuracy score {scores["Accuracy"]}% < 90%',
            'recommendation': 'Review coordinate and format validation failures',
            'owner': 'Data+ML',
        })

    if not actions:
        actions.append({
            'priority': '-',
            'issue': 'No issues found',
            'recommendation': 'Data quality is acceptable',
            'owner': '-',
        })

    return pd.DataFrame(actions)


# ── ML Usability Assessment ──────────────────────────────────

def assess_ml_usability(venues_clean, traffic_clean, weather_clean, scores, grade):
    """Print ML usability summary.  Returns the dict for programmatic use."""
    result = {
        'venues_count': len(venues_clean) if not venues_clean.empty else 0,
        'venue_types': int(venues_clean['venue_type'].nunique()) if not venues_clean.empty else 0,
        'coord_complete_pct': round(venues_clean['latitude'].notna().mean() * 100, 0) if not venues_clean.empty and 'latitude' in venues_clean.columns else 0,
        'district_count': int(venues_clean['district'].nunique()) if not venues_clean.empty and 'district' in venues_clean.columns else 0,
        'quality_score_mean': round(venues_clean['quality_score'].mean(), 2) if not venues_clean.empty and 'quality_score' in venues_clean.columns else 0,
        'traffic_rows': len(traffic_clean) if not traffic_clean.empty else 0,
        'traffic_segments': int(traffic_clean['segmentid'].nunique()) if not traffic_clean.empty else 0,
        'weather_condition': weather_clean.iloc[0]['condition'] if not weather_clean.empty else 'N/A',
        'dq_score': scores,
        'dq_grade': grade,
    }
    return result
