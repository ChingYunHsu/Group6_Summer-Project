"""
dqr_checks.py — Deterministic quality checks for the DQR pipeline.

Every check returns a standard dict:
    {"passed": bool, "score": float, "metrics": {}, "issues": []}

pytest can import these directly — no notebook dependency.
"""

import re
from datetime import datetime

import numpy as np
import pandas as pd

from dqr_utils import validate_coords


# ── Constants ─────────────────────────────────────────────────

KEY_FIELDS = {
    'venues': ['venue_id', 'venue_type', 'name', 'latitude', 'longitude', 'district'],
    'restroom_profiles': ['venue_id', 'status', 'restroom_type'],
    'healthcare_profiles': ['venue_id', 'facility_type', 'healthcare_category'],
    'emergency_assets': ['venue_id', 'asset_type', 'floor'],
    'venue_source_links': ['venue_id', 'source_name'],
}

VALID_VENUE_TYPES = {'restroom', 'healthcare', 'emergency_asset', 'clinic',
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

EXPECTED_EVENT_TYPES = {
    'elevator_broken',
    'wheelchair_lift_broken',
    'toilet_out_of_order',
    'large_crowd',
    'protest_or_blockage',
    'entrance_closed',
    'ramp_blocked',
    'closed_early',
}


# ── Individual checks ─────────────────────────────────────────

def check_completeness(data):
    """Field-level completeness for KEY_FIELDS across tables."""
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
    """Coordinate range, venue_id format, district ENUM."""
    issues = []

    # Coordinate range
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

    # venue_id format (36-char hex)
    vid_pct = 0
    if not venues_df.empty and 'venue_id' in venues_df.columns:
        vid_pattern = re.compile(r'^[0-9a-f]{36}$')
        valid_vids = venues_df['venue_id'].dropna().apply(
            lambda x: bool(vid_pattern.match(str(x)))).sum()
        vid_pct = round(valid_vids / len(venues_df) * 100, 1)

    # District ENUM
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
        'metrics': {
            'coord_pct': coord_pct,
            'vid_pct': vid_pct,
            'invalid_districts': sorted(invalid_districts),
        },
        'issues': issues,
        '_coord_valid_mask': coord_valid_mask,
    }


def check_consistency(venues_df, data):
    """borough == Manhattan rate, venue_type distribution, source_name values."""
    issues = []
    metrics = {}

    # borough consistency
    if not venues_df.empty and 'borough' in venues_df.columns:
        borough_values = list(venues_df['borough'].dropna().unique())
        non_manhattan = venues_df[venues_df['borough'].str.lower() != 'manhattan']
        manhattan_pct = round((1 - len(non_manhattan) / len(venues_df)) * 100, 1) if len(venues_df) > 0 else 0
        metrics['borough_manhattan_pct'] = manhattan_pct
        metrics['borough_values'] = borough_values
        if len(non_manhattan) > 0:
            issues.append(f'{len(non_manhattan)} records with borough != Manhattan')
    else:
        manhattan_pct = 50

    # venue_type distribution
    if not venues_df.empty and 'venue_type' in venues_df.columns:
        metrics['venue_type_dist'] = venues_df['venue_type'].value_counts().to_dict()

    # source_name consistency
    vsl = data.get('venue_source_links', pd.DataFrame())
    if not vsl.empty and 'source_name' in vsl.columns:
        metrics['source_names'] = list(vsl['source_name'].unique())

    return {
        'passed': len(issues) == 0,
        'score': manhattan_pct,
        'metrics': metrics,
        'issues': issues,
    }


def check_uniqueness(data):
    """Primary key uniqueness across tables."""
    issues = []
    all_ok = True

    for table, key in FK_CHECKS + [('pedestrian_ramps', 'ramp_id')]:
        df = data.get(table, pd.DataFrame())
        if df.empty:
            continue
        if isinstance(key, list):
            dup_count = int(df.duplicated(subset=key).sum())
        else:
            if key not in df.columns:
                continue
            dup_count = int(df[key].duplicated().sum())
        if dup_count > 0:
            issues.append(f'{table}.{key}: {dup_count} duplicates')
            all_ok = False

    return {
        'passed': all_ok,
        'score': 100.0 if all_ok else 0.0,
        'metrics': {},
        'issues': issues,
    }


