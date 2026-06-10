# ClearPath 现有问题

> 更新日期：2026-06-09 | 与 openapi_gap_finalacceptcriteria.md 对齐

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

---

## ⚠️ P1 — 对齐问题

### 4. mock_data.py 两处缺口

| 项目 | mock_data.py | OpenAPI v1.4.0 | 状态 |
|------|-------------|----------------|------|
| `REPORT_CONFIRMATION_TEMPLATE` | ✅ 已加 `user_id` | `user_id` 为 required field | ✅ 已修复 2026-06-09 |
| `INSIGHTS_DASHBOARD.district` | ✅ 已改为 `"midtown_east"` | enum lowercase `midtown_east` | ✅ 已修复（风格一致性）2026-06-09 |

### 5. 拥挤度命名 — 已冻结 (D4)
- **四级统一**: `quiet` / `moderate` / `busy` / `no_data`
- `busyness_scores.level` 使用 ENUM，`no_data` = 🔵 Blue (F-06: No Live Info)
- **状态**: ✅ 已执行 ALTER TABLE 2026-06-09

### 6. 报告 issue_type — 已冻结 (D5 + D8)
- OpenAPI 8 个值确认
- 使用字典表 `report_categories` (按场馆类型过滤)
- **状态**: ✅ 已建表 + ALTER user_reports 2026-06-09

### 7. Docker schema 与 test schema 不同步
- `docker/mysql/init/001_clearpath_schema.sql` ≠ `Data+ML/test/6.2-6.5_DB/001_clearpath_schema.sql`
- **状态**: ✅ 已同步 2026-06-09

---

## 📋 P2 — 待确认事项

### 8. 医疗数据边界 — 已冻结 (D10) — 修订 2026-06-09
- ~~Final: 严格本地存储 (AsyncStorage/SQLite)~~
- **新方案**: 云端加密存储（AES-256-GCM），传输 + 静态双层加密
- **加密方式**: Per-user 密钥（PBKDF2 from password + 服务端 salt）
- **保留端点**: GET/PUT `/api/v1/profile`（含加密医学字段）
- **新增端点**: GET/PUT `/api/v1/user/medical-id`、`/api/v1/user/emergency-contacts`（加密读写）
- **变更原因**: Web 端 Medical Passport PDF 列印功能需要服务端可读取医疗数据
- **已恢复**: OpenAPI 需重新加入 medical-id 和 emergency-contacts 端点

### 9. RAG 数据层 — 已冻结 (D9)
- embedding 存储: MySQL JSON/BLOB（~3500 条场馆数据量足够）
- 不创建服务端 `chat_history` 表 (Final 要求聊天历史仅客户端)
- ~~需建 `venue_embeddings` 表~~ ✅ 已创建 (Phase 5, 2026-06-09)
- **状态**: 表结构就绪，数据填充待后端实现 embedding 生成

### 10. busyness_scores 表 0 行
- API 端点已定义 (v1.4.0), 但无实际数据源
- ~~需确认数据来源~~ ✅ 表结构已就绪 (Phase 4: ENUM 改为 quiet/moderate/busy/no_data)
- **busyness_forecasts 表**: ✅ 已创建 (Phase 4, 2026-06-09)
- **状态**: 表结构就绪，数据填充待 ML pipeline (BestTime API / MTA / 手动)

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
| 11 | Chatbot RAG | 已加 POST 端点 | openapi_gap (#2) |
| 12 | Medical Passport PDF | 已加 GET 端点 | openapi_gap (#5) |
| 13 | RouteOption per-mode | 已加 `summary_by_mode` | openapi_gap (#13) |
| 14 | category vs venue_type | 无冲突，API 层映射 | openapi_gap (1.1) |
| 15 | weather_risk 列 | 已在 DB 中存在 | session 2026-06-06 |
| 16 | District Zoning | venues + pedestrian_ramps 已实现 | session 2026-06-09 |
| 17 | emergency_assets 重复写入 | 已加唯一约束 | session 2026-06-06 |
| 18 | P0 #1 users 表缺失 | ✅ 已创建 users 表 (Phase 2) | session 2026-06-09 |
| 19 | P0 #2 user_reports/report_confirmations 缺 user_id | ✅ 已 ALTER TABLE (Phase 3) | session 2026-06-09 |
| 20 | P0 #3 busyness_forecasts 表缺失 | ✅ 已创建表 (Phase 4) | session 2026-06-09 |
| 21 | Phase 5 venue_embeddings + 索引 | ✅ 已创建表 + indexes (Phase 5) | session 2026-06-09 |
| 22 | mock_data.py 两处缺口 | ✅ 已修复 (Phase 6) | session 2026-06-09 |
