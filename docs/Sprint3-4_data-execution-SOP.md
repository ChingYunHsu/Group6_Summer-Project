# Sprint 3–4 Data 下一步执行 SOP

> 目的：按依赖顺序关闭 Data 相关敞口。除非前一阶段的验收证据已记录，否则不得进入下一阶段或宣称可上线。

## 实施状态（2026-07-10）

| 工作项 | 状态 | 已交付 / 剩余 gate |
| --- | --- | --- |
| Stage 0 contract baseline | 已完成 | `Data+ML/test/7.6-7.11/sprint3-4_canonical_contract_baseline.md` 记录 canonical 表名、9 个 report category 与新/旧 volume 观察结果。 |
| O14 report category 运维入口 | 已完成（代码） | `docker/mysql/scripts/ensure_report_categories.sh --apply` 可对既有 volume 幂等补种并验证 9 项；真实部署执行记录仍需附到发布单。 |
| O1 telemetry worker framework | 已完成（代码） | Compose `telemetry` profile、HTTP feed、超时、有限重试与 fail-fast 已实现；真实 source URL、token、字段映射和失败演练尚未提供。 |
| O4 fallback policy | 已冻结，待跨端落地 | mock 仅限开发环境；生产/演示必须显式 degraded/no-data。Backend/Frontend 仍需统一 response schema。 |
| O6/O7/O8 Backend P0 | 已交接，未关闭 | medical route/schema、chatbot route-level privacy coverage 和 fallback contract 由 Backend owner 实施，详见 `docs/backend-p0-handoff.md`。 |

已验证：17 个 telemetry/seed 离线测试通过；worker Python、运维 shell 和默认/telemetry Compose 配置检查通过。真实 DB execute integration 与真实 feed 演练不在本次验证范围内。

## 范围与完成定义

本 SOP 覆盖执行计划中的 O1、O4、O6/O7、O8，以及数据一致性相关的 O14–O18。

完成的定义不是“代码已写”，而是：schema、seed、DB-backed API、mock/fallback 行为、前端消费契约和自动化验证一致；生产/演示路径有可复跑的证据。

## 0. 已完成：冻结基线

**Owner：Data（协调）+ Backend + Ops**

1. 从当前主分支建立执行分支；记录 commit SHA、compose/MySQL 版本和现有 DB volume 状态（新 volume / 既有 volume）。
2. 列出本轮 canonical contract：
   - medical profile 表名；
   - report category 的 9 个有效值；
   - venue type 枚举及 `restroom` / AED 口径；
   - insights 与 reports 的 fallback 响应字段。
3. 对新、旧两个 DB volume 分别运行 schema/seed smoke check，并保留输出。
4. 任何 DB 写入错误必须可见地失败；先禁止“写入失败后静默返回 mock 成功”的路径。

**退出门槛：** 有一份固定的 contract 清单，以及新/旧 volume 的基线结果。未完成则不开始 telemetry 和 chatbot 的端到端验证。

## 1. 部分完成：收敛 schema 与数据种子（O8、O14–O16）

**Owner：Data + Backend；Ops 参与 O14**

1. 选定唯一的 medical profile canonical 表名（建议沿用 DDL 中的 `medical_profiles`）。同步修改：DDL、ORM/SQL、OpenAPI、fixture、cascade-delete 和 RAG forbidden-source allowlist。
2. 确认同一路径只存在一套 medical-profile route；route 字段必须与最终 DDL 对齐。
3. 将 `report_categories` seed 变成对旧 volume 可重复执行的迁移/部署步骤；部署前后都检查记录数与 9 个 category 的内容。
4. 将 report 的 API validation、mock data、seed 和 OpenAPI 统一到相同 9 个有效 category；移除 unknown label。
5. 将 `VALID_VENUE_TYPES`、DB enum、venue seed、mock data 和前端 filter 对齐；明确 `restroom` 与 AED 是否为 venue type 或属性。

**验收：**

- 新/旧 volume 都能完成迁移与 seed，且 `report_categories` 完整；
- medical-profile GET/PUT/DELETE contract tests 通过，且没有 duplicate route；
- 9 个 report category 都可提交和返回 label；
- venue 枚举在 API、DB、seed、mock、客户端一致。

