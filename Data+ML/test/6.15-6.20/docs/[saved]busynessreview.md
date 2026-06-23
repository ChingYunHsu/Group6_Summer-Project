# busyness_ingestion.py 功能实现进展

> 初始审查：2026-06-15  
> 最近更新：2026-06-15  
> 源文件：`Data+ML/test/6.15-5.20/src/busyness_ingestion.py`  
> 测试文件：`Data+ML/test/6.15-5.20/tests/test_busyness_ingestion.py`

## 实现进展

### 已完成

| 日期 | 事项 | 状态 |
|------|------|------|
| 06-15 | `busyness_ingestion.py` ETL 管道实现 | ✅ |
| 06-15 | 44 个单元测试全部通过 | ✅ |
| 06-15 | 5 个旧接口测试修复 (`cursor.execute` → `executemany.call_args`) | ✅ |
| 06-15 | `test_successful_insert` rows 验证逻辑修正 (result==2 → result==3) | ✅ |
| 06-15 | 过时 xfail 从 `test_dropna_on_avg_vol_hh` 移除 | ✅ |
| 06-15 | `pytest-timeout` 配置写入 pyproject.toml (`timeout = 30`) | ✅ |
| 06-15 | `dqr_cleaning_pipeline.ipynb` Part 8 — Busyness 数据总览 | ✅ |
| 06-15 | notebook cell 19 — 数据规模与训练目标说明 | ✅ |
| 06-15 | notebook cell 23 — 12h 预测曲线图 (按 district 去重, 多色区分) | ✅ |
| 06-15 | notebook cell 24 — forecast_1h JSON 展开预览 | ✅ |
| 06-15 | 文件整理至 `6.15-5.20/` 目录 | ✅ |

### 待完成

Null

### 当前数据状态

```text
busyness_scores: 114,720 rows (4,780 venues × 24h)
model_version: nyc_traffic_baseline_v1
粒度: district 级别 (同 district 所有 venue 共享同一份分数)
覆盖率: 28/28 segments → 4,714 venues across 4 districts
DQ 评分: 96.3/100 (Excellent)
```

### 关键修复记录

#### test_busyness_ingestion.py — 5 个旧接口测试 (2026-06-15)

实现已改为 `cursor.executemany(sql, rows)`，但测试仍断言 `cursor.execute`。修复：

| 测试 | 修改前 | 修改后 |
|------|--------|--------|
| `test_successful_insert` | `execute.assert_called()`, result==2 | `executemany.assert_called_once()`, result==3, len(rows)==3 |
| `test_default_model_version` | `execute.assert_called()` | `executemany.assert_called_once()` |
| `test_custom_model_version` | `call_args[0][1][-2]` | `rows[0][6]` (executemany row tuple) |
| `test_forecast_json_in_insert` | `call_args[0][1][3]` | `rows[0][3]` |
| `test_features_snapshot_default` | `call_args[0][1][-1]` | `rows[0][-1]` |

#### dqr_cleaning_pipeline.ipynb — Part 8 更新 (2026-06-15)

- Cell 19：新增数据规模说明（所有 venue × 24h 笛卡尔积）和训练目标（预测 12h 连续数值）
- Cell 23：改为按 district 去重取代表性 venue，4 种颜色区分，图例移到右侧
- Cell 24：forecast_1h JSON 展开，展示 12h 预测轨迹

## 数据流全景

```
NYC SODA API (交通流量)
  │
  ▼
fetch_busyness_data()     ← API 获取 + EPSG2263→WGS84 + Manhattan 过滤
  │
  ▼
aggregate_by_segment()    ← 按 segment+hour 分组, 重算 score
  │
  ▼
map_segments_to_venues()  ← haversine 距离匹配 → venue_id + district
  │
  ▼
build_forecast_1h()       ← 12h 滚动预测窗口
  │
  ▼
insert_busyness_scores()  ← executemany 写入 MySQL busyness_scores 表
  │
  ▼
Flask API (src/api/venues.py) ← 读取 busyness_scores → 返回给前端
  │
  ▼
React 前端 (frontend/web/src/data/venues.js) ← 展示 busyness_level + percent + 预测
```

## 测试套件结构 (44 tests)

### 1. 分数分类 — TestClassifyScore (4 tests)

**源函数**：`classify_score(score)` → 分类为四级标签

| 分数区间 | 返回值 | 含义 |
|---------|--------|------|
| 0 | `no_data` | 无数据 |
| 1-54 | `quiet` | 清闲 (深夜/凌晨) |
| 55-69 | `moderate` | 一般 (非高峰) |
| 70+ | `busy` | 拥挤 (高峰) |

**关联**：`aggregate_by_segment` 和 `insert_busyness_scores` 内部调用此函数计算 `busyness_level`。前端 `src/api/venues.py` 的 `_level_to_color` 消费这些标签（quiet→green, moderate→yellow, busy→red）。

---

### 2. GPS 坐标转换 — TestWktParsing + TestEpsgConversion (3 tests)

