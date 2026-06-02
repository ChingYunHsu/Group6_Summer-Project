# ClearPath Sprint 1 Codex TODO

## P0 — 本周必须完成

### 1. MySQL 建表验证

- [ ] 启动 MySQL：
  - `docker compose up -d mysql`
- [ ] 确认容器健康：
  - `docker compose ps`
- [ ] 连接 MySQL 并检查 schema：
  - `SHOW DATABASES;`
  - `USE clearpath;`
  - `SHOW TABLES;`
- [ ] 验证 10 张表真实创建：
  - `venues`
  - `venue_source_links`
  - `restroom_profiles`
  - `healthcare_profiles`
  - `emergency_assets`
  - `pedestrian_ramps`
  - `user_reports`
  - `report_confirmations`
  - `busyness_scores`
  - `external_context_cache`
- [ ] 将 `SHOW TABLES` / `DESCRIBE` 结果记录到过程文档。

### 2. ETL 基础框架

- [ ] 创建 ETL 目录，例如 `backend/database/etl/`。
- [ ] 新增通用配置：
  - 数据源根目录
  - MySQL 连接配置
  - Manhattan bounding box 常量
- [ ] 新增通用工具：
  - CSV reader
  - GeoJSON reader
  - `POINT (lng lat)` parser
  - source hash generator
  - boolean normalization
  - safe decimal parser
- [ ] 新增 `run_all.py`，支持按顺序运行 loaders。

### 3. Public Restrooms loader

- [ ] 读取 `Public_Restrooms_20260526.csv`。
- [ ] 写入 `venues`：
  - `venue_type = restroom`
  - name / latitude / longitude / address / website
- [ ] 写入 `restroom_profiles`：
  - restroom type
  - status
  - operator
  - ADA accessibility
  - changing station
  - notes
- [ ] 写入 `venue_source_links`。
- [ ] 支持重复运行不重复插入。

### 4. OSM Healthcare loader

- [ ] 读取 `POI_healtcare.geojson`。
- [ ] 解析 GeoJSON coordinates，注意顺序是 `[lng, lat]`。
- [ ] 过滤明显不在 Manhattan / NYC 范围内的异常点。
- [ ] 写入 `venues`：
  - `venue_type = healthcare`
  - name / latitude / longitude / address / phone / website / opening hours
- [ ] 写入 `healthcare_profiles`：
  - healthcare category
  - speciality
  - facility type
- [ ] 写入 `venue_source_links`。

### 5. AED loader

- [ ] 读取 `New_York_City_Automated_External_Defibrillator_(AED)_Inventory_20260526.csv`。
- [ ] 用 `Entity_Name + Address` 生成 stable source hash。
- [ ] 写入 `venues`：
  - `venue_type = emergency_asset`
  - name / address / borough / latitude / longitude
- [ ] 写入 `emergency_assets`：
  - floor
  - location type
  - AED count
  - trained people count
  - last updated
- [ ] 写入 `venue_source_links`。

## P1 — Sprint 1 强支持任务

### 6. NYS Health Facility loader

- [ ] 读取 `Health_Facility_General_Information_20260526.csv`。
- [ ] 过滤缺少坐标的记录，记录 skipped count。
- [ ] 将 `Facility County = New York` 映射为 Manhattan。
- [ ] 写入 `venues` 和 `healthcare_profiles`。
- [ ] 与 OSM healthcare 做初步匹配规则：
  - exact / near name
  - coordinate proximity
  - address similarity
- [ ] 将匹配结果写入 `venue_source_links`。

### 7. Parks Toilets loader

- [ ] 读取 `Directory_Of_Toilets_In_Public_Parks_20260526.csv`。
- [ ] 记录无坐标问题。
- [ ] 优先按 name / borough / location 匹配已有 restroom venues。
- [ ] 暂不强制 geocoding；无法匹配的记录进入 skipped / review log。
- [ ] 将可匹配记录补充到 `restroom_profiles` 和 `venue_source_links`。

### 8. Pedestrian Ramps loader

- [ ] 读取 `Pedestrian_Ramp_Locations_20260526.csv`。
- [ ] 先做 Manhattan subset 或 chunked import，避免一次处理 20 万+ 行导致开发环境过慢。
- [ ] 解析 `the_geom` 为 latitude / longitude。
- [ ] 写入 `pedestrian_ramps`。
- [ ] 输出导入 count、skipped count、异常 geometry count。

### 9. 数据质量报告

- [ ] 输出每个来源的 row count / imported count / skipped count。
- [ ] 记录主要问题：
  - Parks Toilets 无坐标
  - NYS Health 缺坐标
  - OSM tag 不稳定
  - AED 无稳定 ID
  - Pedestrian Ramps 数据量大
- [ ] 形成 Presentation 3 可用的数据质量 bullet points。

### 10. Baseline `busyness_scores`

- [ ] 设计 MVP baseline score，不承诺最终 ML 模型。
- [ ] 初始输入可以包括：
  - venue type
  - active report count
  - hour of day
  - weather cache placeholder
- [ ] 写入 `busyness_scores` 示例数据，供前端 pin color 测试。
- [ ] 记录后续 scikit-learn 模型计划。

## P2 — 后续增强任务

### 11. External context cache

- [ ] 设计 Google Maps cache request key。
- [ ] 设计 Weather / Urban Heat cache request key。
- [ ] 明确 cache expiry：
  - route / distance matrix: 30 minutes or request dependent
  - weather current: 1 hour
  - urban heat static: long-lived
- [ ] 暂不在 Sprint 1 强制接入真实 API。

### 12. API contract 对齐

- [ ] 与 Backend Lead 确认 `/api/v1/venues` 返回字段。
- [ ] 明确 database direct fields vs API derived fields。
- [ ] 处理 fallback：
  - `language_tags = []`
  - `primary_language = null`
  - `secondary_language = null`
  - `active_warning` 从 `user_reports` 推导
  - `accessible_status` 从 restroom / ramps / reports 推导

### 13. Presentation 3 准备

- [ ] 准备 Data Analytics 讲稿结构：
  - data sources
  - collection method
  - cleaning / merging
  - quality problems
  - early insights
  - ML plan
- [ ] 准备数据源数量表。
- [ ] 准备数据质量问题表。
- [ ] 准备 ML roadmap：
  - baseline score
  - feature engineering
  - model comparison later

## 持续验证命令

每次 schema / manifest / source scope 改动后运行：

```bash
python3 -m unittest tests/test_database_plan.py
python3 backend/database/validate_sources.py
docker compose config
cmp docker/mysql/init/001_clearpath_schema.sql ml_training/plan/6.2_codex/001_clearpath_schema.sql
```

## 不要做

- [ ] 不要修改 `ml_training/plan/6.2_CC/*`。
- [ ] 不要把 CC schema 里的旧表直接加回 Docker schema：
  - `toilets`
  - `reports`
  - `busyness_predictions`
  - `users`
  - `saved_venues`
  - `traffic_cache`
  - `weather_cache`
  - `accessibility_infrastructure`
- [ ] 不要重新引入废弃数据源：
  - `POI_accessibility.geojson`
  - HRSA
  - CityMD
  - Google Places
  - MTA
  - Taxi
  - Traffic Volume
  - Language datasets
