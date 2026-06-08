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

详见 [data-source-reference.md](data-source-reference.md) §ETL 后行数。

## venues 列数：24
venue_id, venue_type, name, latitude, longitude, borough, **district**, language_tags, primary_language, secondary_language, accessible_status, accessibility_features, active_warning, open_now, address, phone, website, opening_hours, photos, rating, weather_risk, source_confidence, created_at, updated_at

## 重复数据根因
- `emergency_assets` 无唯一约束 → 每次 ETL 累积新行
- `venues` 和 `venue_source_links` 翻倍因 ETL 执行两次
- Cell 14 重建清除所有数据，唯一约束防止未来重复

## MySQL 版本注意
- MySQL 5.7 不支持 `ALTER TABLE ADD COLUMN ... COMMENT` 语法
- MIGRATIONS 中的 SQL 不要使用 COMMENT

## 历史 Schema 修复结果（合并自 2026-06-03 记录）

来源文件保留在原目录：

- `Data+ML/test/6.2-6.5_DB/fix_summary.md`
- `Data+ML/test/6.2-6.5_DB/backend_database_README.md`

当时完成的基础工作包括：

- 扩展 `venues.venue_type`；
- 为 `venues` 增加照片、评分、天气、语言、无障碍和预警相关字段；
- 为报告、确认和拥挤度增加早期 API 对齐字段；
- 创建 `venue_accessibility`、`venue_language`、`venue_warnings`；
- 同步当时的 Docker/Test Schema 副本。

后续 notebook 迁移继续调整了该设计，包括删除历史
`forecast_4h/forecast_8h`、加入 district zoning、统一迁移执行路径和 ETL
事务辅助函数。因此 `fix_summary.md` 是历史执行记录，不是当前 Schema 清单。

## 数据源与运行边界

- 数据库采用一个 `clearpath` Schema，不为每个来源建立独立应用表。
- 原始数据是 ETL 输入，默认位于仓库外部的 `data_source/`。
- `clearpath_sources.json` 记录保留和排除的数据来源；修改 MVP 来源范围时应同步
  更新该清单与 notebook README。
- 本地 MySQL 由仓库根目录 `docker-compose.yml` 管理，初始化入口是
  `docker/mysql/init/001_clearpath_schema.sql`。
- Docker initializer 只在 MySQL volume 首次创建时自动执行。不得为了重新执行
  initializer 而未经确认删除 volume。
- 历史文档中的 `backend/database/validate_sources.py` 当前仓库不存在，不应作为
  有效验证命令。现阶段以 notebook 的数据源验证单元和
  `clearpath_sources.json` 人工核对为准。

## 文档准确性提示

当前 notebook 有 49 个 cells，索引为 `0` 至 `48`。应优先按 section 标题和
函数名定位；本文较早的执行顺序中若出现 `Cell 49`，属于旧编号引用。

## Safety Classification

| 类型 | Cells | 可重跑 | 说明 |
|------|-------|--------|------|
| ✅ Safe | 1, 3, 5, 8, 10, 25, 29, 33, 39, 45, 47, 48 | 完全安全 | 只读或验证 |
| ✅ Safe | 16, 18, 20, 22, 40, 42 | 安全 | INSERT ... ON DUPLICATE KEY UPDATE |
| ⚠️ Destructive | 14 | ⚠️ 危险 | DROP TABLE — 清除所有数据 |
| ❌ Not idempotent | 35, 37 | ❌ 重跑报错 | ALTER TABLE ADD COLUMN（preflight 检查可缓解） |

## FAQ

**Q1: Schema rebuild 报错 "Failed to open the referenced table 'venues'"**
原因：`venues` 在 SQL 文件中最后创建，但其他表通过 FK 引用它。
修复：`001_clearpath_schema.sql` 已修正，`venues` 现在最先创建。

**Q2: 重跑 ETL 会插入重复数据吗？**
不会。所有 ETL 函数使用 `INSERT ... ON DUPLICATE KEY UPDATE`，重跑更新已有记录。

**Q3: 如何不清数据重跑 ETL？**
跳过 Cell [14]（Schema Rebuild），直接执行 ETL cells（16, 18, 20, 22, 40, 42）。

**Q4: 为什么 venue_language 只有 ~63 条？**
LASS 数据覆盖政府服务中心，仅 442 条 Manhattan 记录，~63 条在 100m GPS 阈值内匹配到现有 venue。
