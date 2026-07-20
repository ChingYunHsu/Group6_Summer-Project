import csv
import json
from dataclasses import dataclass

from .config import DATA_ROOT, MANIFEST_PATH
from .validation import is_manhattan

# bundle of all sources together, for ease of passing around
@dataclass
class SourceBundle:
    restrooms: list
    parks: list
    osm_features: list
    accessibility_features: list
    nys: list
    aed: list
    ramps: list

# helper function to load manifest json file and return dict
def load_manifest(path=MANIFEST_PATH):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)

# helper function to load single csv file and return list of dicts
def _load_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

# helper function to load all sources together into a SourceBundle
def load_sources(data_root=DATA_ROOT):
    # load csv by path and json by path, return a SourceBundle
    restrooms = _load_csv(data_root / "Public_Restrooms_20260526.csv")
    parks = _load_csv(
        data_root / "Directory_Of_Toilets_In_Public_Parks_20260526.csv"
    )
    # load geojson by path, extract features list, return empty list if no features
    with open(data_root / "POI_healtcare.geojson", encoding="utf-8") as handle:
        osm_features = json.load(handle).get("features", [])
    with open(data_root / "POI_accessibility.geojson", encoding="utf-8") as handle:
        accessibility_features = json.load(handle).get("features", [])

    nys = _load_csv(data_root / "Health_Facility_General_Information_20260526.csv")
    aed = _load_csv(
        data_root
        / "New_York_City_Automated_External_Defibrillator_(AED)_Inventory_20260526.csv"
    )
    ramps = _load_csv(data_root / "Pedestrian_Ramp_Locations_20260526.csv")
    return SourceBundle(
        restrooms, parks, osm_features, accessibility_features, nys, aed, ramps
    )

# helper function to count records in each source, return dict of bundle counts by source name
def source_counts(bundle):
    return {
        "NYC Public Restrooms": len(bundle.restrooms),
        "Parks Toilets": len(bundle.parks),
        "OSM Healthcare": len(bundle.osm_features),
        "OSM Accessibility": len(bundle.accessibility_features),
        "NYS Health Facility": len(bundle.nys),
        "AED Inventory": len(bundle.aed),
        "Pedestrian Ramps": len(bundle.ramps),
    }

# helper function to count records in each source within Manhattan scope, return dict of bundle counts by source name
def manhattan_counts(bundle):
    def restroom_in_scope(row):
        try:
            return is_manhattan(row.get("Latitude", 0), row.get("Longitude", 0))
        except (ValueError, TypeError):
            return False

    return {
        "NYC Public Restrooms": sum(map(restroom_in_scope, bundle.restrooms)),
        "Parks Toilets": sum(
            (row.get("Borough") or "").strip().lower() == "manhattan"
            for row in bundle.parks
        ),
        "OSM Healthcare": sum(
            len(feature.get("geometry", {}).get("coordinates", [])) >= 2
            and is_manhattan(
                feature["geometry"]["coordinates"][1],
                feature["geometry"]["coordinates"][0],
            )
            for feature in bundle.osm_features
        ),
        "NYS Health Facility": sum(
            (row.get("Facility County") or "").strip() == "New York"
            for row in bundle.nys
        ),
        "AED Inventory": sum(
            (row.get("Borough") or "").strip().lower() == "manhattan"
            for row in bundle.aed
        ),
        "Pedestrian Ramps": sum(
            (row.get("Borough") or "").strip() == "1" for row in bundle.ramps
        ),
    }
