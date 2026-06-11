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
