# Database Build Notebook 状态

## 文件位置
- **Notebook**: `Data+ML/test/6.2-6.5_DB/database_build.ipynb`
- **Schema**: `Data+ML/test/6.2-6.5_DB/001_clearpath_schema.sql`
- **MANIFEST**: `Data+ML/test/6.2-6.5_DB/clearpath_sources.json`

## 关键修复 (2026-06-06)

### 1. 路径修正
- `SCHEMA_PATH` → `6.2-6.5_DB/001_clearpath_schema.sql`
- `MANIFEST_PATH` → `6.2-6.5_DB/clearpath_sources.json`

### 2. Schema 验证
- Cell 5 `expected_tables` = 13 个表

### 3. District Zoning（Pipeline 要求）
- `gps_to_district(lat, lng)` 函数：uptown/midtown_east/midtown_west/downtown
- MIGRATIONS 新增 2 条：`venues.district` + `pedestrian_ramps.district`
- ETL 函数更新：Cell 16/18/20/22 写入 district
- `migration_is_applied` 支持 `column`/`table`/`index` 三种 kind

### 4. emergency_assets 唯一约束
- `UNIQUE KEY (venue_id, floor, location_type)` 防止重复写入

### 5. forecast_4h/8h 已从数据库删除
- Cell 46 同步 schema 文件后自动反映

### 6. Markdown Cell 引用修正
| 函数 | 旧引用 | 新引用 |
|------|--------|--------|
| `etl_healthcare()` | [22] | [20] |
| `etl_aed()` | [19] | [18] |
| `etl_ramps()` | [24] | [22] |
| `etl_weather()` | [46] | [40] |
| `etl_venue_language()` | [48] | [42] |

## 正确执行顺序
```
Cell 1 → 12 → 14 (Schema Rebuild) → 35 → 37 (Migrations)
→ 16 → 18 → 20 → 22 (ETL)
→ 40 → 42 (Weather + Venue Language)
→ 46 (Sync Schema) → 45 → 47 → 48 (Verify) → 49 (Conclusion)
```

**关键**：Cell 37（Migrations）必须在 Cell 16/18/20/22 之前执行，否则 `district` 列不存在会报错。

## 预期行数
| 表 | 预期行数 |
|----|----------|
| venues | ~3,479 |
| venue_source_links | ~3,479 |
| restroom_profiles | 476 |
| healthcare_profiles | 1,228 |
| emergency_assets | ~3,279 |
| pedestrian_ramps | 23,625 |
| venue_language | ~63 |
| external_context_cache | 1 |

## venues 列数：24
venue_id, venue_type, name, latitude, longitude, borough, **district**, language_tags, primary_language, secondary_language, accessible_status, accessibility_features, active_warning, open_now, address, phone, website, opening_hours, photos, rating, weather_risk, source_confidence, created_at, updated_at

## 重复数据根因
- `emergency_assets` 无唯一约束 → 每次 ETL 累积新行
- `venues` 和 `venue_source_links` 翻倍因 ETL 执行两次
- Cell 14 重建清除所有数据，唯一约束防止未来重复

## MySQL 版本注意
- MySQL 5.7 不支持 `ALTER TABLE ADD COLUMN ... COMMENT` 语法
- MIGRATIONS 中的 SQL 不要使用 COMMENT
