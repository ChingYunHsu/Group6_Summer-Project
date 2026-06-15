# ClearPath 现有问题

> 更新日期：2026-06-11 | Commit: 749c57b PR#12 merged | 来源：Sprint 2 数据任务审计
> 评审日期：2026-06-11 | 评审方法：对比 sprint-tasks-1-4.md 计划 vs 代码实际
> 最后更新：2026-06-11 | D2.1 ERD 图表已导出

---

## 🔴 P0 — 阻塞性问题

### 1. ~~users 表缺失 — 无法认证~~ ✅ 已解决 2026-06-09
- **影响**: JWT 认证、报告登录、收藏同步全部依赖 users 表
- **状态**: ✅ 已创建 `users` 表 (D1: 邮箱+密码, D7: 无 auth_subject)
- **详见**: `execution-plan.md` Phase 2

### 2. ~~user_reports / report_confirmations 缺 user_id~~ ✅ 已解决 2026-06-09
- **影响**: 无法防重复投票、无法执行级联删除、无法追踪报告来源
- **Final 要求**: "Login Required: must be logged in to submit or verify reports"
- **状态**: ✅ 已 ALTER TABLE (加 user_id FK, DROP reported_by, UNIQUE 约束)
- **详见**: `execution-plan.md` Phase 3

### 3. ~~busyness_forecasts 表缺失 — 12h 预测无数据源~~ ✅ 已解决 2026-06-09
- **影响**: `GET /venues/{id}/busyness/forecast` 返回假数据
- **OpenAPI**: 定义了 12 元素数组 `[{offset_hours, percent, level}]`
- **状态**: ✅ 已创建 `busyness_forecasts` 表 (D4: quiet/moderate/busy/no_data)
- **详见**: `execution-plan.md` Phase 4

### 4. ~~venues 表缺少 district 列 — Docker vs Data+ML schema 不同步~~ ✅ 已解决 2026-06-11
- **文件**: `docker/mysql/init/001_clearpath_schema.sql:379-380`
- **影响**: Docker schema 的 venues 表使用 `borough` 而非 `district`，但 `idx_venues_district` 索引和 `idx_venues_type_district` 索引引用 `venues(district)` — 该列在 Docker schema 中不存在。
- **状态**: ✅ 已解决
- **修复详情**:
  1. Docker schema 文件已包含 `district` 列定义（第 44 行）和索引定义（第 382-383 行）
  2. 运行中的 MySQL 实例已通过 `CREATE INDEX` 手动创建缺失索引（Docker volume 不会重新执行 initdb 脚本）
  3. 索引已验证: `idx_venues_district(district)` + `idx_venues_type_district(venue_type, district)`
- **注意**: 如果重建 Docker volume，initdb 脚本会自动创建这些索引

### 5. ✅ 已解决 MEDICAL_ID / EMERGENCY_CONTACTS 幻影导入 (b73309c) — 新增 2026-06-10
- **文件**: `src/api/user.py:6`
- **影响**: user.py 从 mock_data 导入 MEDICAL_ID 和 EMERGENCY_CONTACTS，但两者在 mock_data.py (783行) 中均未定义
- **状态**:✅ 已解决
- **失败场景**: 任何加载 user 蓝图的进程在导入时就会崩溃 (ImportError)。整个 Flask 应用启动失败（不是优雅的 404，而是硬崩溃）。
- **修复**: 在 mock_data.py 中添加 MEDICAL_ID 和 EMERGENCY_CONTACTS 的模拟数据。

### 6. ~~emergencyasset 命名漂移~~ ✅ 已解决 2026-06-10
- **文件**: `openapi.yaml:278`, `docker/mysql/init/001_clearpath_schema.sql:19`, `Data+ML/test/6.2-6.5_DB/001_clearpath_schema.sql:234`, `src/mock_data.py:176`
- **影响**: OpenAPI、DB schema ENUM、ETL notebook、mock_data 已统一为 `'emergencyasset'`（无下划线）
- **状态**: ✅ 已验证全链路（2026-06-10）
- **注**: `emergency_assets` 表名保留下划线（表名 ≠ ENUM 值）

---

## ⚠️ P1 — 对齐问题

### 7. ~~mock_data.py 两处缺口~~ ✅ 已解决 2026-06-09
- **状态**: ✅ 已修复

### 8. ~~拥挤度命名 — 已冻结 (D4)~~ ✅ 已解决 2026-06-09
- **状态**: ✅ 已执行 ALTER TABLE

### 9. ~~报告 issue_type — 已冻结 (D5 + D8)~~ ✅ 已解决 2026-06-09
- **状态**: ✅ 已建表 + ALTER

### 10. ~~Docker schema 与 test schema 不同步~~ ✅ 已解决 2026-06-09
- **状态**: ✅ 已同步



