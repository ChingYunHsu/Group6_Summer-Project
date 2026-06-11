"""
dqr_cleaning.py — Pure cleaning/transformation for the DQR pipeline.

All functions copy their input — they never mutate the caller's DataFrame.
"""

import pandas as pd

from dqr_utils import validate_coords


def clean_venues(venues_df, coord_valid_mask=None, quality_scores=None):
    """Clean venues table: drop null rows, validate coords, attach quality score.

    Parameters
    ----------
    coord_valid_mask : pd.Series or None
        Pre-computed coordinate validity from check_accuracy().
    quality_scores : pd.Series or None
        Pre-computed quality scores from build_record_analysis().

    Returns
    -------
    pd.DataFrame  (copy, never mutates input)
    """
    if venues_df.empty:
        return venues_df.copy()

    clean = venues_df.copy()

    # Drop fully null rows
    clean = clean.dropna(how='all')

    # Validate and filter coordinates
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

    # Attach quality score
    if quality_scores is not None and len(quality_scores) == len(clean):
        clean['quality_score'] = quality_scores.values
    else:
        key_fields = ['venue_id', 'venue_type', 'name', 'latitude', 'longitude', 'district']
        clean['quality_score'] = clean.apply(
            lambda r: sum(1 for f in key_fields
                          if pd.notna(r.get(f)) and str(r.get(f, '')).strip()) / len(key_fields),
            axis=1)

    print(f'  Kept: {len(clean)} records (quality_score mean={clean["quality_score"].mean():.2f})')
    return clean
