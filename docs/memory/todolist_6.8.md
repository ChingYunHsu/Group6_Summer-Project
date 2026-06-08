
# ClearPath 数据库修改任务清单 (2026-06-08)

> 来源：`final-requirements-database-impact.md`、`openapi-vs-schema-gap.md`、`pipeline-requirements.md`

---

## Phase 1: 基础同步与决策冻结

- [ ] 同步两份 `001_clearpath_schema.sql`（docker/mysql/init/ ↔ Data+ML/test/6.2-6.5_DB/）
- [ ] 冻结 5 项产品决策（报告是否必须登录、报告类别最终集合、四级拥挤度第四级含义、医疗数据是否绝不云同步、RAG embedding 存储位置）

## Phase 2: 用户与账户表

- [ ] 新建 `users` 表（user_id, auth_subject, email, display_name, preferred_language, account_status, deleted_at）
- [ ] 新建 `user_favorite_venues` 表（user_id, venue_id, 联合主键 + FK CASCADE）
- [ ] 新建 `notification_preferences` 表（user_id, venue_id, notification_type, quiet_start/end）
- [ ] 更新 OpenAPI：移除 `GET /api/v1/user/medical-id` 和 `GET /api/v1/user/emergency-contacts`
- [ ] `UserProfile` schema 仅保留账户显示字段（user_id, account_state, full_name, email, preferred_language）

## Phase 3: 报告系统改造

- [ ] `user_reports` 新增 `user_id VARCHAR(36) NOT NULL` + FK → users
- [ ] `user_reports` 删除 `anonymous` 和 `reported_by` 列
- [ ] `report_confirmations` 新增 `user_id` + 唯一约束 `(report_id, user_id)`
- [ ] 报告类别从 ENUM 迁移为 `report_categories` 字典表
- [ ] OpenAPI 报告端点添加 `security: [BearerAuth]`

## Phase 4: 拥挤度预测

- [ ] 新建 `busyness_forecasts` 表（venue_id, forecast_for, predicted_score, predicted_level, model_version）
- [ ] 停止将单值 `forecast_1h` 伪造为 12h 数组
- [ ] 确认四级拥挤度命名统一（Schema `low/medium/high` ↔ API `quiet/moderate/busy` ↔ Final UI）
- [ ] OpenAPI: 统一 Venue `phone_number` → `phone`

## Phase 5: RAG 数据层

- [ ] 为 `venues(latitude, longitude)`、`venue_type`、`district` 建立合适索引
- [ ] 生成可检索的场馆文档投影（含语言、无障碍、营业、警告、实时拥挤度）
- [ ] 确定 embedding 存储方案（MySQL JSON/BLOB vs 外部向量库）
- [ ] 不创建服务端 `chat_history` 表（Final 要求聊天历史仅客户端）

## Phase 6: OpenAPI 与验证

- [ ] 添加 `POST /user/sos` 端点（US-10 Must Have）
- [ ] 添加 `GET/PUT /user/notification-preferences` 端点
- [ ] 添加 `DELETE /api/v1/account` 级联删除端点
- [ ] 更新 mock_data.py 对齐新 schema
- [ ] 更新 ETL notebook 验证新表结构
- [ ] 级联删除测试（删除用户 → 收藏、通知、报告一并清除）
- [ ] 第二次 ETL 幂等性验证（不产生重复行）

---

## 🔴 已知冲突（需团队讨论）

| 议题 | openapi-vs-schema-gap | openapi_gap_finalacceptcriteria |
|------|----------------------|-------------------------------|
| Medical ID 端点 | 删除（隐私边界） | 添加（US-10 Must Have） |

## ✅ 已解决的冲突

| 议题 | 结论 |
|------|------|
| 12h 预测表结构 | 统一为独立 `busyness_forecasts` 表（JSON 列方案已否决） |

## 📋 Pipeline 附加快速任务

- [ ] Docker schema 与 test schema 一致性检查
- [ ] `busyness_scores` 表数据源确认（当前 0 行）
- [ ] MySQL 5.7 COMMENT 语法兼容性检查
