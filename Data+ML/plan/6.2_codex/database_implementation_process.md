# ClearPath Database Implementation Process
# ClearPath 数据库实施流程

## 1. Input Scope Confirmed
## 1. 已确认的输入范围

This implementation follows the revised ClearPath database scope confirmed on 2026-06-02.
本实施遵循 2026-06-02 确认的修订版 ClearPath 数据库范围。

Only these nine sources are included:
仅包含以下九个数据源：

| Type | Source | Implementation role |
| --- | --- | --- |
| Internal | User Reports Database | Runtime tables for reports and confirmations |
| Toilet | NYC Public Restrooms `i7jb-7jku` | Venue + restroom profile source |
| Toilet | Directory of Toilets in Public Parks `hjae-yuav` | Venue + restroom profile supplement |
| Healthcare | OpenStreetMap / Overpass POI | Broad healthcare venue source |
| Healthcare | NYS Health Facility General Information `vn5v-hh5r` | Official healthcare validation source |
| Healthcare | AED Inventory `2er2-jqsx` | Emergency asset venue source |
| Accessibility | Pedestrian Ramp Locations `ufzp-rrqu` | Wheelchair routing infrastructure |
| Traffic | Google Map API | Runtime route/context cache |
| Weather | Weather / NYC Urban Heat Portal | Runtime weather/heat context cache |

Excluded sources are intentionally not part of the MVP database path: `POI_accessibility.geojson`, HRSA, CityMD, Google Places, MTA, taxi, traffic volume, LASS, LEP, and other unlisted sources.
以下数据源已明确排除在 MVP 数据库路径之外：`POI_accessibility.geojson`、HRSA、CityMD、Google Places、MTA、出租车、交通流量、LASS、LEP 及其他未列出的数据源。

## 2. Design Decision
## 2. 设计决策

The database is implemented as one MySQL 8.4 schema named `clearpath`.
数据库采用单个 MySQL 8.4 schema，命名为 `clearpath`。

The design avoids one-table-per-source storage. Similar source types are merged into business objects:
设计上避免了"一个数据源一张表"的存储方式。相似的数据源类型被合并到业务对象中：

- restrooms merge into `venues` + `restroom_profiles`
- 公共洗手间数据合并到 `venues` + `restroom_profiles`
- healthcare POIs and NYS facilities merge into `venues` + `healthcare_profiles`
- 医疗 POI 和 NYS 设施数据合并到 `venues` + `healthcare_profiles`
- AED records are displayable `venues` with details in `emergency_assets`
- AED 记录作为可展示的 `venues`，详细信息存储在 `emergency_assets`
- pedestrian ramps stay separate in `pedestrian_ramps` because they support routing rather than venue search
- 人行道坡道保留在独立的 `pedestrian_ramps` 表中，因为它们用于路线规划而非场所搜索
- Google Maps and Weather are cached in `external_context_cache`
- Google Maps 和天气数据缓存在 `external_context_cache` 中
- live user reports are stored in `user_reports` and `report_confirmations`
- 实时用户报告存储在 `user_reports` 和 `report_confirmations` 中
- ML output is stored in `busyness_scores`
- 机器学习输出存储在 `busyness_scores` 中

This keeps the schema compact while preserving source traceability through `venue_source_links`.
这样既保持了 schema 的精简，又通过 `venue_source_links` 表保留了数据源的可追溯性。

## 3. Files Implemented
## 3. 已实施的文件

| File | Purpose |
| --- | --- |
| 文件 | 用途 |
| `docker-compose.yml` | Adds local MySQL 8.4 service and schema initializer mount |
| `docker/mysql/init/001_clearpath_schema.sql` | Creates the 10-table ClearPath schema |
| `ml_training/plan/6.2_codex/001_clearpath_schema.sql` | Codex-owned copy of the Docker initializer schema |
| `backend/database/clearpath_sources.json` | Source manifest for the nine approved sources |
| `backend/database/validate_sources.py` | Validates retained local files and checks excluded files are unused |
| `backend/database/README.md` | Explains database scope, tables, and local setup |
| `ml_training/plan/database.md` | Updated architecture note aligned to the nine-source scope |
| `tests/test_database_plan.py` | Unit tests for manifest scope, source availability, and schema table set |

