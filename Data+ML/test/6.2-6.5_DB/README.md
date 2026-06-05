# ClearPath 数据库构建 Notebook 说明文档

**文件**: `database_build.ipynb`
**日期**: 2026-06-05
**范围**: Manhattan 区域数据
**总 Cell 数**: 52 个

---

## 一、Notebook 整体结构

```
Part 1:  数据源验证           [Cell 0-3]
Part 2:  Schema 验证          [Cell 4-5]
Part 3:  数据量对比           [Cell 6-8]
Part 4:  数据质量检查         [Cell 9-10]
Part 5:  ETL 数据导入         [Cell 11-24]
Part 6:  导入验证             [Cell 25-27]
Part 7:  Schema 更新 (API)    [Cell 28-30]
Part 8:  表结构验证           [Cell 31-32]
Part 10: Backend API 对齐     [Cell 33-35]
Part 11: 表完成度验证         [Cell 36-37]
Part 12: Fix Plan 执行        [Cell 38-40]
Part 13: 最终验证             [Cell 41-43]
Part 14: Weather ETL          [Cell 44-46]
Part 15: Venue Language ETL   [Cell 47-50]
Part 16: 结论                 [Cell 51]
```

---

## 二、各 Cell 功能详解

### Cell [0] - 标题说明
- **类型**: Markdown
- **功能**: Notebook 标题和说明
- **内容**: 项目名称、日期、范围、目录

### Cell [1] - 初始化
- **类型**: Code
- **功能**: 导入库、配置、定义工具函数
- **内容**:
  - 导入: csv, json, re, hashlib, datetime, pymysql
  - 配置: MySQL 连接、Manhattan BBOX、NYC BBOX
  - 工具函数: `is_manhattan()`, `source_hash()`, `gen_vid()`, `get_conn()`
- **执行**: ✅ 必须第一个执行

### Cell [3] - 数据源验证
- **类型**: Code
- **功能**: 检查数据源文件是否存在
- **内容**: 读取 `clearpath_sources.json`，验证 6 个本地文件
- **输出**: 每个文件的行数/特征数

### Cell [5] - Schema 验证
- **类型**: Code
- **功能**: 验证 SQL Schema 文件结构
- **内容**: 检查 10 张表是否匹配预期
- **输出**: 表数量、排除的术语

### Cell [8] - 数据量对比
- **类型**: Code
- **功能**: 对比 Manhattan 数据量
- **内容**: 6 个数据源的 Expected vs Actual
- **输出**: 每个数据源的数量和差异百分比

### Cell [10] - 数据质量检查
- **类型**: Code
- **功能**: 记录级字段完整性分析
- **内容**:
  - Step 1: 对所有 6 个数据源做字段完整性分析
  - Step 2: 识别有问题的数据源
  - Step 3: LASS venue_language 预检查
- **输出**: 每个数据源的坐标/名称完整性百分比

### Cell [12] - ETL 工具函数
- **类型**: Code
- **功能**: 定义 ETL 工具函数和去重预处理函数
- **内容**:
  - MySQL 连接测试
  - 工具函数: `check_row()`, `validate_coords()`, `dedup_check()`, `fill_missing()`, `log_import()`
  - 去重函数: `dedup_restrooms()`, `dedup_parks()`, `dedup_aed()`, `dedup_healthcare()`, `dedup_ramps()`
- **执行**: ✅ ETL 前必须执行

### Cell [14] - Schema 重建
- **类型**: Code
- **功能**: 清空所有表并重建 Schema
- **内容**:
  - DROP TABLE IF EXISTS (13 张表)
  - 重新执行 `001_clearpath_schema.sql`
- **输出**: "Schema rebuilt: all tables dropped and recreated"
- **执行**: ⚠️ 危险操作，会清空所有数据

### Cell [16] - Restrooms ETL
- **类型**: Code
- **功能**: 导入 NYC Restrooms + Parks Toilets
- **内容**:
  - Phase 1: `dedup_restrooms()` + `dedup_parks()` 预去重
  - Phase 2: `etl_restrooms()` 导入到 venues + restroom_profiles + venue_source_links