<!-- ### 12. ❌ confirm_report KeyError (b73309c) — 新增 2026-06-10，修正 2026-06-100
- **文件**: `src/api/reports.py:114`
- **影响**: `confirm_report()` 访问 `report['confirmation_count']`（顶层 key），但所有 mock 数据（r_501-r_507）使用嵌套 `confirmations.count` 结构，无顶层 `confirmation_count`
- **状态**: ❌ 未解决
- **严重程度**: ⚠️ 仅影响通过 API 调用 `POST /reports/{id}/confirmations` 路径。Mock 数据中的 reports 是独立副本（非全局引用），直接读取 mock 数据不受影响。
- **失败场景**: `POST /api/v1/reports/r_505/confirmations` 带 `action='still_here'` → `KeyError: 'confirmation_count'` → 返回 500。
- **修复**: 更新 `confirm_report()` 处理嵌套 `confirmations.count` 结构，或更新 mock data 使用顶层 `confirmation_count` key。 -->

---

## 📋 P2 — 待确认事项

### 13. 医疗数据边界 — D10 需求变更 🔄 2026-06-15
- **状态**: 🔄 已修订
- **原方案**: 云端加密存储（AES-256-GCM）
- **新方案**: 严格数据分层 — Tier 1 Profile Group(User ID/Email/Name[Read-Only] + Phone/Languages/Nationality[Editable])云端同步; Tier 2 Medical ID(DOB/Gender/Address/Emergency Contact/Blood Type/Allergies/Conditions)100%本地 Mobile Only; Web端Medical ID字段禁用; F-14打印通过render_token+QR码+P2P加密通道实现

### 14. ~~RAG 数据层 — 已冻结 (D9)~~ ✅ 已解决 2026-06-09
- **状态**: ✅ 已创建 venue_embeddings 表

### 15. ~~busyness_scores 表 0 行~~ ✅ 已解决 2026-06-09
- **状态**: ✅ 表结构就绪，待 ML pipeline 填充数据

### 16. ~~DQR 管道 O(N²) 效率问题~~ ✅ 已解决 2026-06-11
- **文件**: `Data+ML/test/6.8-6.12_DB/dqr_cleaning_pipeline.ipynb` Cell 24
- **影响**: detect_gps_duplicates() 函数进行 O(N²) 成对 haversine 比较，无空间预过滤
- **状态**: ✅ 已解决
- **修复详情**:
  1. 经纬度网格预过滤：将 Manhattan 划分为 ~30m 网格，每个 venue 仅与同格 + 8 邻格内的 ramp 点比较
  2. 跳过绝大多数远距离配对，候选数量从 114M 降至估计 <100K（<0.1%）
  3. 向量化 haversine 仅在小候选子集上执行，内存峰值 ~KB 级（非 90MB/块）
  4. 添加 `time.perf_counter()` 计时和候选数量日志输出
  5. 零新依赖（仅 numpy + pandas）
  6. 输出结果数量不变（9,425 对 < 30m）

### 17. ~~dqr_utils.py 代码重复~~ ✅ 已解决 2026-06-11
- **文件**: `Data+ML/test/6.2-6.5_DB/dqr_utils.py` 和 `Data+ML/test/6.8-6.12_DB/dqr_utils.py`
- **影响**: 两个目录中的 dqr_utils.py 文件完全相同（82行），导致维护困难
- **状态**: ✅ 已解决
- **修复详情**:
  1. 唯一副本移至 `Data+ML/test/shared/dqr_utils.py`（单一权威源）
  2. `dqr_cleaning_pipeline.ipynb` Cell 3 导入路径改为 `parents[1] / 'shared'`
  3. 两个测试目录中的副本已删除
  4. Cell 31 冗余 `from dqr_utils import MANHATTAN_BOUNDS` 已移除（Cell 3 已导入）
  5. `database_build.ipynb` 不导入 dqr_utils，无需修改
  6. Kernel 已重启清除旧模块缓存

<!-- ### 18. ❌ D2.4 Mock 数据不完整 — 缺少按区域分组 (749c57b) — 新增 2026-06-11
- **文件**: `src/mock_data.py`
- **影响**: 当前只有 3 个 mock venues，且仅覆盖 Midtown East 区域。Sprint 2 要求 JSON mock data 按 lowercase district tokens 分组。
- **状态**: ❌ 未解决
- **失败场景**: API 开发和前端联调时无法获取完整的区域测试数据。`GET /venues?district=downtown` 等过滤查询无法验证。
- **修复**: 扩展 mock_data.py，为 downtown、midtown_west、midtown_east、uptown 四个区域各添加 5-10 个代表性 venues。 -->

