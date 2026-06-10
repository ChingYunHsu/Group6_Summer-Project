# Data+ML Module - ClearPath Database

## Overview

The ClearPath database module is responsible for managing data storage for the Waze-style accessibility app, including data import, schema management, and API integration.

## Database Architecture

### Tech Stack

| Component | Technology |
|-----------|------------|
| Database | MySQL 8.4 |
| Container | Docker |
| ETL | Python (pymysql) |
| Schema Versioning | SQL files |

### 10-Table Schema

| Table | Description |
|-------|-------------|
| `venues` | Main table, storing all venue information |
| `venue_source_links` | Data source tracking |
| `restroom_profiles` | Restroom details |
| `healthcare_profiles` | Healthcare facility details |
| `emergency_assets` | Emergency equipment (AED) |
| `pedestrian_ramps` | Pedestrian ramps |
| `user_reports` | User reports |
| `report_confirmations` | Report confirmations |
| `busyness_scores` | Busyness scores |
| `external_context_cache` | External API cache |

### Extended Tables (API Alignment)

| Table | Description |
|-------|-------------|
| `venue_accessibility` | Accessibility features details |
| `venue_language` | Language support |
| `venue_warnings` | Venue warnings |

## Quick Start

### 1. Start MySQL

```bash
# From project root
docker compose up -d

# Verify
docker ps | grep mysql
```

### 2. Connect to Database

```bash
# Command line
mysql -h 127.0.0.1 -P 3306 -u clearpath_app -pclearpath_app clearpath

# Or via Docker
docker exec -it clearpath-mysql mysql -u clearpath_app -pclearpath_app clearpath
```

### 3. View Data (GUI Options)

| Tool | Connection |
|------|------------|
| MySQL Workbench | Host: `127.0.0.1`, Port: `3306` |
| DBeaver | Host: `127.0.0.1`, Port: `3306` |
| phpMyAdmin | http://localhost:8080 |

## ETL Pipeline

### Data Sources

| Source | File | Records (Manhattan) |
|--------|------|---------------------|
| NYC Public Restrooms | `Public_Restrooms_20260526.csv` | 349 |
| Parks Toilets | `Directory_Of_Toilets_In_Public_Parks_20260526.csv` | 127 |
| OSM Healthcare | `POI_healtcare.geojson` | 900 |
| NYS Health Facility | `Health_Facility_General_Information_20260526.csv` | 431 |
| AED Inventory | `New_York_City_Automated_External_Defibrillator_(AED)_Inventory_20260526.csv` | 1,781 |
| Pedestrian Ramps | `Pedestrian_Ramp_Locations_20260526.csv` | 23,625 |

### ETL Functions

| Function | Source | Dedup Strategy |
|----------|--------|----------------|
| `etl_restrooms` | NYC Restrooms + Parks Toilets | Within-source: same name |
| `etl_healthcare` | OSM + NYS Health | Cross-source: GPS <30m |
| `etl_aed` | AED Inventory | Within-source: entity+address |
| `etl_ramps` | Pedestrian Ramps | Within-source: ramp_id |

### Run ETL

```bash
# Open Jupyter Notebook
jupyter notebook test/6.2_DB/database_build.ipynb

# Execute cells in order:
# Cell 1: Load tools
# Cell 12: MySQL connection + utility functions
# Cell 14: Schema rebuild
# Cell 16: etl_restrooms
# Cell 22: etl_healthcare (merged OSM+NYS)
# Cell 19: etl_aed
# Cell 24: etl_ramps
# Cell 27: Verification
```

## Confidence Levels

| Source | Confidence | Reason |
|--------|------------|--------|
| NYS Health | 0.9 | Official government data |
| AED Inventory | 0.8 | Verified inventory |
| NYC Restrooms | 0.6 | City data, may be outdated |
| OSM Healthcare | 0.5 | Community-sourced |
| Parks Toilets | 0.3 | No coordinates available |

## Schema Management

### Location

- **Development**: `test/6.2_DB/001_clearpath_schema.sql`
- **Production**: `docker/mysql/init/001_clearpath_schema.sql`

### Sync Schema

After ETL modifications, sync schema file:

```python
# In notebook cell-43
# Auto-syncs database structure to 001_clearpath_schema.sql
```

### Fix Plan Alignment

Schema aligns with `fix_plan.md` requirements:
-  venue_type enum: 8 values
-  venues: 21 columns
-  user_reports: 12 columns
-  3 new tables (venue_accessibility, venue_language, venue_warnings)

## Configuration

### MySQL Credentials

| Key | Value |
|-----|-------|
| Host | `127.0.0.1` |
| Port | `3306` |
| Database | `clearpath` |
| User | `clearpath_app` |
| Password | `clearpath_app` |
| Root Password | `clearpath_root` |

### Manhattan BBOX

```python
MANHATTAN_BBOX = {
    'lat_min': 40.700,
    'lat_max': 40.880,
    'lng_min': -74.020,
    'lng_max': -73.9
}
```

## File Structure

```
Data+ML/
├── README.md                    # This file
├── test/
│   └── 6.2_DB/
│       ├── database_build.ipynb # Main ETL notebook
│       ├── 001_clearpath_schema.sql
│       ├── clearpath_sources.json
│       ├── fix_plan.md
│       ├── api_schema_gap_analysis_en.md
│       └── [CN]fix_plan.md
└── ml_training/                 # Future ML models
```

## Troubleshooting

### Connection Failed

```bash
# Check if MySQL is running
docker ps | grep mysql

# Restart MySQL
docker compose restart mysql

# Check logs
docker logs clearpath-mysql
```

### Schema Mismatch

```bash
# Rebuild schema from file
docker exec -it clearpath-mysql mysql -u root -pclearpath_root clearpath < docker/mysql/init/001_clearpath_schema.sql
```

### Data Too Large

```bash
# Check table sizes
docker exec -it clearpath-mysql mysql -u clearpath_app -pclearpath_app clearpath -e "
SELECT table_name, table_rows 
FROM information_schema.tables 
WHERE table_schema = 'clearpath'
ORDER BY table_rows DESC;
"
```

## Related Documents

- [Fix Plan](test/6.2_DB/fix_plan.md) - Schema alignment plan
- [API Gap Analysis](test/6.2_DB/api_schema_gap_analysis_en.md) - API requirements
- [Data Sources](test/6.2_DB/clearpath_sources.json) - Data source manifest