- **输出**: imported=476, skipped=1206

### Cell [19] - AED ETL
- **类型**: Code
- **功能**: 导入 AED Inventory
- **内容**:
  - Phase 1: `dedup_aed()` 预去重
  - Phase 2: `etl_aed()` 导入到 venues + emergency_assets + venue_source_links
- **输出**: imported=1781, skipped=...

### Cell [22] - Healthcare ETL
- **类型**: Code
- **功能**: 导入 OSM + NYS Health (合并)
- **内容**:
  - Phase 1: `dedup_healthcare()` 预去重 (NYS 优先 + OSM GPS 匹配)
  - Phase 2: `etl_healthcare()` 导入到 venues + healthcare_profiles + venue_source_links
- **输出**: imported=1317, skipped=84

### Cell [24] - Ramps ETL
- **类型**: Code
- **功能**: 导入 Pedestrian Ramps
- **内容**:
  - Phase 1: `dedup_ramps()` 预去重
  - Phase 2: `etl_ramps()` 导入到 pedestrian_ramps (批量插入)
- **输出**: imported=23625, skipped=194054

### Cell [27] - 导入验证
- **类型**: Code
- **功能**: 验证导入后的数据量
- **内容**: 检查 8 张表的行数 + 数据源分布
- **输出**: 各表行数统计

### Cell [29-30] - Schema 更新 (API)
- **类型**: Code
- **功能**: 创建新表、添加新字段
- **内容**:
  - 创建: venue_accessibility, venue_language, venue_warnings
  - 修改: venues, user_reports, report_confirmations, busyness_scores
- **输出**: "Schema update applied"

### Cell [32] - 表结构验证
- **类型**: Code
- **功能**: 验证新增的表和字段
- **内容**: SHOW TABLES + DESCRIBE
- **输出**: 表数量、字段列表

### Cell [34-35] - Backend API 对齐
- **类型**: Code
- **功能**: 对齐 Backend API Schema
- **内容**: 添加 language_tags, accessible_status, weather_risk 等字段
- **输出**: "Backend API schema update applied"

### Cell [37] - 表完成度验证
- **类型**: Code
- **功能**: 验证所有表和字段
- **内容**: SHOW TABLES + DESCRIBE venues + DESCRIBE user_reports
- **输出**: 表数量、字段列表

### Cell [39-40] - Fix Plan 执行
- **类型**: Code
- **功能**: 执行 fix_plan.md 的 Schema 优化
- **内容**: 修改 venue_type enum、添加新字段、创建新表
- **输出**: "Fix plan applied successfully"

### Cell [42] - 最终验证
- **类型**: Code
- **功能**: 验证所有表和字段
- **内容**: SHOW TABLES + DESCRIBE
- **输出**: 表数量、字段列表

### Cell [43] - Schema 同步
- **类型**: Code
- **功能**: 同步 Schema 文件到数据库
- **内容**: 从数据库导出 CREATE TABLE 语句
- **输出**: "Schema file updated"

### Cell [45] - Weather API 测试
- **类型**: Code
- **功能**: 测试 NWS API 连接
- **内容**: 测试 5 个 API 端点
- **输出**: "ALL PASS — API is ready for ETL"

### Cell [46] - Weather ETL
- **类型**: Code
- **功能**: 获取天气数据并缓存
- **内容**:
  - 获取当前天气
  - 获取 7 天预报
  - 分类天气风险
  - 缓存到 external_context_cache
- **输出**: cached=2, failed=1

### Cell [48] - Venue Language ETL
- **类型**: Code
- **功能**: 导入 LASS 语言数据到 venue_language
- **内容**:
  - 解析 LASS 语言字符串
  - GPS 匹配 venues
  - 插入 venue_language 表
- **输出**: inserted=61, skipped=381

### Cell [50] - Venue Language 验证
- **类型**: Code
- **功能**: 验证 venue_language 导入结果
- **内容**: 语言支持级别分布、语言标签频率、示例记录
- **输出**: 详细的导入统计

---

## 三、执行顺序

### 方案 1: 首次执行 (完整流程)

