# ClearPath 执行计划 (DB Schema 重点)

> 更新日期：2026-06-09 | 审计: 与 openapi_gap_finalacceptcriteria.md 对齐
> 决策冻结: 2026-06-09 grill-with-docs 会话 (10 项)

---

## 已冻结决策 (D1-D10)

详见 `context-terms.md` — 以下为摘要：

| # | 决策项 | 结论 |
|---|-------|------|
| D1 | 认证方式 | 邮箱+密码（bcrypt），No OAuth |
| D2 | Guest 模式 | 无 token = Guest，被动访问 |
| D3 | 匿名报告 | 提交后匿名化，保留 `anonymous` 字段 |
| D4 | 拥挤度等级 | 三级 `quiet/moderate/busy`，NULL = 无数据 |
| D5 | 报告类别 | OpenAPI 8 个 issue_type 值 |
| D6 | 确认操作 | 覆盖旧 action，`UNIQUE (report_id, user_id)` |
| D7 | `auth_subject` | 不需要，邮箱即认证标识 |
| D8 | 报告类别存储 | 字典表 `report_categories`（按场馆类型过滤） |
| D9 | RAG embedding | MySQL JSON/BLOB（~3500 条数据量足够） |
| D10 | 医疗数据边界 | 云端加密存储（AES-256-GCM）+ 本地无独立副本 |

---

## 已完成项

- [x] emergency_assets 唯一约束 `(venue_id, floor, location_type)` — session 2026-06-06
- [x] District Zoning: venues.district + pedestrian_ramps.district — session 2026-06-09
- [x] forecast_4h/8h 从 busyness_scores 删除 — session 2026-06-06
- [x] forecast_1h 改为 JSON 类型 — session 2026-06-06
- [x] Schema 文件同步 (test → 001_clearpath_schema.sql) — session 2026-06-06
- [x] D1-D10 产品决策冻结 — session 2026-06-09 (grill-with-docs)
- [x] busyness_scores ENUM 改为 `quiet/moderate/busy` + 删除 forecast_4h/8h — session 2026-06-09

---

## Phase 1: 基础同步与决策冻结

**目标**: 统一 Schema 文件, 冻结产品决策

- [x] 同步两份 `001_clearpath_schema.sql` (docker/mysql/init/ ↔ Data+ML/test/6.2-6.5_DB/)
- [x] 冻结 10 项产品决策 — 已完成，见 `context-terms.md`

---

## Phase 2: 用户与账户表

**目标**: 建立认证基础 (D1 邮箱+密码, D2 Guest 无 token)

~~### 新建 `users` 表~~ ✅ 2026-06-09

~~### 新建 `user_favorite_venues` 表~~ ✅ 2026-06-09

~~### 新建 `notification_preferences` 表~~ ✅ 2026-06-09

---

## Phase 3: 报告系统改造

**目标**: 绑定认证用户, 防重复投票, 按场馆类型过滤类别

~~### 改造 `user_reports`~~ ✅ 2026-06-09

~~### 改造 `report_confirmations`~~ ✅ 2026-06-09

~~### 新建 `report_categories` 字典表 (D8: 按场馆类型过滤)~~ ✅ 2026-06-09

---

## Phase 4: 拥挤度预测

**目标**: 支持 12 小时预测图表

~~### 新建 `busyness_forecasts` 表 (D4 + D9)~~ ✅ 2026-06-09

---

## Phase 5: RAG 数据层

**目标**: 支持 Gemini RAG 查询

~~- [ ] 为 `venues(latitude, longitude)`、`venue_type`、`district` 建立索引~~ ✅ 2026-06-09
~~- [ ] 生成可检索的场馆文档投影 (含语言、无障碍、营业、警告、实时拥挤度)~~ ⏳ 待后端实现
~~- [x] embedding 存储方案确定: MySQL JSON/BLOB (D9) — ~3500 条数据量足够~~ ✅
~~- [ ] 创建 `venue_embeddings` 表~~ ✅ 2026-06-09
~~- [ ] 不创建服务端 `chat_history` 表 (Final 要求聊天历史仅客户端)~~ ✅ 确认不创建

~~### 新建 `venue_embeddings` 表 (D9: MySQL JSON/BLOB)~~ ✅ 2026-06-09

---

## Phase 6: OpenAPI 与验证

**目标**: 确保 API 与 DB 一致

