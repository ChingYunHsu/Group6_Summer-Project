# ClearPath 数据库架构文档（Codex 方案）— 2026.6.2

## 1. Scope / 范围

ClearPath 使用一个 **MySQL 8.4 application schema**，schema 名为 `clearpath`。当前已验证目标是 MySQL 8.4；MariaDB compatibility 不是本阶段验证目标，因为本地 Docker service 和 initializer SQL 都基于 `mysql:8.4`。

本方案按 **业务对象 / product objects** 建模，而不是 one-table-per-source：

- `venues` and source provenance / 场所与来源追踪
- restroom, healthcare, emergency-service profiles / 厕所、医疗、AED 扩展信息
- pedestrian ramps for wheelchair routing / 轮椅路线基础设施
- live user reports and confirmations / 实时用户报告与确认
- ML busyness outputs / 机器学习拥挤度输出
- Google Maps and Weather context cache / 外部 API 上下文缓存

The MVP keeps sensitive medical profile data on-device via AsyncStorage or SQLite. It is not part of the backend schema.

---

## 2. 需求来源与当前约束

| Source document | 对数据库的约束 |
| --- | --- |
| User Stories / Acceptance Criteria | 支持 Find、Report、Predict、Assist；报告需要确认、过期、用于 ML training signal。 |
| Business Plan | 技术栈为 Flask + MySQL + Google Maps + Gemini/RAG；数据库服务 venues、reports、busyness history。 |
| COMP47360 Project Specification | 至少两个 Manhattan-related datasets；需要 data analytics、ML prediction、Generative AI、EDI features。 |
| Endpoint Shared Contract | 当前共享 API 包含 `/api/v1/venues`、`/api/v1/reports`、`/api/v1/integrations/status` 等核心路径。 |
| Data Source Review | 只使用用户确认的 9 个来源，废弃来源不进入 MVP database path。 |

---

## 3. Retained Data Sources / 保留数据源

Only these nine sources are in scope. Local source files live outside the repository at `/Users/alex/Documents/COMP47360-Research_Practicum/data_source`; `backend/database/clearpath_sources.json` resolves this from the project root.

| Type | Source | Local file / role | Storage role |
| --- | --- | --- | --- |
| Internal | User Reports Database | Internal runtime data | `user_reports`, `report_confirmations` |
| Toilet | NYC Public Restrooms `i7jb-7jku` | `Public_Restrooms_20260526.csv` | `venues`, `venue_source_links`, `restroom_profiles` |
| Toilet | Directory of Toilets in Public Parks `hjae-yuav` | `Directory_Of_Toilets_In_Public_Parks_20260526.csv` | `venues`, `venue_source_links`, `restroom_profiles` |
| Healthcare | OpenStreetMap / Overpass POI | `POI_healtcare.geojson` | `venues`, `venue_source_links`, `healthcare_profiles` |
| Healthcare | NYS Health Facility General Information `vn5v-hh5r` | `Health_Facility_General_Information_20260526.csv` | `venues`, `venue_source_links`, `healthcare_profiles` |
| Healthcare | AED Inventory `2er2-jqsx` | `New_York_City_Automated_External_Defibrillator_(AED)_Inventory_20260526.csv` | `venues`, `venue_source_links`, `emergency_assets` |
| Accessibility | Pedestrian Ramp Locations `ufzp-rrqu` | `Pedestrian_Ramp_Locations_20260526.csv` | `pedestrian_ramps` |
| Traffic | Google Map API | API cache only | `external_context_cache` |
| Weather | Weather / NYC Urban Heat Portal | API/static context cache only | `external_context_cache` |

Excluded for this version: `POI_accessibility.geojson`, HRSA, CityMD, Google Places, MTA outages/stations, taxi data, traffic volume counts, language datasets, and any other source not listed above.

---

## 4. Overall Architecture / 整体架构

```text
┌─────────────────────────────────────────────────────────────┐
│                    ClearPath Frontend                        │
│          React Native Mobile + Responsive Web UI             │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / JSON
┌──────────────────────────▼──────────────────────────────────┐
│                    Flask Backend API                         │
│   /api/v1/venues  /api/v1/reports  /api/v1/integrations      │
└──────┬──────────────┬──────────────┬────────────────────────┘
       │              │              │
       ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌───────────────────────────┐
│ MySQL 8.4 DB │ │ External APIs │ │     ML / Analytics         │
│ clearpath    │ │ Maps/Weather  │ │ busyness score pipeline    │
└──────┬───────┘ └──────┬───────┘ └──────────────┬────────────┘
       │                │                        │
       ▼                ▼                        ▼
┌──────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│ ETL scripts  │ │ external_context_    │ │ busyness_scores      │
│ CSV/GeoJSON  │ │ cache                │ │ model output table   │
└──────────────┘ └─────────────────────┘ └─────────────────────┘

Local device storage remains separate:
AsyncStorage / SQLite for medical_profile, SOS data, show-staff cards.
```