### 19. ❌ D2.5 ML 模型未实现 — ARIMA/LSTM 缺失 (749c57b) — 新增 2026-06-11
- **文件**: `Data+ML/test/6.8-6.12_DB/`
- **影响**: Sprint 2 任务 D2.5 要求 "init ARIMA/LSTM"，但当前只有 DQR pipeline，无 ML 模型实现
- **状态**: ❌ 未解决
- **失败场景**: Sprint 3 的 D3.1 (Real-Time Telemetry) 和 D3.2 (12-Hour Forecast) 依赖 ML 模型输出。缺少模型将阻塞 Sprint 3 数据任务。
- **修复**: 创建独立 notebook 实现 ARIMA/LSTM 拥挤度预测模型，使用 traffic_hourly.csv 作为训练数据。

### 20. ~~D2.7 单元测试缺失~~ ✅ 已解决 2026-06-11
- **文件**: `Data+ML/test/6.8-6.12_DB/tests/test_dqr_modules.py`
- **影响**: Sprint 2 任务 D2.7 要求 "PyTest: 100% venues non-Null district classification"
- **状态**: ✅ 已解决
- **修复详情**:
  1. DQR notebook Cell 21: `3.7 Database Integrity (D2.7)` — 运行时检查
  2. pytest 文件 `test_dqr_modules.py`: 12 个测试用例 — D2.7 (5 cases), GPS grid (2), export overwrite (2), import path (1), clean_venues immutability (2)
  3. conftest.py: cwd-independent path resolution via `Path(__file__)`
  4. 所有 12 tests pass

### 21.  D2.1 ERD 图表未导出 — 仅有 ASCII 架构图 (749c57b) — 新增 2026-06-11
- **文件**: `Data+ML/plan/6.2_CC/6.2_architecture.md`
- **影响**: D2.1 任务要求 ERD 图表，但只有 ASCII 文本架构图，无可视化 ERD 图片
- **状态**: ✅ 已解决
- **失败场景**: 无法直观展示表关系，新成员理解数据库结构困难，技术文档不完整
- **修复**: 
  1. 使用 Mermaid 语法创建 ERD 图表 (`docs/erd/clearpath_erd.mmd`)
  2. 导出为 PNG 和 SVG 格式 (`docs/erd/clearpath_erd.png`, `docs/erd/clearpath_erd.svg`)
  3. `Data+ML/README.md` 暂未更新 ERD 图表链接（后续补充）

---

## Sprint 2 Data 任务进度审计 (2026-06-11, verified)

| 任务 | 计划状态 | 实际状态 | 偏差 |
|------|----------|----------|------|
| D2.1 ERD Revision, Schema Updates & District Zoning | 🔄 In progress | ✅ 已完成 | Schema 完成，ERD 图表已导出 (docs/erd/) |
| D2.2 MySQL Table Implementation & Index Tuning  ✅ 已完成 | 19 tables, 20 FK, composite indexes verified |
| D2.3 Data Parsing & Ingestion |  | ✅ 已完成 | 7 sources, ~30K rows, clearpath_sources.json |
<!-- | D2.4 API & Map Mocking Data Arrays | ❌ Not started | ⚠️ 部分完成 | 缺少区域分组 mock 数据 | -->
| D2.5 Zoned Historical Ingestion & ML Model Init | ❌ Not started  | traffic_hourly.csv fetched; ARIMA/LSTM pending |
| D2.6 Data Deduplication & Multi-Source Cleansing |  ✅ 已完成 | GPS duplicate detection (grid+haversine, lat-scaled) |
| D2.7 Database Integrity Unit Testing | ✅ 已完成 | 12 pytest cases in test_dqr_modules.py, all pass |

---

## 已解决的问题

