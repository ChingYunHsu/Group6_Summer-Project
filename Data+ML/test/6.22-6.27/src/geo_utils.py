"""Shared geographic / spatial utilities for venue matching.

Provides:
- EARTH_RADIUS_M constant
- haversine_distance_m() for single-pair distance
- haversine_distances_m() for vectorized distance from one point to many

All distances are in meters.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

EARTH_RADIUS_M = 6_371_008.8


def haversine_distance_m(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> float:
    """Haversine distance in meters between two coordinate pairs."""
    lat1_rad = np.radians(lat1)
    lng1_rad = np.radians(lng1)
    lat2_rad = np.radians(lat2)
    lng2_rad = np.radians(lng2)
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlng / 2) ** 2
    )
    return float(EARTH_RADIUS_M * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))


def haversine_distances_m(
    venues: pd.DataFrame,
    lat: float,
    lng: float,
) -> np.ndarray:
    """Vectorized haversine: distance from every row in *venues* to (lat, lng).

    Returns a numpy array of distances in meters, same length as venues.
    """
    lat1 = np.radians(venues["latitude"].values)
    lng1 = np.radians(venues["longitude"].values)
    lat2 = np.radians(lat)
    lng2 = np.radians(lng)

    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng / 2) ** 2
    return EARTH_RADIUS_M * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