```python
# 按顺序执行以下 cells
Cell 1  → 初始化
Cell 3  → 数据源验证
Cell 5  → Schema 验证
Cell 8  → 数据量对比
Cell 10 → 数据质量检查
Cell 12 → ETL 工具函数
Cell 14 → Schema 重建 (⚠️ 清空数据)
Cell 16 → Restrooms ETL
Cell 22 → Healthcare ETL
Cell 19 → AED ETL
Cell 24 → Ramps ETL
Cell 27 → 导入验证
Cell 29 → Schema 更新 (API)
Cell 30 → 执行 Schema 更新
Cell 32 → 表结构验证
Cell 34 → Backend API 对齐
Cell 35 → 执行 Backend API 对齐
Cell 37 → 表完成度验证
Cell 39 → Fix Plan SQL
Cell 40 → 执行 Fix Plan
Cell 42 → 最终验证
Cell 43 → Schema 同步
Cell 45 → Weather API 测试
Cell 46 → Weather ETL
Cell 48 → Venue Language ETL
Cell 50 → Venue Language 验证
```

### 方案 2: 重新执行 ETL (不清空 Schema)

```python
# 跳过 Schema 重建和 Schema 更新
Cell 1  → 初始化
Cell 8  → 数据量对比
Cell 12 → ETL 工具函数
Cell 16 → Restrooms ETL
Cell 22 → Healthcare ETL
Cell 19 → AED ETL
Cell 24 → Ramps ETL
Cell 27 → 导入验证
Cell 46 → Weather ETL
Cell 48 → Venue Language ETL
Cell 50 → Venue Language 验证
```

### 方案 3: 仅验证当前数据

```python
# 只执行验证 cells
Cell 1  → 初始化
Cell 27 → 导入验证
Cell 32 → 表结构验证
Cell 42 → 最终验证
Cell 50 → Venue Language 验证
```

---

## 四、安全性分类

| 类型 | Cells | 重复执行 | 说明 |
|------|-------|----------|------|
| ✅ 安全 | 1, 3, 5, 8, 10, 27, 32, 42, 50 | 完全安全 | 只读或验证操作 |
| ✅ 安全 | 16, 22, 19, 24, 46, 48 | 安全 | INSERT ... ON DUPLICATE KEY UPDATE |
| ⚠️ 警告 | 14 | ⚠️ 危险 | DROP TABLE，会清空数据 |
| ❌ 不安全 | 29, 30, 34, 35, 39, 40 | ❌ 重复执行报错 | ALTER TABLE ADD COLUMN |

---

## 五、ETL 流程详解

### 两阶段 ETL 设计

```
Phase 1: 去重预处理 (Cell 12)
    │
    ├─ dedup_restrooms()    → restrooms_deduped
    ├─ dedup_parks()        → parks_deduped
    ├─ dedup_aed()          → aed_deduped
    ├─ dedup_healthcare()   → nys_deduped, osm_deduped
    └─ dedup_ramps()        → ramps_deduped
    │
    ▼
Phase 2: 数据导入 (Cell 16, 19, 22, 24)
    │
    ├─ etl_restrooms()      → venues + restroom_profiles + venue_source_links
    ├─ etl_aed()            → venues + emergency_assets + venue_source_links
    ├─ etl_healthcare()     → venues + healthcare_profiles + venue_source_links
    └─ etl_ramps()          → pedestrian_ramps
```

### 去重规则

| 函数 | 去重键 | 筛选条件 | 输出 |
|------|--------|----------|------|
| `dedup_restrooms()` | `name.lower()` | Manhattan GPS | `restrooms_deduped` |
| `dedup_parks()` | `name.lower()` | Manhattan Borough | `parks_deduped` |
| `dedup_aed()` | `ename\|address` | Manhattan Borough | `aed_deduped` |
| `dedup_healthcare()` | GPS <30m (NYS 优先) | Manhattan | `nys_deduped, osm_deduped` |
| `dedup_ramps()` | `ramp_id` | Borough=1 | `ramps_deduped` |

### 数据源置信度