---

## 5. Cloud MySQL Table Layers / 云端 MySQL 表分层

### Layer 1: POI 数据层（静态 / 低频更新）

```text
┌─────────────────────────────────────────────────────────────┐
│                     POI 数据层                               │
│                                                             │
│  venues                                                     │
│  ├─ venue_source_links       来源追踪 / 去重证据              │
│  ├─ restroom_profiles        厕所扩展字段                    │
│  ├─ healthcare_profiles      医疗扩展字段                    │
│  └─ emergency_assets         AED / emergency asset details   │
│                                                             │
│  pedestrian_ramps            轮椅路线基础设施，不作为 venue   │
└─────────────────────────────────────────────────────────────┘
```

### Layer 2: 实时交互层（高频读写）

```text
┌─────────────────────────────────────────────────────────────┐
│                    实时交互层                                │
│                                                             │
│  user_reports             active / resolved / expired        │
│  report_confirmations     still_here / resolved / not_sure   │
│                                                             │
│  Purpose: live warnings, confidence update, ML training log  │
└─────────────────────────────────────────────────────────────┘
```

### Layer 3: ML 输出层（Predict）

```text
┌─────────────────────────────────────────────────────────────┐
│                    ML 输出层                                 │
│                                                             │
│  busyness_scores                                             │
│  ├─ venue_id                                                 │
│  ├─ score / level                                            │
│  ├─ estimated_wait_minutes                                   │
│  ├─ forecast_start_time / forecast_end_time                  │
│  └─ model_version / features_snapshot_id                     │
└─────────────────────────────────────────────────────────────┘
```

### Layer 4: 缓存层（External APIs）

```text
┌─────────────────────────────────────────────────────────────┐
│                    外部 API 缓存层                           │
│                                                             │
│  external_context_cache                                      │
│  ├─ google_route                                             │
│  ├─ distance_matrix                                          │
│  ├─ weather_current                                          │
│  ├─ weather_forecast                                         │
│  └─ urban_heat_static                                        │
└─────────────────────────────────────────────────────────────┘
```

### Layer 5: 本地设备层（不进入 backend schema）

```text
medical_profile | sos_data | show_staff_cards | chat_drafts | consent_flags
```

这些数据属于 privacy-sensitive local data，默认保存在客户端 AsyncStorage / SQLite。

---

## 6. Logical Schema / 逻辑表设计

| Table | Purpose | Main source / owner |
| --- | --- | --- |
| `venues` | Shared displayable POI table for restrooms, healthcare venues, and AED locations. | Data Lead + Backend |
| `venue_source_links` | Maps each unified venue to raw source records, dedupe method, and match confidence. | Data Lead |
| `restroom_profiles` | Restroom-specific fields merged from both toilet datasets. | Data Lead |
| `healthcare_profiles` | Healthcare-specific fields from OSM and NYS Health Facility data. | Data Lead |
| `emergency_assets` | AED-specific details from the NYC AED inventory. | Data Lead |
| `pedestrian_ramps` | Wheelchair routing support points from official ramp data. | Data Lead |
| `user_reports` | Real-time accessibility, toilet, crowd, protest, and entrance reports. | Backend + Data/ML |
| `report_confirmations` | User confirmation/resolution events for live reports. | Backend + Data/ML |
| `busyness_scores` | ML output for current and forecast venue busyness. | ML Lead |
| `external_context_cache` | Server-side cache for Google Maps and Weather/Urban Heat context. | Backend + Data/ML |

---

## 7. ER Relationship / ER 关系图