**停止条件：** 任一 canonical 名称或枚举未定时，不合并跨层改动；先记录决策，再继续。

## 2. 策略已冻结：fallback 与响应标记（O4、O17、O18）

**Owner：Data + Backend + Frontend**

1. 决定 demo 策略：`mock_data.INSIGHTS_DASHBOARD` 仅可用于 dev/DB unavailable，或完全禁止；不能保留隐式判断。
2. 固定 insights/reports 的响应 schema，显式返回数据来源与降级信息（至少 `data_mode`；需要时补 `formula_version`、`fallback_reason`）。
3. 无数据时返回 `no_data` 或 partial payload；不允许以未标记的固定 mock 常量伪装真实数据。
4. 固定 venue list 与 busyness 的分层：`GET /venues` 不 inline busyness，客户端只通过独立 busyness/realtime endpoint 消费容量数据。

**验收：** DB 可用、DB 不可用和空数据三种场景的 response schema 完全一致；前端仅依赖 frozen schema；contract tests 覆盖三种场景。

## 3. 框架已完成：落地真实 telemetry 生产路径（O1）

**Owner：Data + Ops**

1. 记录并批准真实 feed source（供应方、字段映射、刷新频率、可用性/限流假设）。未批准时只能标记为非生产能力。
2. 将 `run_live_telemetry.py --execute` 包进受控 scheduler/worker：单实例保护、超时、重试、失败告警和审计日志。
3. 在隔离环境先运行一次完整写入；验证依赖表、seed、audit log、写入行数和幂等性。
4. 部署后通过 `/api/v1/realtime/map-updates` 验证新记录可被读取，且 `model_version='live-telemetry-v1'`。
5. 人为注入一次 source/DB 失败，验证重试、告警和 API 降级标记；不得产生静默陈旧数据。

**验收：** 有一条可复跑调度记录、一次成功 refresh、一次失败演练，以及 endpoint 读取到本轮新数据的证据。

## 4. Backend 交接：锁住 RAG 数据边界（O6/O7）

**Owner：Backend；Data 提供 allowlist 与回归样本**

1. Backend chatbot route 使用最终 schema/allowlist 进行 retrieval；medical profile 数据不得进入检索或 prompt assembly。
2. 为 route 增加回归测试：forbidden source、medical-advice refusal、Gemini timeout/retry、错误响应、language preservation。
3. 用审计日志或 test double 确认实际 retrieval SQL/检索结果只来自允许的数据源。

**验收：** 全部上述测试通过；测试能证明 medical source 未被访问，而不只是最终回答看似安全。

## 5. 发布前联合 gate

**Owner：Data（签字）+ Backend + Frontend + Ops**

按以下顺序执行，任一失败即回到对应阶段修复：

1. 新/旧 volume migration + seed smoke check；
2. API contract suite（medical profile、reports、venues、insights、realtime）；
3. fallback/empty-data matrix；
4. telemetry 成功 refresh 与失败演练；
5. chatbot privacy regression；
6. 前端 demo 冒烟：只消费 frozen contract，明显展示 `data_mode`/无数据状态。

发布记录至少包含：执行 commit、环境、迁移版本、feed source 版本、测试结果、失败演练结果和遗留项（若有）。任何未通过的 P0 都必须在 demo/release note 中明确标为未交付，不能以 mock 成功替代。

## 建议提交顺序

1. `data: canonicalize medical profile schema and fixtures`
2. `data: make report category seed repeatable and align enums`
3. `data: freeze venue/report/insights contracts and explicit fallback metadata`
4. `ops: schedule telemetry refresh with audit, retry and alerting`
5. `backend: lock chatbot retrieval privacy boundary with route tests`
6. `test: add cross-volume and cross-contract release gates`

## 证据清单

- [x] canonical contract 决策记录
- [x] 新/旧 DB volume baseline 输出
- [x] schema/seed contract 与 telemetry 离线测试结果（17 passed）
- [x] telemetry worker / shell / Compose 静态配置检查
- [ ] fallback/empty-data matrix 结果
- [ ] telemetry 成功与失败演练日志
- [ ] chatbot forbidden-source 回归结果
- [ ] 前端 demo 冒烟证据
