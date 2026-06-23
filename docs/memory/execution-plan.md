# ClearPath 执行计划 (DB Schema 重点)

> 更新日期：2026-06-23 | 审计: 与 openapi_gap_finalacceptcriteria.md 对齐 + Sprint 3 数据任务归属整理
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
| D10 | 医疗数据边界 | **严格数据分层**: Tier 1 Profile Group 云端同步(Read-Only/Editable); Tier 2 Medical ID 100%本地 Mobile Only; F-14 QR-P2P打印 (2026-06-15 修订) |

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

- [x] 新建 `users` 表 — 2026-06-09
- [x] 新建 `user_favorite_venues` 表 — 2026-06-09
- [x] 新建 `notification_preferences` 表 — 2026-06-09

---

## Phase 3: 报告系统改造

**目标**: 绑定认证用户, 防重复投票, 按场馆类型过滤类别

- [x] 改造 `user_reports` — 2026-06-09
- [x] 改造 `report_confirmations` — 2026-06-09
- [x] 新建 `report_categories` 字典表 (D8: 按场馆类型过滤) — 2026-06-09

---

## Phase 4: 拥挤度预测

**目标**: 支持 12 小时预测图表

- [x] 新建 `busyness_forecasts` 表 (D4 + D9) — 2026-06-09

---

## Phase 5: RAG 数据层

**目标**: 支持 Gemini RAG 查询

- [x] 为 `venues(latitude, longitude)`、`venue_type`、`district` 建立索引 — 2026-06-09
- [ ] 生成可检索的场馆文档投影 (含语言、无障碍、营业、警告、实时拥挤度) — 待后端实现
- [x] embedding 存储方案确定: MySQL JSON/BLOB (D9) — ~3500 条数据量足够
- [x] 创建 `venue_embeddings` 表 — 2026-06-09
- [x] 确认不创建服务端 `chat_history` 表 (Final 要求聊天历史仅客户端)

---

## Phase 6: OpenAPI 与验证

**目标**: 确保 API 与 DB 一致