```text
┌──────────────────┐
│      venues       │
│──────────────────│
│ PK venue_id       │
│ venue_type        │
│ name              │
│ latitude/longitude│
└───────┬──────────┘
        │ 1:N
        ▼
┌──────────────────────┐
│ venue_source_links   │
│──────────────────────│
│ source_name          │
│ source_record_id     │
│ matched_method       │
│ match_confidence     │
└──────────────────────┘

venues 1:1 restroom_profiles
venues 1:1 healthcare_profiles
venues 1:N emergency_assets
venues 1:N user_reports
venues 1:N busyness_scores
venues 1:N external_context_cache

┌──────────────────┐       ┌──────────────────────┐
│   user_reports    │ 1:N   │ report_confirmations │
│──────────────────│──────▶│──────────────────────│
│ PK report_id      │       │ PK confirmation_id    │
│ FK venue_id       │       │ FK report_id          │
│ issue_type        │       │ action                │
│ status/expires_at │       │ created_at            │
└──────────────────┘       └──────────────────────┘

┌──────────────────┐
│ pedestrian_ramps  │
│──────────────────│
│ PK ramp_id        │
│ corner_id         │
│ latitude/longitude│
│ slope/width/etc.  │
└──────────────────┘
```

`pedestrian_ramps` is intentionally independent from `venues`: users do not search ramps as destinations; ramps support accessibility scoring and route checks.

---

## 8. Merge Rules / 数据合并规则

| Source group | Merge target | Rule |
| --- | --- | --- |
| NYC Public Restrooms + Parks Toilets | `venues` + `restroom_profiles` | Merge by name + coordinate proximity where possible; preserve both source records in `venue_source_links`. |
| OSM Healthcare + NYS Health Facility | `venues` + `healthcare_profiles` | OSM gives broad searchable POIs; NYS gives official validation and higher confidence. |
| AED Inventory | `venues` + `emergency_assets` | AED locations are displayable venues with `venue_type = 'emergency_asset'`. |
| Pedestrian Ramps | `pedestrian_ramps` | Do not convert into venues; use for wheelchair route support. |
| Google Maps + Weather | `external_context_cache` | Cache runtime context only; do not treat as primary static facts. |
| User Reports | `user_reports` + `report_confirmations` | Store live warnings, confidence changes, and ML training signal. |

---

## 9. Field Mapping / 字段映射摘要

### 9.1 OSM Healthcare POI → `venues` + `healthcare_profiles`

| Source field | Target | Transformation |
| --- | --- | --- |
| `@id` | `venue_source_links.source_record_id` | Direct, e.g. `node/123`. |
| `name` | `venues.name` | Direct. |
| `healthcare` / `amenity` | `healthcare_profiles.healthcare_category` | Normalize `clinic`, `hospital`, `doctors`, `pharmacy`, `urgent_care`. |
| `geometry.coordinates` | `venues.latitude`, `venues.longitude` | GeoJSON order is `[lng, lat]`. |
| `addr:housenumber` + `addr:street` | `venues.address` | Concatenate when available. |
| `phone`, `website`, `opening_hours` | `venues.phone`, `venues.website`, `venues.opening_hours` | Direct where available. |
| `healthcare:speciality` | `healthcare_profiles.healthcare_speciality` | Direct. |

### 9.2 NYS Health Facility → `venues` + `healthcare_profiles`

| Source field | Target | Transformation |
| --- | --- | --- |
| `Facility ID` | `venue_source_links.source_record_id` / `healthcare_profiles.facility_external_id` | Direct. |
| `Facility Name` | `venues.name` | Direct. |
| `Facility Latitude`, `Facility Longitude` | `venues.latitude`, `venues.longitude` | Skip or log records without coordinates for map MVP. |
| `Facility Address 1/2` | `venues.address` | Concatenate. |
| `Facility Phone Number`, `Facility Website` | `venues.phone`, `venues.website` | Direct. |
| `Facility County` | `venues.borough` | `New York` maps to Manhattan. |
| `Short Description`, `Description` | `healthcare_profiles.facility_type` | Direct / normalized. |
| `Operator Name`, `Ownership Type` | `healthcare_profiles.operator_name`, `ownership_type` | Direct. |

### 9.3 AED Inventory → `venues` + `emergency_assets`

| Source field | Target | Transformation |
| --- | --- | --- |
| `Entity_Name` | `venues.name` | Use entity name, optionally suffix AED in UI only. |
| `Address`, `Borough`, `Latitude`, `Longitude` | `venues.address`, `borough`, `latitude`, `longitude` | Direct. |
| `Entity_Name` + `Address` | `venue_source_links.source_record_id` | Hash if no stable ID exists. |
| `Floor`, `Location Type` | `emergency_assets.floor`, `location_type` | Direct. |
| `AED_NumAeds`, `AED_NumPersonTrained` | `emergency_assets.aed_count`, `trained_people_count` | Parse integer. |
| `Last Updated` | `emergency_assets.last_updated` | Parse date. |

### 9.4 Public Restrooms + Parks Toilets → `venues` + `restroom_profiles`