def check_timeliness(venues_df, data):
    """Data freshness: created_at/updated_at < 1 year, cache expiry."""
    issues = []
    metrics = {}
    score = 50

    if not venues_df.empty:
        for time_col in ['created_at', 'updated_at']:
            if time_col in venues_df.columns:
                dates = pd.to_datetime(venues_df[time_col], errors='coerce').dropna()
                if len(dates) > 0:
                    metrics[f'venues.{time_col}'] = {
                        'min': str(dates.min()),
                        'max': str(dates.max()),
                        'n': len(dates),
                    }

    ecc = data.get('external_context_cache', pd.DataFrame())
    if not ecc.empty and 'expires_at' in ecc.columns:
        now = pd.Timestamp.now()
        expired = pd.to_datetime(ecc['expires_at'], errors='coerce') < now
        expired_count = int(expired.sum())
        metrics['ecc_expired'] = expired_count
        if expired_count > 0:
            issues.append(f'{expired_count} expired cache entries')

    # Score: 95 if all data < 1 year old
    if not venues_df.empty and 'updated_at' in venues_df.columns:
        dates = pd.to_datetime(venues_df['updated_at'], errors='coerce').dropna()
        if len(dates) > 0:
            score = 95 if (dates.max() - dates.min()).days < 365 else 70

    return {
        'passed': len(issues) == 0,
        'score': score,
        'metrics': metrics,
        'issues': issues,
    }


def check_validity(data):
    """ENUM compliance for venue_type, restroom_profiles.status, busyness_scores.level."""
    issues = []
    all_violations = 0

    venues_df = data.get('venues', pd.DataFrame())
    if not venues_df.empty and 'venue_type' in venues_df.columns:
        violations = int((~venues_df['venue_type'].isin(VALID_VENUE_TYPES)).sum())
        all_violations += violations

    rp = data.get('restroom_profiles', pd.DataFrame())
    if not rp.empty and 'status' in rp.columns:
        violations = int((~rp['status'].isin(VALID_RESTROOM_STATUS) & rp['status'].notna()).sum())
        all_violations += violations

    bs = data.get('busyness_scores', pd.DataFrame())
    if not bs.empty and 'level' in bs.columns:
        violations = int((~bs['level'].isin(VALID_BUSYNESS_LEVELS) & bs['level'].notna()).sum())
        all_violations += violations

    score = 100.0 if all_violations == 0 else 0.0
    if all_violations > 0:
        issues.append(f'{all_violations} ENUM violations across tables')

    return {
        'passed': all_violations == 0,
        'score': score,
        'metrics': {'total_violations': all_violations},
        'issues': issues,
    }


def check_database_integrity(venues_df):
    """D2.7: 100% venues must have non-null district."""
    issues = []
    if venues_df.empty or 'district' not in venues_df.columns:
        return {'passed': False, 'score': 0, 'metrics': {}, 'issues': ['District column missing']}

    null_district = int(venues_df['district'].isna().sum())
    total = len(venues_df)
    pct = round((1 - null_district / total) * 100, 1) if total else 0

    if null_district > 0:
        issues.append(f'{null_district} venues with null district')
        # Diagnose: null district caused by zero coordinates?
        if 'latitude' in venues_df.columns:
            null_mask = venues_df['district'].isna()
            zero_mask = (venues_df['latitude'] == 0) & (venues_df['longitude'] == 0)
            overlap = int((null_mask & zero_mask).sum())
            if overlap > 0:
                issues.append(f'{overlap}/{null_district} have GPS (0,0)')

    return {
        'passed': null_district == 0,
        'score': pct,
        'metrics': {'null_district': null_district, 'total': total},
        'issues': issues,
    }


def check_fk_orphans(venues_df, data):
    """FK referential integrity: every FK value must exist in venues."""
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

    return {
        'passed': len(issues) == 0,
        'score': 100.0 if not issues else 0.0,
        'metrics': {},
        'issues': issues,
    }