- [x] 更新 mock_data.py: `REPORT_CONFIRMATION_TEMPLATE` 加 `user_id` (openapi_gap #9)
- [x] 更新 mock_data.py: `INSIGHTS_DASHBOARD.district` 改为 lowercase `midtown_east`
- [x] 更新 ETL notebook 验证新表结构
- [x] 级联删除测试 (删除用户 → 收藏、通知、报告一并清除)
- [x] 第二次 ETL 幂等性验证 (不产生重复行)
- [x] 同步 Docker schema (test → docker/mysql/init/)
- [x] MySQL 5.7 COMMENT 语法兼容性检查 — 无 COMMENT 语法问题

---

## Sprint 2 数据任务 (fangxun.wu)

**目标**: 完成数据库 ERD 修订、数据摄取、模拟数据和 ML 模型初始化  
**总工时**: Est. 46h

| # | Task | Week | Description | Status | Est. (h) |
|---|------|------|-------------|:------:|:--------:|
| D2.1 | ERD Revision, Schema Updates & District Zoning Setup | Week 4 | ERD update + 4 district nodes | ✅ 2026-06-09 | 5 |
| D2.2 | MySQL Table Implementation & Index Tuning | Week 4 | DDL scripts + FK constraints + composite indexes | ✅ 2026-06-09 | 5 |
| D2.3 | Data Parsing & Ingestion | Week 5 | ETL: 349 restrooms, 900 healthcare, 431 NYS, 3,279 AEDs, 63 LASS | ✅ 2026-06-05 | 10 |
| D2.5 | Zoned Historical Ingestion & ML Model Init (Advance Start) | Week 5 | [High Priority] traffic_hourly.csv fetched; ARIMA/LSTM pending | ⏳ 进行中 | 10 |
| D2.6 | Data Deduplication & Multi-Source Cleansing Preprocessing | Week 5 | GPS duplicate detection (grid+haversine, lat-scaled) | ✅ 2026-06-11 | 10 |
| D2.7 | Database Integrity, Privacy & Constraint Unit Testing | Week 5 | PyTest: 100% venues non-Null district; 12 test cases | ✅ 2026-06-11 | — |

### DQR Pipeline 重构 (2026-06-11)

- 6 个共享模块 in `Data+ML/test/shared/` (dqr_utils, dqr_io, dqr_checks, dqr_analysis, dqr_cleaning, external_ingestion)
- Notebook: 21 cells, 218 code lines (from 40 cells, 406 lines)
- Output moved to `output/` subdirectory
- All imports consolidated in Cell 2
- pytest: 12 tests pass (D2.7, GPS grid, export overwrite, import path, clean_venues immutability)

### Park Toilet GPS Fix (2026-06-11)

- 124 zero-coordinate restroom venues fixed using NYC Open Data (`i7jb-7jku`)
- 93 Manhattan-trusted matches written to DB
- 3 Bronx Jackie Robinson Park entries deleted (wrong Borough)
- CSV `Directory_Of_Toilets_In_Public_Parks_20260526.csv` updated: +Latitude/Longitude columns
- DB: 473 restrooms, 100% GPS, 0 null districts

### D2.5 ARIMA/LSTM 实施计划

#### 当前数据限制

- `traffic_hourly.csv` 是按道路方向和小时聚合的 24 小时年度平均轮廓，不是连续历史时间序列。
- 当前数据缺少日期、连续时间戳和 `venue_id`，不能直接作为可信的 ARIMA/LSTM 生产训练集。
- 该文件仅保留为小时轮廓分析和演示基线，不标记为生产训练数据。

#### 实施阶段

1. 历史序列重构: 从 NYC SODA 保留 `yr`、`m`、`d`、`hh`，按道路方向生成 `traffic_timeseries.csv`。
2. 基线模型: 实现 24 小时季节性朴素预测，作为 SARIMA/LSTM 的最低性能基准。
3. SARIMA: 使用 Statsmodels SARIMAX 为每条道路方向训练时序模型；数据不足时回退到季节性基线。
4. LSTM: 使用 PyTorch 训练共享模型，输入过去 24 或 48 小时，输出未来 12 小时。
5. 场馆映射: 建立道路序列到场馆的空间映射，生成 `venue_traffic_mapping.csv`，字段为 `venue_id`、`series_id`、`distance_m`。
6. 预测发布: 统一输出 `forecast_for`、`predicted_score`、`predicted_level`、`model_version`，最终写入 `busyness_forecasts`。

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

---

## Venue ML Coverage SOP (2026-06-23)

**目标**: 保留原始 venue catalogue，同时明确哪些 venue 可进入 supervised ML。

- 原始 `venues` 不删除。
- 仅训练有可靠 Google Popular Times / SerpApi busy label 的 venue。
- 无 label venue 不进入 supervised ML，但仍可在应用层展示。
- `no_data` 只表示数据可用性，不是预测等级。

### 最小规则

- `label_status` 只保留 `api_not_checked` / `has_popular_times` / `no_popular_times` / `api_error`
- `prediction_source` 只保留 `ml_model` / `rule_fallback` / `none`
- `display_level` 只保留 `quiet` / `moderate` / `busy` / `no_data`
- 只有 `prediction_source = none` 时，`display_level` 才允许为 `no_data`
- SerpApi 只做候选筛选、匹配和验证，不做全量盲查

### 额度策略

- 先离线筛选，再调用 SerpApi
- 只对高优先级候选做 Place detail 验证
- 所有 raw response 必须缓存
- 预计 labeled set 以 80-180 个 venue 为保守范围

### SerpApi 查询设计

主流程使用 Google Maps Search，而不是普通 Google Search。普通搜索会混入网页结果、百科、新闻和健康文章，不适合作为 venue discovery 主数据源。

整体策略是三步流程：

1. **Discovery**: 用粗类别关键词 + 地理网格批量发现 Google Maps candidates。
2. **Matching**: 将 candidates 按名称、距离、类别匹配回本地 cleaned venues。
3. **Validation**: 只对匹配成功且高优先级的 candidates 调 Place Results，检查 `popular_times` / busy score。

Discovery 查询模板：

```text
engine=google_maps
type=search
q=<coarse_category_keyword>
ll=@<lat>,<lng>,<zoom>z
hl=en
gl=us
```

示例：

```text
engine=google_maps
type=search
q=cafe
ll=@40.7580,-73.9855,15z
hl=en
gl=us
```

Place validation 查询模板：

```text
engine=google_maps
place_id=<google_place_id>
hl=en
gl=us
```

Discovery 阶段收集字段：

| 字段 | 用途 |
|------|------|
| `title` | 名称匹配 |
| `place_id` | 后续 Place Results 查询 |
| `gps_coordinates` | 空间匹配 |
| `rating` | 候选优先级 |
| `reviews` | 候选优先级与热度 proxy |
| `type` / `types` | 类别匹配 |
| `address` | 辅助去重和人工审查 |

`data_id` 可保留在 raw response cache 中，但不进入主状态表或核心匹配逻辑。主流程统一以 `place_id` 作为 Google Maps 标识。

粗类别关键词控制在 8-12 个，每类 1-3 个 query phrase：

| 本地大类 | SerpApi query phrase |
|----------|----------------------|
| `food_drink` | `cafe`, `coffee shop`, `restaurant` |
| `health` | `pharmacy`, `hospital`, `urgent care` |
| `public_service` | `library`, `public restroom`, `community center` |
| `tourism` | `museum`, `tourist attraction`, `art gallery` |
| `outdoor` | `park`, `playground` |

预算计算：

```text
search_budget = keyword_count x grid_cell_count x pages_per_query
place_budget = remaining_calls_for_popular_times_validation
```

示例：

```text
10 keywords x 15 grid cells x 1 page = 150 search calls
250 monthly quota - 150 search calls = 100 place validation calls
```

匹配回本地 venue catalogue 的建议规则：

```text
match_score =
    name_similarity
  + distance_score
  + category_similarity

if distance_m <= 50 and name_similarity >= 0.85:
    matched
elif distance_m <= 100 and name_similarity >= 0.75 and category_match:
    matched
else:
    unmatched_google_candidate
```

Search query 用于批量发现 candidates；Place query 只用于最终 label 验证。不要对每个本地 venue 直接消耗一次 SerpApi 调用。

## Sprint 3 数据任务（fangxun.wu）

> **说明**: 下列任务全部归属 Sprint 3 的 `fangxun.wu` 工作流，并按现有 DB 设计约束执行：基础 `venues` / `reports` 结构保持稳定，实时与预测结果写入动态层，医疗资料单独进入加密表。

- `S3.1 MySQL Keyring Configuration & Tablespace Encryption Integration`  
  SOP: 只为加密医疗表提供前置能力；先验证 keyring 和 tablespace encryption，再执行加密迁移；不要把失败扩散到无关基础表。

- `S3.2 Encrypted User Medical Profile Schema Migration Setup`  
  SOP: 只建 `user_medical_profiles` 一张表；`user_id` 同时做 PK/FK，`ON DELETE CASCADE`，只存 Tier 2 医疗字段，表级 `ENCRYPTION='Y'`。

- `S3.3 Real-Time MySQL Seed Venues Ingestion & Verification`  
  SOP: 做成幂等 seed；只补齐静态 `venues` 基础数据；执行前后都能重复跑，不把它当 ETL 第二权威源。

- `S3.4 Real-Time Zoned Telemetry Pipeline`  
  SOP: 只写动态 telemetry 层或预测输入层；实时容量和等待时间不要回写 `venues` 静态表。

- `S3.5 12-Hour Capacity Forecasting Production Engine`  
  SOP: 输出 12 小时预测结果到 forecast 层；保持结构和前端读取一致；不要把预测逻辑混进静态 venue 记录。

- `S3.6 Polymorphic Crowdsourced Ingestion Engine & 2-Hour TTL Pipeline`  
  SOP: 保留 report 记录并更新状态；TTL 到期只改 `expired` / `status`，不要硬删除；Path A / Path B 分开处理。

---

### Sprint 3 扩展：用户医疗信息加密存储

**目标**: 在服务器端加密存储用户 Tier 2 医疗数据，并通过同一账号支持 iOS / Android / Web 自动同步。

**前置条件**: Phase 2 (users 表必须存在)

**范围决策 (2026-06-17)**:

- Medical ID 不再坚持 “100% 本地”；本阶段修订为服务器端存储加密医疗资料。
- 加密边界为 MySQL InnoDB 表空间加密，应用层和 API 层按明文业务对象处理。
- 不做字段级 AES 加密、端到端加密、KMS、离线缓存、审计日志或历史版本。
- 登录注册同步切到 MySQL `users` 表；JWT 必须从真实用户记录签发。
- JWT 只做 access token，不做 refresh token、rotation 或 revoke list。
- 三端都可读写，但 Phase 7 只交付后端 + OpenAPI + 测试；iOS / Android / Web UI 接入另行排期。

| # | Task | Description | Status |
|---|------|-------------|:------:|
| 7.1 | 共享 DB helper | 抽出 `pymysql` 连接/事务 helper，供 auth 和 medical API 复用 | ⏳ 待实施 |
| 7.2 | MySQL Auth 改造 | `register/login` 读写 `users` 表，密码使用 hash，不再使用 `AUTH_USERS` mock | ⏳ 待实施 |
| 7.3 | Bearer JWT | 登录/注册返回 access token；protected API 从 `Authorization: Bearer <token>` 解析 `sub=user_id` | ⏳ 待实施 |
| 7.4 | Docker keyring 配置 | `docker-compose.yml` 启用 MySQL keyring，表空间加密不可用时硬失败 | ⏳ 待实施 |
| 7.5 | 新建 `user_medical_profiles` 表 | `user_id` FK + 结构化医疗字段 + `ENCRYPTION='Y'` | ⏳ 待实施 |
| 7.6 | 后端 Medical API | `GET` / `PUT` / `DELETE /api/v1/user/medical-profile`，用户身份只来自 JWT | ⏳ 待实施 |
| 7.7 | OpenAPI 更新 | 修订 D10 隐私边界、Auth token schema、MedicalProfile schema 和三端同步 API | ⏳ 待实施 |
| 7.8 | 后端测试 | PyTest: password hash、JWT 鉴权、用户隔离、GET/PUT/DELETE、级联删除、表加密验证 | ⏳ 待实施 |

**加密方案选择**:

| 方案 | 粒度 | 是否本阶段 | 说明 |
|------|------|:---:|------|
| InnoDB 表空间加密 | 整张表 | ✅ | 当前最小实现；医疗表必须 `ENCRYPTION='Y'` |
| 列级 AES_ENCRYPT | 单个字段 | ❌ | 不做字段级加解密，避免引入密钥管理复杂度 |
| 端到端加密 | 客户端密文 | ❌ | 不做跨 iOS / Android / Web 的客户端密钥同步 |
| 应用层加密 + KMS | 代码控制 | ❌ | 生产增强项，本阶段不引入 KMS |

> **硬约束**: 如果 MySQL keyring 或表空间加密不可用，迁移必须失败；不得降级创建未加密 `user_medical_profiles` 表。

**认证与同步方案**:

- `POST /api/v1/auth/register`: 写入 MySQL `users` 表，`password_hash = generate_password_hash(password)`。
- `POST /api/v1/auth/login`: 从 MySQL `users` 表查用户，使用 `check_password_hash()` 校验密码。
- 登录/注册返回 `access_token`，JWT payload 至少包含 `sub=user_id`。
- `GET` / `PUT` / `DELETE /api/v1/user/medical-profile` 必须使用 Bearer JWT。
- Medical API 不接受 `user_id` 参数，所有读写都绑定 JWT 当前用户。
- 三端自动同步语义: 任一端保存后，其他端下次 `GET` 获取最新资料。
- 冲突策略: 最后写入覆盖；本阶段不做 `version`、`If-Match` 或 `409 Conflict`。
- 数据保留: 每个用户最多一行医疗资料；不保留历史版本或审计日志。

**字段来源对照**:

| 字段 | Mobile MedicalId | Web userProfile | F-12 需求 | F-11/F-14 | 存储层级 |
|------|:---:|:---:|:---:|:---:|------|
| blood_type | ✅ string | ✅ string | ✅ | ✅ | Tier 2 (加密) |
| severe_allergies | ✅ {name,detail}[] | ✅ {name,detail}[] | ✅ | ✅ | Tier 2 (加密) |
| conditions | ✅ {name,detail}[] | ✅ {name,detail}[] | ✅ | ✅ | Tier 2 (加密) |
| medications | ✅ {name,dosage,frequency}[] | — | — | ✅ F-11 | Tier 2 (加密) |
| emergency_contacts | — | ✅ {name,relationship,phone,primary}[] | ✅ | ✅ F-14 | Tier 2 (加密) |
| emergency_notes | ✅ string | — | — | — | Tier 2 (加密) |
| medical_pass_title | ✅ string | — | — | — | Tier 2 (加密) |
| donor_status | — | ✅ string | — | — | Tier 2 (加密) |
| date_of_birth | — | ✅ | ✅ | ✅ F-14 | Tier 1 (已在 UserProfile) |
| gender | — | ✅ | ✅ | — | Tier 1 (已在 UserProfile) |
| address | — | ✅ | ✅ | — | Tier 1 (已在 UserProfile) |

> **注意**: date_of_birth, gender, address 已在 `users` 表 (Tier 1)，不重复存储。
> Mobile / Web / iOS / Android 统一对象数组格式，不再兼容 `string[]` 原样存储。

**Schema 草案**:

```sql
CREATE TABLE user_medical_profiles (
    -- 主键
    user_id             VARCHAR(36) PRIMARY KEY,

    -- 基础信息
    blood_type          VARCHAR(5),             -- O+, O-, A+, A-, B+, AB+
    donor_status        VARCHAR(50),            -- organ_donor 等

    -- 医疗信息 (统一对象数组)
    severe_allergies    JSON,                   -- [{"name":"Penicillin","detail":"Anaphylaxis"}]
    conditions          JSON,                   -- [{"name":"Asthma","detail":"Diagnosed 2005"}]
    medications         JSON,                   -- [{"name":"Salbutamol","dosage":"2 puffs","frequency":"As needed"}]

    -- 紧急联系人
    emergency_contacts  JSON,                   -- [{"name":"Jane Doe","relationship":"Spouse","phone":"212-555-0101","primary":true}]
    emergency_notes     TEXT,                   -- 自由文本备注

    -- Medical Passport
    medical_pass_title  VARCHAR(100),           -- 自定义标题 (如 "Medical Information")

    -- 时间戳
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_medical_profile_user
      FOREIGN KEY (user_id) REFERENCES users(user_id)
      ON DELETE CASCADE
) ENCRYPTION='Y';
```

**JSON 字段格式规范**:

```json
{
  "blood_type": "O+",
  "donor_status": "organ_donor",
  "severe_allergies": [
    {"name": "Penicillin", "detail": "Anaphylaxis"}
  ],
  "conditions": [
    {"name": "Asthma", "detail": "Diagnosed 2005"}
  ],
  "medications": [
    {"name": "Salbutamol Inhaler", "dosage": "2 puffs", "frequency": "As needed"}
  ],
  "emergency_contacts": [
    {"name": "Jane Doe", "relationship": "Spouse", "phone": "212-555-0101", "primary": true}
  ],
  "emergency_notes": "Use inhaler before calling ambulance.",
  "medical_pass_title": "Medical Information"
}
```

**默认空 Profile**:

```json
{
  "blood_type": null,
  "donor_status": null,
  "severe_allergies": [],
  "conditions": [],
  "medications": [],
  "emergency_contacts": [],
  "emergency_notes": null,
  "medical_pass_title": "Medical Information"
}
```

**API 语义**:

| Method | Path | 语义 |
|--------|------|------|
| GET | `/api/v1/user/medical-profile` | 返回当前 JWT 用户医疗资料；不存在时返回默认空 Profile |
| PUT | `/api/v1/user/medical-profile` | 全量替换/upsert 当前 JWT 用户医疗资料；最后写入覆盖 |
| DELETE | `/api/v1/user/medical-profile` | 删除当前 JWT 用户医疗资料；幂等；再次 GET 返回默认空 Profile |

**非范围**:

- 不包含 iOS / Android / Web UI 接入或 mock 替换。
- 不包含离线缓存、本地 SecureStore/Keychain/IndexedDB 存储。
- 不包含 refresh token、token rotation、token revoke list。
- 不包含医疗资料历史版本、审计日志或恢复功能。
- 不包含字段级加密、端到端加密或 KMS。

**更新文件范围与代码量预估**:

| 文件/目录 | 变更 | 预估代码量 |
|-----------|------|-----------:|
| `src/db.py` | 新增共享 MySQL 连接/事务 helper | 40-80 行 |
| `src/auth.py` | 新增 Bearer JWT 生成/解析、当前用户校验 helper | 80-150 行 |
| `src/api/auth.py` | 注册/登录从 mock 改为 MySQL users + password hash + access token | 120-220 行 |
| `src/api/user.py` | 新增 medical profile GET/PUT/DELETE | 120-220 行 |
| `docker-compose.yml` | MySQL keyring / 表空间加密配置 | 10-30 行 |
| `docker/mysql/init/001_clearpath_schema.sql` | 新增 `user_medical_profiles` 加密表；必要时调整 users 相关约束 | 50-100 行 |
| `.env.example` / `src/settings.py` | 新增 DB/JWT 配置项 | 20-60 行 |
| `openapi.yaml` | Auth token、MedicalProfile schema、medical-profile endpoints、D10 修订 | 150-260 行 |
| `backend/tests/` | JWT、password hash、medical profile、用户隔离、级联删除、表加密测试 | 180-350 行 |

**后端 + OpenAPI 总代码量**: 约 770-1,470 行。

**工作量预估**: 15-26 小时；如果 MySQL keyring / `ENCRYPTION='Y'` 在 Docker MySQL 8.4 上配置踩坑，额外 2-6 小时。

---

## 实施依赖关系

```
Phase 1 (同步+决策)
    ↓
Phase 2 (users + favorites + notifications)
    ↓
Phase 3 (reports user_id + confirmations user_id)    Phase 7 (医疗数据加密存储)
    ↓                                                  ↑ 依赖 Phase 2
Phase 4 (busyness_forecasts)
    ↓
Phase 5 (RAG 索引)
    ↓
Phase 6 (验证+清理)
```

**Phase 2 是所有后续阶段的前置条件** — 没有 users 表, Phase 3/5/7 都无法执行。

---

## 风险提示

1. **按旧 Pipeline 实现服务器医疗 Profile** — 违反 Final 隐私边界
2. **继续允许无法追踪用户身份的报告/确认** — 无法执行唯一用户确认
3. **12 小时预测数据失真** — 单值伪造数组无法支撑真实图表

---
