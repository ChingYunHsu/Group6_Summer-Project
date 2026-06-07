# Sprint Pipeline 需求总结

## 来源文档
- `Backend Lead Pipeline.docx` — Emmett, 后端 Sprint 2-4 任务
- `Data Lead Pipeline.docx` — 数据团队 Sprint 2-4 任务

## Sprint 2：数据库分区 + 认证 + Profile

### Backend
- Flask Blueprints 模块化（✅ 已实现）
- MySQL 表 + 连接池（✅ 13 张表）
- JWT 认证网关：`/auth/register`, `/auth/login`, `/auth/guest`
- Profile & Medical ID CRUD：`/api/v1/profile` GET/PUT
- PyTest 单元测试

### Data
- ERD + Schema 更新（✅ 已完成）
- **行政区分区（District Zoning）：`district` 列 — ⚠️ 未实现，最高优先级**
  - 分区：Uptown, Midtown East, Midtown West, Downtown
  - 需要覆盖：venues, busyness_scores, emergency_assets
- 数据导入（✅ ETL 已完成）
- Mock 数据（✅ mock_data.py 已有）
- 历史数据导入 + ARIMA/LSTM 模型初始化

## Sprint 3：空间查询 + 报告 + ML 生产

### Backend
- 地图查询引擎：`/api/v1/map/venues` 支持 district/language/wheelchair 过滤
- 5 分钟缓存窗口（busyness 查询）
- 报告引擎 Path A（venue 绑定）/ Path B（纯 GPS 独立表）
- **2 小时 TTL**：报告自动过期，Celery/Redis 后台清理
- Push 通知（报告解决时推送）
- SOS Webhook：`/api/v1/emergency/sos` 5 秒长按紧急信号

### Data
- 实时遥测管道（外部数据源 → 实时等待时间/负载）
- ML 模型：12 小时单设施时间序列预测（ARIMA/LSTM）
- 报告 Path A/B 数据路由（与 Backend 对齐）
- **区域聚合公式**：
  - Real-Time Density Card：区域聚合容量百分比
  - Best Travel Window Card：区域历史最低拥挤谷值
  - Fastest Hubs Leaderboard：Cost = Wait Time + Transit

## Sprint 4：账户删除 + Gemini RAG + 集成

### Backend
- 级联删除 API：`DELETE /api/v1/account` 清除所有关联数据
- JWT 失效 + 前端强制清理本地存储
- Gemini RAG 集成（AI 聊天机器人路由）
- Rate-limiting + Swagger/Postman 文档

### Data
- 多语言 RAG 管道：向量嵌入 + Gemini API
- 跨语言意图识别（中文/法语查询）
- E2E 集成 + Code Freeze

## 🔴 关键 Gap：District Zoning

两份文档共同最高优先级：**从第一天起需要 `district` 列**

| 分区 | 覆盖表 |
|------|--------|
| Uptown | venues, busyness_scores, emergency_assets |
| Midtown East | 同上 |
| Midtown West | 同上 |
| Downtown | 同上 |

当前数据库无 `district` 列，是 Sprint 2/3 所有聚合查询的前置条件。

## 项目当前状态

| 已完成 | 待实现 |
|--------|--------|
| ✅ 13 张表 Schema | ❌ JWT 认证 |
| ✅ ETL 数据导入 | ❌ Profile CRUD |
| ✅ Mock 数据 | ❌ 实时遥测管道 |
| ✅ Weather API 集成 | ❌ 12 小时 ML 预测 |
| ✅ Venue Language ETL | ❌ 报告 TTL (2h) |
| ✅ Schema 同步机制 | ❌ SOS Webhook |
| ✅ **District Zoning**（venues + ramps） | ❌ 级联删除 API |
| ✅ emergency_assets 唯一约束 | ❌ Gemini RAG |