**源函数**：
- `parse_wkt_point(wkt)` — 从 WKT POINT 字符串提取 x/y 坐标
- `epsg2263_to_wgs84(x, y)` — NYC State Plane (EPSG:2263) → WGS84 经纬度

**关联**：`fetch_busyness_data` 从 SODA API 获取的交通数据使用 EPSG:2263 投影坐标，必须转换为经纬度才能与 venues 的 GPS 坐标做距离匹配。

---

### 3. 距离计算 — TestHaversine (2 tests)

**源函数**：`haversine_m(lat1, lng1, lat2, lng2)` → 两点间距离（米）

**关联**：`map_segments_to_venues` 用此函数判断交通路段是否在 venue 的 50m 覆盖范围内。

---

### 4. 路段聚合 — TestAggregateBySegment (4 tests)

**源函数**：`aggregate_by_segment(df)` → 按 segment+hour 分组并重算 score

关键行为：
- **保留 GPS**：`lat`/`lng` 列不丢失
- **重算 score**：`score = avg_vol / peak_vol × 100`，不沿用输入值
- **重算 level**：基于新 score 重新分类，忽略输入的 `busyness_level`

**关联**：`run_pipeline` 的第二步，将 `fetch_busyness_data` 的原始数据聚合后传给 `map_segments_to_venues`。

---

### 5. Venue 匹配 — TestMapSegmentsToVenues (7 tests)

**源函数**：`map_segments_to_venues(conn, segment_hourly)` → 路段映射到附近场馆

测试覆盖：
- 空输入 → 空结果
- 基本匹配 — 路段 GPS 与 venue 相同
- 距离过远 (~5km) → 不匹配
- 同 district 聚合 — 同 district 多个 venue 获得相同 score
- 空 venues 表 → 空结果
- 多路段多 district → 分别匹配
- 输出列校验 — 结果只含 `venue_id, district, hour, score, busyness_level`

**关联**：从 MySQL `venues` 表读取所有场馆，用 haversine 距离做最近匹配。

---

### 6. 预测生成 — TestBuildForecast1h (6 tests)

**源函数**：`build_forecast_1h(scores_df, target_hour)` → 12 小时滚动预测窗口

关键行为：
- **固定 12 条**：输出始终 12 条
- **跨午夜**：target_hour=22 → 输出 hour 22, 23, 0, 1, ..., 9
- **缺失小时填 no_data**：`percent=0, level='no_data'`
- **结构校验**：每条含 `offset_hours`, `percent`, `level`

**关联**：`insert_busyness_scores` 在构建 rows 时内联调用此函数，将 forecast JSON 序列化存入 `busyness_scores.forecast_1h` 列。前端 `src/api/venues.py` 的 `get_venue_busyness_forecast` 读取该 JSON 返回给用户。

---

### 7. DB 写入 — TestInsertBusynessScores (6 tests)

**源函数**：`insert_busyness_scores(conn, venue_scores_df, ...)` → executemany 批量写入

关键行为：
- 空 DataFrame → 返回 0
- 使用 `cursor.executemany(sql, rows)` 批量插入
- `cursor.rowcount` 返回受影响行数
- 默认 `model_version='nyc_traffic_baseline_v1'`
- `features_snapshot` 默认格式 `nyc_traffic_{year}_manhattan`

**关联**：写入的 `busyness_scores` 表被后端 API 消费：
- `src/api/venues.py:80` `get_venue_busyness` — 读 `score, level` 返回当前拥挤度
- `src/api/venues.py:141` `get_venue_busyness_forecast` — 读 `forecast_1h` 返回 12 小时预测

---

### 8. API 数据获取 — TestFetchBusynessData (7 tests)

**源函数**：`fetch_busyness_data(year, boro)` → 从 NYC SODA API 拉取并转换坐标

测试覆盖：
- 空 API 响应 → 空 DataFrame
- Manhattan 边界过滤 — 只保留 Manhattan 范围内的路段
- busyness_level 从 score 派生
- API 参数验证 — `$where` 包含年份和 boro
- dropna 处理 — `hh` 为非数字的行被丢弃
- 输出列完整性

**关联**：pipeline 的第一步。数据源为 NYC TLC 交通流量 API。

---

### 9. Pipeline 编排 — TestRunPipeline (5 tests)

**源函数**：`run_pipeline(year, dry_run, model_version)` → 编排整个 ETL 流程

测试覆盖：
- 空交通数据 → 提前中止
- 空聚合结果 → 提前中止
- dry_run 模式 → 不调用 insert
- 正常运行 → 调用 insert 并传递 model_version
- 空 venue 映射 → 中止并关闭连接

---

## 关联文件

| 文件 | 角色 |
|------|------|
| `Data+ML/test/6.8-6.12_DB/dqr/busyness_ingestion.py` | ETL 核心实现 |
| `Data+ML/test/6.8-6.12_DB/tests/test_busyness_ingestion.py` | 44 个单元测试 |
| `src/api/venues.py` | Flask API，消费 busyness_scores 表 |
| `frontend/web/src/data/venues.js` | 前端场馆数据 |
| `pyproject.toml` | 项目配置，含 pytest timeout 设置 |