| Source field | Target | Transformation |
| --- | --- | --- |
| `Facility Name` / `Name` | `venues.name` | Direct. |
| `Latitude`, `Longitude` | `venues.latitude`, `venues.longitude` | Direct for NYC Public Restrooms. |
| `Location`, `Borough` | `venues.address`, `venues.borough` | Direct where available. |
| `Restroom Type`, `Operator`, `Status` | `restroom_profiles.restroom_type`, `operator`, `status` | Direct / normalized. |
| `Accessibility`, `Handicap Accessible` | `restroom_profiles.ada_accessible`, `handicap_accessible` | Map yes/accessibility values to boolean. |
| `Open`, `Open Year-Round` | `restroom_profiles.open_seasonal`, `open_year_round` | Normalize boolean. |
| `Changing Stations` | `restroom_profiles.changing_station` | Normalize boolean. |
| `Comments`, `Additional Notes` | `restroom_profiles.additional_notes` | Preserve text. |

Parks Toilets has no reliable coordinates in the local file. MVP ETL should either geocode later or import only records that can be matched to an existing restroom venue by name/location.

### 9.5 Pedestrian Ramps → `pedestrian_ramps`

| Source field | Target | Transformation |
| --- | --- | --- |
| `RampID` | `pedestrian_ramps.ramp_id` | Direct. |
| `CornerID` | `corner_id` | Direct. |
| `the_geom` | `latitude`, `longitude` | Parse `POINT (lng lat)`. |
| `Borough` | `borough` | Map numeric borough codes where needed. |
| `Ramp_OnStreet`, `StName1`, `StName2` | `on_street`, `cross_street_1`, `cross_street_2` | Direct. |
| `RAMP_WIDTH`, `RAMP_RUNNING_SLOPE_TOTAL` | `ramp_width`, `ramp_slope` | Parse decimal. |
| `DWS_CONDITIONS`, `PONDING`, `OBSTACLES_*` | `dws_condition`, `ponding`, `obstacles_ramp`, `obstacles_landing` | Direct / normalized text. |

---

## 10. Data Quality Problems / 数据质量问题

| Problem | Source | Planned solution |
| --- | --- | --- |
| Parks Toilets lacks latitude/longitude | Directory of Toilets in Public Parks | Match against Public Restrooms where possible; otherwise defer geocoding. |
| Some NYS Health records lack coordinates | NYS Health Facility | Skip for map MVP, log row count, keep as future enrichment candidate. |
| OSM tags are inconsistent | OSM Healthcare | Normalize `healthcare`, `amenity`, and `healthcare:speciality`; lower source confidence than official data. |
| AED has no stable single ID | AED Inventory | Generate hash from `Entity_Name + Address`, preserve raw source text. |
| Pedestrian ramps dataset is large | Pedestrian Ramp Locations | Start with Manhattan subset or chunked import; keep indexes on latitude/longitude and borough. |
| Duplicate POIs across sources | Toilets / Healthcare | Use `venue_source_links` and match confidence instead of overwriting source rows. |
| API contract includes language fields | Endpoint Shared Contract | Current 9-source MVP has no reliable language source; return empty/default values or revise contract later. |

---

## 11. Index Strategy / 索引策略

| Table | Index | Purpose |
| --- | --- | --- |
| `venues` | `(venue_type)` | Type filtering: restroom / healthcare / emergency_asset. |
| `venues` | `(latitude, longitude)` | Manhattan bounding-box and nearby map queries. |
| `venues` | `(borough)` | Borough filter and dataset sanity checks. |
| `venue_source_links` | `(source_name, source_record_id)` unique | Import idempotency and dedupe. |
| `venue_source_links` | `(venue_id)` | Explain source provenance on venue detail page. |
| `user_reports` | `(venue_id, status)` | Active warnings for venue cards/details. |
| `user_reports` | `(status, expires_at)` | Expiry cleanup and active report queries. |
| `pedestrian_ramps` | `(latitude, longitude)` | Nearby ramp lookup. |
| `busyness_scores` | `(venue_id, forecast_start_time, forecast_end_time)` | Current and forecast busyness lookup. |
| `external_context_cache` | `(context_type, request_key)` unique | Cache hit for route/weather requests. |
| `external_context_cache` | `(context_type, expires_at)` | Cache expiry cleanup. |

---

## 12. API Mapping / API 与数据库映射