| 数据源 | 置信度 | 原因 |
|--------|--------|------|
| NYS Health | 0.9 | 官方政府数据 |
| AED Inventory | 0.8 | 已验证库存 |
| NYC Restrooms | 0.6 | 城市数据，可能过时 |
| OSM Healthcare | 0.5 | 社区贡献数据 |
| Parks Toilets | 0.3 | 无坐标数据 |
| LASS Ratings | 0.4 | 政府评估数据 |

---

## 六、数据库表结构

### 主表

| 表名 | 行数 | 说明 |
|------|------|------|
| venues | 3,564 | 统一 POI 表 |
| venue_source_links | 3,564 | 数据来源追踪 |

### 详情表

| 表名 | 行数 | 说明 |
|------|------|------|
| restroom_profiles | 476 | 洗手间详情 |
| healthcare_profiles | 1,313 | 医疗机构详情 |
| emergency_assets | 1,775 | AED 设备详情 |
| pedestrian_ramps | 23,625 | 行人坡道数据 |
| venue_language | 61 | 多语言支持信息 |

### 运行时表 (MVP 阶段为空)

| 表名 | 行数 | 说明 |
|------|------|------|
| user_reports | 0 | 用户上报事件 |
| report_confirmations | 0 | 用户确认/投票 |
| busyness_scores | 0 | ML 繁忙度预测 |
| venue_accessibility | 0 | 无障碍信息 (待填充) |
| venue_warnings | 0 | 警告信息 (运行时) |

### 缓存表

| 表名 | 行数 | 说明 |
|------|------|------|
| external_context_cache | 2 | 天气 API 缓存 |

---

## 七、常见问题

### Q1: Schema 重建报错 "Failed to open the referenced table 'venues'"

**原因**: SQL 文件中 `venues` 表被最后创建，但其他表的外键都引用它。

**解决**: 已修复 `001_clearpath_schema.sql`，让 `venues` 表第一个创建。

### Q2: 重复执行 ETL 会插入重复数据吗？

**不会**。所有 ETL 函数使用 `INSERT ... ON DUPLICATE KEY UPDATE`，重复执行会更新已有记录。

### Q3: 如何重新执行 ETL 但不清空数据？

跳过 Cell [14] (Schema Rebuild)，直接执行 Cell [16], [19], [22], [24]。

### Q4: venue_language 表为什么只有 61 条记录？

LASS 数据是政府服务中心评估数据，只有 442 条 Manhattan 记录，其中 61 条能与 venues 表 GPS 匹配。

---

## 八、数据源说明

| 数据源 | 文件 | 记录数 | Manhattan | 用途 |
|--------|------|--------|-----------|------|
| NYC Public Restrooms | Public_Restrooms_20260526.csv | 1,066 | 358 | 洗手间 |
| Parks Toilets | Directory_Of_Toilets_In_Public_Parks_20260526.csv | 616 | 129 | 公园厕所 |
| OSM Healthcare | POI_healtcare.geojson | 966 | 900 | 医疗机构 |
| NYS Health Facility | Health_Facility_General_Information_20260526.csv | 5,963 | 454 | 医疗机构 |
| AED Inventory | New_York_City_Automated_External_Defibrillator_(AED)_Inventory_20260526.csv | 7,373 | 3,393 | AED 设备 |
| Pedestrian Ramps | Pedestrian_Ramp_Locations_20260526.csv | 217,679 | 23,625 | 行人坡道 |
| LASS Ratings | Language_Access_Secret_Shopper_(LASS)_Ratings_20260526.csv | 1,231 | 442 | 多语言支持 |
| Weather API | NWS API (weather.gov) | — | — | 天气数据 |

---

## 九、注意事项

1. **执行顺序**: 严格按照推荐顺序执行，避免依赖错误
2. **Schema 重建**: Cell [14] 会清空所有数据，仅在首次执行或重建时使用
3. **MySQL 连接**: 确保 MySQL Docker 容器正在运行
4. **数据路径**: 数据文件位于 `/Users/alex/Documents/COMP47360-Research_Practicum/data_source/`
5. **Schema 文件**: `001_clearpath_schema.sql` 已修复表创建顺序