## 4. Schema Tables Created
## 4. 已创建的 Schema 表

The SQL initializer creates exactly these core tables:
SQL 初始化脚本精确创建以下核心表：

1. `venues`
2. `venue_source_links`
3. `restroom_profiles`
4. `healthcare_profiles`
5. `emergency_assets`
6. `pedestrian_ramps`
7. `user_reports`
8. `report_confirmations`
9. `busyness_scores`
10. `external_context_cache`

The Docker initializer and the Codex copy under `ml_training/plan/6.2_codex` must remain identical. The `ml_training/plan/6.2` and `ml_training/plan/6.2_CC` directories are separate Claude/CC work areas and are not the source of truth for the Docker initializer.
Docker 初始化文件和 `ml_training/plan/6.2_codex` 下的 Codex 副本必须保持一致。`ml_training/plan/6.2` 和 `ml_training/plan/6.2_CC` 目录是独立的 Claude/CC 工作区域，不是 Docker 初始化文件的权威来源。

Key relationships:
关键关系：

- profile tables reference `venues`
- profile 表引用 `venues` 表
- source links reference `venues`
- source links 引用 `venues` 表
- reports optionally reference `venues`
- reports 可选引用 `venues` 表
- confirmations reference `user_reports`
- confirmations 引用 `user_reports` 表
- busyness scores reference `venues`
- busyness scores 引用 `venues` 表
- external context cache optionally references `venues`
- external context cache 可选引用 `venues` 表

## 5. Validation Results
## 5. 验证结果

Commands run from the repository root:
在项目根目录执行以下命令：

```bash
python3 backend/database/validate_sources.py
python3 -m unittest tests/test_database_plan.py
docker compose config
```

Results:
验证结果：

- source manifest includes 9 approved sources
- 数据源清单包含 9 个已批准的数据源
- 6 retained local source files exist
- 6 个保留的本地数据源文件存在
- excluded local files are not referenced
- 已排除的本地文件未被引用
- schema defines the expected 10 tables
- schema 定义了预期的 10 张表
- Docker Compose configuration is valid
- Docker Compose 配置有效

Local retained file counts found by the validator:
验证器发现的本地保留文件行数：

| File | Count |
| --- | ---: |
| `Public_Restrooms_20260526.csv` | 1,066 rows |
| `Directory_Of_Toilets_In_Public_Parks_20260526.csv` | 616 rows |
| `POI_healtcare.geojson` | 966 features |
| `Health_Facility_General_Information_20260526.csv` | 5,963 rows |
| `New_York_City_Automated_External_Defibrillator_(AED)_Inventory_20260526.csv` | 7,373 rows |
| `Pedestrian_Ramp_Locations_20260526.csv` | 217,679 rows |

## 6. Next Implementation Step
## 6. 下一步实施计划

The next backend step is to add ETL loaders that read the six local retained files and populate the schema:
后端下一步是添加 ETL 加载器，读取六个本地保留文件并填充 schema：

- restroom loader with dedupe into `venues` and `restroom_profiles`
- 洗手间加载器：去重后写入 `venues` 和 `restroom_profiles`
- healthcare loader with OSM/NYS merge logic into `venues` and `healthcare_profiles`
- 医疗加载器：合并 OSM/NYS 数据后写入 `venues` 和 `healthcare_profiles`
- AED loader into `venues` and `emergency_assets`
- AED 加载器：写入 `venues` 和 `emergency_assets`
- ramp loader into `pedestrian_ramps`
- 坡道加载器：写入 `pedestrian_ramps`

After ETL, Flask endpoints can be wired to the schema:
ETL 完成后，可以将 Flask 端点接入 schema：

- `GET /api/v1/venues`
- `GET /api/v1/venues/{venue_id}`
- `POST /api/v1/reports`
- `POST /api/v1/reports/{report_id}/confirmations`
- `GET /api/v1/integrations/status`