| # | 问题 | 解决方式 | 来源 |
|---|------|---------|------|
| 1 | `phone_number` vs `phone` | mock_data.py 已改为 `phone` | session 2026-06-06 |
| 2 | forecast_4h/8h 残留字段 | 已从 DB 删除 + schema 同步 | session 2026-06-06 |
| 3 | ~~Medical ID 端点~~ | ~~已从 OpenAPI 移除 (device-local)~~ → D10 修订后需恢复（加密版） | openapi_gap (1.3) → D10 修订 2026-06-09 |
| 4 | 12h 预测结构 | 独立 `busyness_forecasts` 表方案确定 | openapi_gap (1.5) |
| 5 | issue_type 缺 2 值 | 已补 `ramp_blocked` + `closed_early` | openapi_gap (1.4) |
| 6 | GET /reports 无过滤 | 已加 `venue_id`, `issue_type`, `status` | openapi_gap (#10) |
| 7 | Report.status 缺 expired | 已加 | openapi_gap (#11) |
| 8 | Insights tag 错误 | 已改为 `Insights` tag | openapi_gap (#6) |
| 9 | Favourites CRUD | 已加 POST + DELETE | openapi_gap (#4) |
| 10 | Account Delete | 已加 DELETE 端点 | openapi_gap (#3) |
| 11 | D1 认证方式 | 邮箱+密码 (bcrypt), No OAuth | grill-with-docs 2026-06-09 |
| 12 | D2 Guest 模式 | 无 token = Guest, 被动访问 | grill-with-docs 2026-06-09 |
| 13 | D3 匿名报告 | 提交后匿名化, 保留 `anonymous` 字段 | grill-with-docs 2026-06-09 |
| 14 | D4 拥挤度等级 | 三级 `quiet/moderate/busy`, NULL=无数据 | grill-with-docs 2026-06-09 |
| 15 | D5 报告类别 | OpenAPI 8 个 issue_type 值 | grill-with-docs 2026-06-09 |
| 16 | D6 确认操作 | 覆盖旧 action, `UNIQUE (report_id, user_id)` | grill-with-docs 2026-06-09 |
| 17 | D7 `auth_subject` | 不需要, 邮箱即认证标识 | grill-with-docs 2026-06-09 |
| 18 | D8 报告类别存储 | 字典表 `report_categories` (按场馆类型过滤) | grill-with-docs 2026-06-09 |
| 19 | D9 RAG embedding | MySQL JSON/BLOB (~3500条足够) | grill-with-docs 2026-06-09 |
| 20 | D10 医疗数据边界 | ~~严格本地~~ → ~~云端加密~~ → **严格数据分层**: Tier 1 标准档案云端同步 + Tier 2 医疗ID 100%本地隔离 + F-14 QR-P2P打印 | grill-with-docs 2026-06-09 → 修订 2026-06-15 |
| 21 | Chatbot RAG | 已加 POST 端点 | openapi_gap (#2) |
| 22 | Medical Passport PDF | 已加 GET 端点 | openapi_gap (#5) |
| 23 | RouteOption per-mode | 已加 `summary_by_mode` | openapi_gap (#13) |
| 24 | category vs venue_type | 无冲突，API 层映射 | openapi_gap (1.1) |
| 25 | weather_risk 列 | 已在 DB 中存在 | session 2026-06-06 |
| 26 | District Zoning | venues + pedestrian_ramps 已实现 | session 2026-06-09 |
| 27 | emergency_assets 重复写入 | 已加唯一约束 | session 2026-06-06 |
| 28 | P0 #1 users 表缺失 | ✅ 已创建 users 表 (Phase 2) | session 2026-06-09 |
| 29 | P0 #2 user_reports/report_confirmations 缺 user_id | ✅ 已 ALTER TABLE (Phase 3) | session 2026-06-09 |
| 30 | P0 #3 busyness_forecasts 表缺失 | ✅ 已创建表 (Phase 4) | session 2026-06-09 |
| 31 | Phase 5 venue_embeddings + 索引 | ✅ 已创建表 + indexes (Phase 5) | session 2026-06-09 |
| 32 | mock_data.py 两处缺口 | ✅ 已修复 (Phase 6) | session 2026-06-09 |
| 33 | forecast_1h INT → JSON 变更 | ✅ 已验证为计划内设计变更，文档齐全 | 代码审查 2026-06-10 |
| 34 | P1 #6 emergencyasset 命名漂移 | ✅ 全链路统一为 emergencyasset (4 files) | 代码修复 2026-06-10 |
| 35 | P0 #4 Docker venues 缺 district 索引 | ✅ 手动 CREATE INDEX (Docker volume 不重跑 initdb) | 数据库修复 2026-06-11 |
| 36 | P2 #17 dqr_utils.py 代码重复 | ✅ 移至 shared/ + 删除副本 + 更新导入路径 | 代码重构 2026-06-11 |
| 37 | P2 #16 DQR O(N²) 效率问题 | ✅ 网格预过滤 + 向量化 haversine，候选 <0.1% | 性能优化 2026-06-11 |
| 38 | P2 #20 D2.7 单元测试缺失 | ✅ 合并到 DQR notebook Cell 22 (3.7 Database Integrity) | 测试合并 2026-06-11 |
| 39 | D2.1 ERD 图表未导出 | ✅ Mermaid 语法创建 + 导出 PNG/SVG | 2026-06-11 |
| 40 | DQR notebook 406 行 / 重复导入 / 无 pytest | ✅ 拆为 6 modules + 218 行 notebook + 12 tests | 2026-06-11 |
| 41 | GPS 网格漏检高纬度重复点 | ✅ GRID_LNG 按 cos(40.88°) 缩放 | 2026-06-11 |
| 42 | export_dqr_artifacts 空结果不覆盖旧 CSV | ✅ unlink() 删除过期文件 | 2026-06-11 |
| 43 | Park toilet 124 零坐标 (Nominatim 2.4% 成功率) | ✅ NYC Open Data 匹配 93 + 删 3 Bronx + CSV 更新 | 2026-06-11 |