| API | Database behavior |
| --- | --- |
| `GET /api/v1/venues` | Reads `venues` plus relevant profile table, latest `busyness_scores`, and active `user_reports`. |
| `GET /api/v1/venues/{venue_id}` | Reads full venue profile, source links, reports, and busyness forecast. |
| `POST /api/v1/reports` | Writes `user_reports`; default expiry should be two hours unless backend changes policy. |
| `POST /api/v1/reports/{report_id}/confirmations` | Writes `report_confirmations`; backend updates report status or confidence. |
| `GET /api/v1/integrations/status` | Checks database, Google Maps, Weather, and ML output availability. |

### API Compatibility Notes

- `user_reports.status = 'expired'` is an internal database lifecycle state. Public `Report.status` responses should expose only contract-supported states such as `active` and `resolved`; expired reports should normally be filtered out or mapped by the API layer.
- `Venue.active_warning` is derived from active `user_reports` near or attached to the venue.
- `Venue.accessible_status` and `Venue.accessibility_features` are derived from restroom accessibility fields, nearby `pedestrian_ramps`, and active accessibility reports.
- `Venue.language_tags`, `primary_language`, and `secondary_language` do not have a reliable source in the current nine-source MVP scope. The API should return empty/default values for MVP or the shared endpoint contract should be revised later.

---

## 13. ETL Flow / 数据导入流程

```text
CSV / GeoJSON source files
        │
        ▼
backend/database/clearpath_sources.json
        │
        ▼
ETL loaders
  - read source
  - normalize fields
  - validate coordinates
  - generate source_record_id / hash
  - merge into venues
  - write source provenance
        │
        ▼
MySQL 8.4 clearpath schema
```

Recommended ETL module direction:

```text
backend/database/
├── clearpath_sources.json
├── validate_sources.py
└── etl/
    ├── load_restrooms.py
    ├── load_healthcare.py
    ├── load_emergency_assets.py
    ├── load_pedestrian_ramps.py
    └── run_all.py
```

Sprint 1 can start with a minimal import order:

1. Public Restrooms → `venues` + `restroom_profiles`
2. OSM Healthcare → `venues` + `healthcare_profiles`
3. AED Inventory → `venues` + `emergency_assets`
4. Pedestrian Ramps Manhattan subset → `pedestrian_ramps`

---

## 14. Nonfunctional Requirements / 非功能需求

| Requirement | Target / rationale |
| --- | --- |
| 查询延迟 | Map POI queries should stay under 200ms for demo-sized Manhattan subsets. |
| 空间查询 | Support latitude/longitude bounding-box query for Manhattan map viewport. |
| 并发 | Demo target: 50+ concurrent users; MySQL indexes avoid full scans on core map/report paths. |
| 数据一致性 | `venue_source_links` unique source record keys support idempotent re-import. |
| 字符集 | `utf8mb4` for multilingual names and notes. |
| 过期清理 | `user_reports.expires_at` and `external_context_cache.expires_at` support cleanup. |
| 可维护性 | Source manifest records included/excluded datasets so scope changes are explicit. |
| 隐私 | Medical profile and SOS data stay local by default. |

---

## 15. Acceptance Criteria / 验收标准

| # | Standard | Verification |
| --- | --- | --- |
| AC1 | Docker initializer defines exactly the 10 Codex schema tables. | `python3 -m unittest tests/test_database_plan.py` |
| AC2 | The nine approved data sources are the only manifest sources. | `python3 backend/database/validate_sources.py` |
| AC3 | Excluded sources are not referenced by the MVP manifest. | Unit test + manifest review |
| AC4 | Docker Compose config is valid for MySQL 8.4. | `docker compose config` |
| AC5 | Docker schema and Codex schema copy remain identical. | `cmp docker/mysql/init/001_clearpath_schema.sql ml_training/plan/6.2_codex/001_clearpath_schema.sql` |
| AC6 | Future ETL imports can run idempotently. | Re-import should not duplicate `venue_source_links.source_name + source_record_id`. |
| AC7 | API layer can distinguish public states from internal states. | Expired reports filtered/mapped before API response. |

---

## 16. Implementation Files / 实现文件

- Schema initializer: `docker/mysql/init/001_clearpath_schema.sql`
- Codex schema copy: `ml_training/plan/6.2_codex/001_clearpath_schema.sql`
- Docker service: `docker-compose.yml`
- Source manifest: `backend/database/clearpath_sources.json`
- Source validator: `backend/database/validate_sources.py`
- Verification tests: `tests/test_database_plan.py`
- Process document: `ml_training/plan/6.2_codex/database_implementation_process.md`

`ml_training/plan/6.2` and `ml_training/plan/6.2_CC` are separate Claude/CC work areas. They are useful references for structure and presentation, but they are not the source of truth for the Codex Docker initializer.