- [x] 更新 mock_data.py: `REPORT_CONFIRMATION_TEMPLATE` 加 `user_id` (openapi_gap #9) ✅ 2026-06-09
- [x] 更新 mock_data.py: `INSIGHTS_DASHBOARD.district` 改为 lowercase `midtown_east` ✅ 2026-06-09
- [x] 更新 ETL notebook 验证新表结构 ✅ 2026-06-09
- [x] 级联删除测试 (删除用户 → 收藏、通知、报告一并清除) ✅ 2026-06-09
- [x] 第二次 ETL 幂等性验证 (不产生重复行) ✅ 2026-06-09
- [x] 同步 Docker schema (test → docker/mysql/init/) ✅ 2026-06-09
- [x] MySQL 5.7 COMMENT 语法兼容性检查 ✅ 无 COMMENT 语法问题

---

## 实施依赖关系

```
Phase 1 (同步+决策)
    ↓
Phase 2 (users + favorites + notifications)
    ↓
Phase 3 (reports user_id + confirmations user_id)
    ↓
Phase 4 (busyness_forecasts)
    ↓
Phase 5 (RAG 索引)
    ↓
Phase 6 (验证+清理)
```

**Phase 2 是所有后续阶段的前置条件** — 没有 users 表, Phase 3/5 都无法执行。

---

## 风险提示

1. **按旧 Pipeline 实现服务器医疗 Profile** — 违反 Final 隐私边界
2. **继续允许无法追踪用户身份的报告/确认** — 无法执行唯一用户确认
3. **12 小时预测数据失真** — 单值伪造数组无法支撑真实图表

---

## Sprint 2 数据任务 (fangxun.wu)

**目标**: 完成数据库 ERD 修订、数据摄取、模拟数据和 ML 模型初始化
**总工时**: Est. 46h

| # | Task | Week | Description | Status | Est. (h) |
|---|------|------|-------------|:------:|:--------:|
| D2.1 | ERD Revision, Schema Updates & District Zoning Setup | Week 4 | ERD update + 4 district nodes | ✅ 2026-06-09 | 5 |
| D2.2 | MySQL Table Implementation & Index Tuning | Week 4 | DDL scripts + FK constraints + composite indexes | ✅ 2026-06-09 | 5 |
| D2.3 | Data Parsing & Ingestion | Week 5 | ETL: 349 restrooms, 900 healthcare, 431 NYS, 3,279 AEDs, 63 LASS | ✅ 2026-06-05 | 10 |
| D2.4 | API & Map Mocking Data Arrays | Week 4 | JSON mock data grouped by lowercase district tokens | ⚠️ 部分完成 | 6 |
| D2.5 | Zoned Historical Ingestion & ML Model Init (Advance Start) | Week 5 | [High Priority] traffic_hourly.csv fetched; ARIMA/LSTM pending | ⚠️ 进行中 | 10 |
| D2.6 | Data Deduplication & Multi-Source Cleansing Preprocessing | Week 5 | GPS duplicate detection (grid+haversine, lat-scaled) | ✅ 2026-06-11 | 10 |
| D2.7 | Database Integrity, Privacy & Constraint Unit Testing | Week 5 | PyTest: 100% venues non-Null district; 12 test cases | ✅ 2026-06-11 | — |

### DQR Pipeline Refactoring (2026-06-11)

- 6 shared modules in `Data+ML/test/shared/` (dqr_utils, dqr_io, dqr_checks, dqr_analysis, dqr_cleaning, external_ingestion)
- Notebook: 21 cells, 218 code lines (from 40 cells, 406 lines)
- Output moved to `output/` subdirectory
- All imports consolidated in Cell 2
- pytest: 12 tests pass (D2.7, GPS grid, export overwrite, import path, clean_venues immutability)

### Park Toilet GPS Fix (2026-06-11)

- 124 zero-coordinate restroom venues fixed using NYC Open Data (`i7jb-7jku`)
- 93 Manhattan-可信 matches written to DB
- 3 Bronx Jackie Robinson Park entries deleted (wrong Borough)
- CSV `Directory_Of_Toilets_In_Public_Parks_20260526.csv` updated: +Latitude/Longitude columns
- DB: 473 restrooms, 100% GPS, 0 null districts



Sprint2 重点任务 D2.5 进展说明：
### D2.5 ARIMA/LSTM 实施计划

#### 当前数据限制

- `traffic_hourly.csv` 是按道路方向和小时聚合的 24 小时年度平均轮廓，不是连续历史时间序列。
- 当前数据缺少日期、连续时间戳和 `venue_id`，不能直接作为可信的 ARIMA/LSTM 生产训练集。
- 该文件仅保留为小时轮廓分析和演示基线，不标记为生产训练数据。

#### 实施阶段

1. **历史序列重构**: 从 NYC SODA 保留 `yr`、`m`、`d`、`hh`，按道路方向生成 `traffic_timeseries.csv`。
2. **基线模型**: 实现 24 小时季节性朴素预测，作为 SARIMA/LSTM 的最低性能基准。
3. **SARIMA**: 使用 Statsmodels SARIMAX 为每条道路方向训练时序模型；数据不足时回退到季节性基线。
4. **LSTM**: 使用 PyTorch 训练共享模型，输入过去 24 或 48 小时，输出未来 12 小时。
5. **场馆映射**: 建立道路序列到场馆的空间映射，生成 `venue_traffic_mapping.csv`，字段为 `venue_id`、`series_id`、`distance_m`。
6. **预测发布**: 统一输出 `forecast_for`、`predicted_score`、`predicted_level`、`model_version`，最终写入 `busyness_forecasts`。

数据库写入默认关闭。只有模型通过验证且预测记录具有有效场馆映射后，才允许显式启用写入。

#### 产物与接口

- `traffic_timeseries.csv`
- `venue_traffic_mapping.csv`
- `busyness_forecasting.ipynb`
- SARIMA/PyTorch 模型文件和模型评估报告
- 连续 12 小时预测结果

`predicted_score` 必须限制在 `0-100`，等级规则如下：

- `< 30`: `quiet`
- `30-70`: `moderate`
- `> 70`: `busy`

#### 验收标准

- 每条训练序列至少覆盖 7 天，推荐覆盖 28 天以上。
- 训练、验证和测试集必须按时间顺序切分，禁止随机切分。
- SARIMA 或 LSTM 至少一个模型必须优于 24 小时季节性朴素基线。
- 每次预测必须输出连续 12 个小时，且不得包含重复时间点。
- 所有预测分数必须位于 `0-100`，等级必须符合统一阈值。
- 没有有效 `venue_id` 映射的道路预测不得写入 `busyness_forecasts`。