def validate_event_types(data):
    """Check user_reports.issue_type against EXPECTED_EVENT_TYPES."""
    ur = data.get('user_reports', pd.DataFrame())
    if ur.empty or 'issue_type' not in ur.columns:
        return None

    actual = set(ur['issue_type'].dropna().unique())
    return {
        'actual': sorted(actual),
        'expected': sorted(EXPECTED_EVENT_TYPES),
        'unknown': sorted(actual - EXPECTED_EVENT_TYPES),
        'missing': sorted(EXPECTED_EVENT_TYPES - actual),
    }


# ── DQ Score ─────────────────────────────────────────────────

def compute_dq_scores(venues_df, data, anomaly_df, gps_duplicates_df, coord_valid_mask=None):
    """Compute the 6 DQR dimension scores for the venues table.

    Parameters
    ----------
    coord_valid_mask : pd.Series or None
        Pre-computed validate_coords boolean mask from check_accuracy().
    anomaly_df : pd.DataFrame
        Coordinate anomalies — penalises Accuracy score.
    gps_duplicates_df : pd.DataFrame
        GPS duplicate pairs — penalises Uniqueness score.
    """
    scores = {}
    n = len(venues_df) if not venues_df.empty else 1

    # Completeness
    fill_rates = [venues_df[f].notna().mean() for f in KEY_FIELDS.get('venues', []) if f in venues_df.columns]
    scores['Completeness'] = round(np.mean(fill_rates) * 100, 1) if fill_rates else 0

    # Accuracy
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

    # Consistency
    if 'borough' in venues_df.columns:
        consistent = venues_df['borough'].str.lower() == 'manhattan'
        scores['Consistency'] = round(consistent.mean() * 100, 1)
    else:
        scores['Consistency'] = 50

    # Uniqueness
    if 'venue_id' in venues_df.columns:
        dup_rate = venues_df['venue_id'].duplicated().mean()
        scores['Uniqueness'] = round((1 - dup_rate) * 100, 1)
    else:
        scores['Uniqueness'] = 0
    gps_ratio = min(len(gps_duplicates_df) / max(n, 1), 0.5)
    scores['Uniqueness'] = round(max(scores['Uniqueness'] - gps_ratio * 100, 0), 1)

    # Timeliness
    if 'updated_at' in venues_df.columns:
        dates = pd.to_datetime(venues_df['updated_at'], errors='coerce').dropna()
        if len(dates) > 0:
            scores['Timeliness'] = 95 if (dates.max() - dates.min()).days < 365 else 70
        else:
            scores['Timeliness'] = 50
    else:
        scores['Timeliness'] = 50

    # Validity
    if 'venue_type' in venues_df.columns:
        compliance = venues_df['venue_type'].isin(VALID_VENUE_TYPES).mean()
        scores['Validity'] = round(compliance * 100, 1)
    else:
        scores['Validity'] = 0

    return scores


def compute_total_score(scores, weights=None):
    """Weighted total score and grade from dimension scores."""
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


# ── Convenience runner ────────────────────────────────────────

def run_all_checks(data, venues_df):
    """Run every deterministic check and return a summary dict.

    Returns
    -------
    dict with keys: completeness, accuracy, consistency, uniqueness,
                    timeliness, validity, integrity, fk_orphans, event_types,
                    coord_valid_mask, scores, total_score, grade
    """
    results = {}

    results['completeness'] = check_completeness(data)
    results['accuracy'] = check_accuracy(venues_df)
    results['consistency'] = check_consistency(venues_df, data)
    results['uniqueness'] = check_uniqueness(data)
    results['timeliness'] = check_timeliness(venues_df, data)
    results['validity'] = check_validity(data)
    results['integrity'] = check_database_integrity(venues_df)
    results['fk_orphans'] = check_fk_orphans(venues_df, data)
    results['event_types'] = validate_event_types(data)

    # Carry forward coord_valid_mask from accuracy check
    results['coord_valid_mask'] = results['accuracy'].pop('_coord_valid_mask', None)

    return results
