# ClearPath 现有问题

> 更新日期：2026-06-10 | Commit: b73309c DQR build | 来源：代码审查 + 评审验证
> 评审日期：2026-06-10 | 评审方法：逐项验证代码/Schema 实际内容

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

### 4. ❌ venues 表缺少 district 列 — Docker vs Data+ML schema 不同步 (b73309c) — 新增 2026-06-10
- **文件**: `docker/mysql/init/001_clearpath_schema.sql:379-380`
- **影响**: Docker schema 的 venues 表（第 14-46 行）使用 `borough` 而非 `district`，但 `idx_venues_district` 索引（第 379 行）和 `idx_venues_type_district`（第 380 行）引用 `venues(district)` — 该列在 Docker schema 中不存在。Data+ML schema 的 venues 表（第 239 行）包含 `district` 列，但两个 schema 未同步。
- **状态**: ❌ 未解决
- **失败场景**: MySQL 抛出 ERROR 1054 ('Unknown column district in venues')，idx_venues_district 或 idx_venues_type_district 索引创建失败。这些索引静默失效，导致场馆类型+区域查询全表扫描。
- **修复**: 将 Docker schema 的索引改为 `venues(borough)`，或在 Docker schema 的 venues 表中添加 `district` 列（与 Data+ML schema 对齐）。

### 5. ❌ MEDICAL_ID / EMERGENCY_CONTACTS 幻影导入 (b73309c) — 新增 2026-06-10
- **文件**: `src/api/user.py:6`
- **影响**: user.py 从 mock_data 导入 MEDICAL_ID 和 EMERGENCY_CONTACTS，但两者在 mock_data.py (783行) 中均未定义
- **状态**: ❌ 未解决
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

### 11. ❌ Mock 数据 status/expires_at 矛盾 (b73309c) — 新增 2026-06-10
- **文件**: `src/mock_data.py:450`
- **影响**: 报告 r_505, r_506, r_507 的 status='active'，但 expires_at 时间戳已在过去 (2026-05-29 和 2026-05-30)，远早于当前日期 2026-06-10
- **状态**: ❌ 未解决
- **失败场景**: 任何按 'WHERE status = active AND expires_at > NOW()' 过滤报告的端点或测试返回 0 行。期望看到活跃报告的 UI 测试将失败。不一致性使模拟数据对测试过期逻辑不可靠。
- **修复**: 更新 expires_at 日期到未来，或将 status 改为 'expired'。

### 12. ❌ confirm_report KeyError (b73309c) — 新增 2026-06-10，修正 2026-06-100
- **文件**: `src/api/reports.py:114`
- **影响**: `confirm_report()` 访问 `report['confirmation_count']`（顶层 key），但所有 mock 数据（r_501-r_507）使用嵌套 `confirmations.count` 结构，无顶层 `confirmation_count`
- **状态**: ❌ 未解决
- **严重程度**: ⚠️ 仅影响通过 API 调用 `POST /reports/{id}/confirmations` 路径。Mock 数据中的 reports 是独立副本（非全局引用），直接读取 mock 数据不受影响。
- **失败场景**: `POST /api/v1/reports/r_505/confirmations` 带 `action='still_here'` → `KeyError: 'confirmation_count'` → 返回 500。
- **修复**: 更新 `confirm_report()` 处理嵌套 `confirmations.count` 结构，或更新 mock data 使用顶层 `confirmation_count` key。

---

## 📋 P2 — 待确认事项

### 13. ~~医疗数据边界 — 已冻结 (D10)~~ ✅ 已解决 2026-06-09
- **状态**: ✅ 已确定云端加密存储方案

### 14. ~~RAG 数据层 — 已冻结 (D9)~~ ✅ 已解决 2026-06-09
- **状态**: ✅ 已创建 venue_embeddings 表

### 15. ~~busyness_scores 表 0 行~~ ✅ 已解决 2026-06-09
- **状态**: ✅ 表结构就绪，待 ML pipeline 填充数据

### 16. ❌ DQR 管道 O(N²) 效率问题 (b73309c) — 新增 2026-06-10
- **文件**: `Data+ML/test/6.8-6.12_DB/dqr_cleaning_pipeline.ipynb:23`
- **影响**: detect_gps_duplicates() 函数进行 O(N²) 成对 haversine 比较，无空间预过滤
- **状态**: ❌ 未解决
- **失败场景**: 4,841 个场馆 + 23,625 个 pedestrian_ramps = ~114M 次 haversine_m() 调用。纯 Python 的三角函数操作导致函数运行极慢（~几分钟），占整个 DQR 管道的主要计算成本，生产数据集不可行。
- **修复**: 添加空间索引预过滤（如 geohash 网格），或使用 KD-tree/Ball-tree 加速邻近点查询。

### 17. ❌ dqr_utils.py 代码重复 (b73309c) — 新增 2026-06-10
- **文件**: `Data+ML/test/6.2-6.5_DB/dqr_utils.py` 和 `Data+ML/test/6.8-6.12_DB/dqr_utils.py`
- **影响**: 两个目录中的 dqr_utils.py 文件完全相同（82行），导致维护困难
- **状态**: ❌ 未解决
- **失败场景**: 在一个目录中修复 bug 不会自动传播到另一个。隐藏的依赖漂移风险。未来 Sprint 添加新函数时，容易遗漏同步。
- **修复**: 移除重复，确保所有目录引用单一共享的 dqr_utils.py（通过 sys.path 或相对导入）。

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
| 20 | ~~D10 医疗数据边界~~ | ~~严格本地存储, 不云同步~~ → D10 修订: 云端加密存储 (AES-256-GCM) | grill-with-docs 2026-06-09 → 修订 2026-06-09 |
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