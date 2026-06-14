# ClearPath — 领域术语表

> 由 grill-with-docs 会话生成，2026-06-09

---

## 设计原则

**最小化功能实现，先跑通。** 不过度设计，不提前优化。ENUM/JSON/字段数量保持最小集，后续测试有问题再扩展。

---

## 已冻结决策（2026-06-09）

| # | 决策项 | 结论 | 理由 |
|---|-------|------|------|
| D1 | 认证方式 | 邮箱+密码（bcrypt） | 需求文档明确要求，No OAuth |
| D2 | Guest 模式 | 无 token = Guest | "No Account Required" 被动访问 |
| D3 | 匿名报告 | 提交后匿名化，保留 `anonymous` 字段 | 数据库有记录，前端隐藏 |
| D4 | 拥挤度等级 | **四级** `quiet/moderate/busy/no_data` | 统一 DB 与 OpenAPI，`no_data` 映射 🔵 Blue (F-06) |
| D5 | 报告类别 | OpenAPI 8 个 issue_type 值 | 产品负责人冻结 |
| D6 | 确认操作 | 覆盖旧 action，`UNIQUE (report_id, user_id)` | 互斥状态，只保留最新 |
| D7 | `auth_subject` | 不需要 | 邮箱即认证标识 |
| D8 | 报告类别存储 | 字典表 `report_categories` | 按场馆类型过滤类别 |
| D9 | RAG embedding 存储 | MySQL JSON/BLOB | 零额外成本，~3500 条场馆数据量足够 |
| D10 | 医疗数据边界 | 云端加密存储（AES-256-GCM）+ 本地无独立副本 | Web 医疗護照列印需求要求服务端可读取医疗数据 |

---

## 待决策（Remaining）

_所有 10 项产品决策已冻结（2026-06-09），D10 于同日修订为云端加密存储方案。_

## 认证域

| 术语 | 定义 |
|------|------|
| **user_id** | 系统内部 UUID v4（36字符），所有业务表的 FK，由后端生成 |
| **email** | 用户登录标识，小写规范化，UNIQUE 约束 |
| **password_hash** | bcrypt 哈希存储的密码，永不存明文 |
| **JWT** | 认证 token，payload 包含 `{ user_id, email, exp }`，由 Flask-JWT-Extended 签发 |
| **Guest** | 无 token 访问，被动浏览，无写权限（无 `Authorization` header） |
| **Authenticated** | 带有效 JWT token，可提交报告、收藏、通知 |

## 报告域

| 术语 | 定义 |
|------|------|
| **anonymous** | 报告字段，`TRUE` = 前端隐藏提交者信息，数据库仍存 `user_id` |
| **匿名报告** | 提交后匿名化（不是提交时匿名），需登录才能提交 |
| **report_id** | 报告唯一标识，VARCHAR(36) |
| **issue_type** | 报告问题类型 ENUM，8 个值：`elevator_broken`, `wheelchair_lift_broken`, `toilet_out_of_order`, `large_crowd`, `protest_or_blockage`, `entrance_closed`, `ramp_blocked`, `closed_early` |
| **expires_at** | 报告自动过期时间，默认创建后 2 小时 |
| **confirmation action** | 用户确认操作 ENUM：`still_here` / `resolved` / `not_sure` / `still_out_of_order` / `open_now` |
| **确认覆盖规则** | 同一用户对同一报告只保留最新 action，`UNIQUE (report_id, user_id)` + `ON DUPLICATE KEY UPDATE` |

## 拥挤度域

| 术语 | 定义 |
|------|------|
| **busyness_scores** | 实时观测（当前时刻拥挤度），保留 `forecast_1h` |
| **busyness_forecasts** | 未来 12h 时序预测（ML pipeline 写入） |
| **level** | 拥挤度等级，**四级统一**：`quiet` / `moderate` / `busy` / `no_data` |
| **quiet** | 🟢 Green，容量负载 < 30% |
| **moderate** | 🟡 Yellow，容量负载 30%–70% |
| **busy** | 🔴 Red，容量负载 > 70% |
| **no_data** | 🔵 Blue，无实时数据（未来预测模式或实时数据离线），F-06 要求 |

## 场馆域

| 术语 | 定义 |
|------|------|
| **venue** | 统一 POI 表，包含卫生间、医疗、AED 等所有设施 |
| **venue_type** | 设施类型 ENUM（API 和 DB 统一用此字段，不用 `category`） |
| **district** | 曼哈顿行政区划，小写枚举如 `midtown_east` |
