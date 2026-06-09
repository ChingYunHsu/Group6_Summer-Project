# ClearPath 现有问题

> 更新日期：2026-06-09

---

## 🔴 P0 — 阻塞性问题

### 1. users 表缺失 — 无法认证
- **影响**: JWT 认证、报告登录、收藏同步全部依赖 users 表
- **状态**: 未开始
- **详见**: `execution-plan.md` Phase 2

### 2. user_reports / report_confirmations 缺 user_id — 违反 Final 隐私要求
- **影响**: 无法防重复投票、无法执行级联删除、无法追踪报告来源
- **Final 要求**: "Login Required: must be logged in to submit or verify reports"
- **当前 Schema**: `anonymous BOOLEAN` + `reported_by VARCHAR(50)`, 无 user_id FK
- **状态**: 未开始
- **详见**: `execution-plan.md` Phase 3

### 3. busyness_forecasts 表缺失 — 12h 预测无数据源
- **影响**: `GET /venues/{id}/busyness/forecast` 返回假数据
- **OpenAPI**: 定义了 12 元素数组 `[{offset_hours, percent, level}]`
- **当前 DB**: 仅有 `busyness_scores.forecast_1h` (单值 INT)
- **状态**: 未开始
- **详见**: `execution-plan.md` Phase 4

---

## ⚠️ P1 — 对齐问题

### 4. mock_data.py 两处缺口

| 项目 | mock_data.py | OpenAPI v1.4.0 | 状态 |
|------|-------------|----------------|------|
| `REPORT_CONFIRMATION_TEMPLATE` | 缺 `user_id` | `user_id` 为 required field | ⚠️ Gap |
| `INSIGHTS_DASHBOARD.district` | `"Midtown East"` (title case) | enum lowercase `midtown_east` | ⚠️ Mismatch |

### 5. 四级拥挤度命名不统一

| 层级 | DB ENUM | OpenAPI | Final UI |
|------|---------|---------|----------|
| 低 | `low` | `quiet` | Quiet |
| 中 | `medium` | `moderate` | Moderate |
| 高 | `high` | `busy` | Busy |
| 第四级 | `unknown` | ❌ 无 | ❌ 无 |

**需确认**: 第四级是 `very_high` 还是仅表示"无数据"？

### 6. 报告类别集合不匹配

| OpenAPI (8 values) | Final 要求 | 状态 |
|-------------------|-----------|------|
| `elevator_broken` | `elevator_broken` | ✅ |
| `wheelchair_lift_broken` | — | 需确认 |
| `toilet_out_of_order` | — | 需确认 |
| `large_crowd` | `long_wait_time` | ⚠️ 语义不同 |
| `protest_or_blockage` | `ramp_blocked` | ❌ 缺失 |
| `entrance_closed` | `closed_early` | ⚠️ 可能重叠 |
| `ramp_blocked` | — | 已补 ✅ |
| `closed_early` | — | 已补 ✅ |

**建议**: 产品负责人冻结最终类别集合，考虑迁移到 `report_categories` 字典表。

### 7. Docker schema 与 test schema 不同步
- `docker/mysql/init/001_clearpath_schema.sql` ≠ `Data+ML/test/6.2-6.5_DB/001_clearpath_schema.sql`
- 必须先确认目标环境再同步，禁止无判断覆盖

---

## 📋 P2 — 待确认事项

### 8. 医疗数据边界
- Final: 严格本地存储 (AsyncStorage/SQLite)
- 服务器 Profile 只保留账户显示字段
- Medical ID / Emergency Contacts 由客户端本地 API 处理
- **已确认**: OpenAPI 已移除 medical-id 和 emergency-contacts 端点

### 9. RAG 数据层选型
- embedding 存储: MySQL JSON/BLOB vs 外部向量库
- 不创建服务端 `chat_history` 表 (Final 要求聊天历史仅客户端)
- 需要为 venues 建立合适的过滤索引

### 10. busyness_scores 表 0 行
- API 端点已定义 (v1.4.0), 但无实际数据源
- 需确认数据来源: BestTime API / MTA / 手动

---

## 已解决的问题

| 问题 | 解决方式 |
|------|---------|
| `phone_number` vs `phone` | OpenAPI 已统一为 `phone` |
| forecast_4h/8h 残留字段 | 已从 VenueBusyness schema 移除 |
| Medical ID 端点 | 已从 OpenAPI 移除 (device-local) |
| 12h 预测结构 | 独立 `busyness_forecasts` 表方案确定 |
| issue_type 缺 2 值 | 已补 `ramp_blocked` + `closed_early` |
| GET /reports 无过滤 | 已加 `venue_id`, `issue_type`, `status` |
| Report.status 缺 expired | 已加 |
| Insights tag 错误 | 已改为 `Insights` tag |
| Favourites CRUD | 已加 POST + DELETE |
| Account Delete | 已加 DELETE 端点 |
| Chatbot RAG | 已加 POST 端点 |
| Medical Passport PDF | 已加 GET 端点 |
| RouteOption per-mode | 已加 `summary_by_mode` |
