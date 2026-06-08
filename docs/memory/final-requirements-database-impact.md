# Final 需求对数据库设计的影响

> **更新日期**：2026-06-07
> **参考材料**：`Mobile Mockup.pdf` (37 页 UI 规范)、`openapi.yaml` (v1.1.0)、`001_clearpath_schema.sql`

---

## 1. 当前数据库状态

### 1.1 Schema 已实现 (13 张表)

| 表名 | 用途 | 状态 |
|------|------|------|
| `venues` | 统一 POI 表 (含 district、语言、无障碍、警告) | ✅ 完成 |
| `venue_source_links` | 场馆原始数据源映射 | ✅ 完成 |
| `restroom_profiles` | 卫生间详情 | ✅ 完成 |
| `healthcare_profiles` | 医疗机构详情 | ✅ 完成 |
| `emergency_assets` | AED 设备数据 | ✅ 完成 |
| `pedestrian_ramps` | 无障碍坡道数据 | ✅ 完成 |
| `venue_accessibility` | 场馆无障碍详情 | ✅ 完成 |
| `venue_language` | 场馆多语言支持 | ✅ 完成 |
| `venue_warnings` | 场馆警告和提醒 | ✅ 完成 |
| `user_reports` | 众包事件报告 | ⚠️ 需改造 |
| `report_confirmations` | 报告用户投票 | ⚠️ 需改造 |
| `busyness_scores` | ML 拥挤度预测 | ⚠️ 需改造 |
| `external_context_cache` | 外部 API 缓存 | ✅ 完成 |

### 1.2 缺失的关键表

| 表名 | Final 需求 | 优先级 |
|------|-----------|--------|
| `users` | 账户系统基础 | P0 |
| `user_favorite_venues` | 跨设备收藏同步 | P1 |
| `notification_preferences` | 安静时段提醒 + Push 订阅 | P1 |
| `user_devices` | 设备 Push Token (可选) | P2 |
| `busyness_forecasts` | 12 小时时序预测 | P1 |

### 1.3 OpenAPI 定义的端点 vs Schema 覆盖

| OpenAPI 端点 | Schema 支持 | 冲突 |
|-------------|------------|------|
| `POST /api/v1/reports` | ❌ 无 `user_id` | 游客可提交，违反 Final |
| `POST /api/v1/reports/{id}/confirmations` | ❌ 无 `user_id` | 无法防重复投票 |
| `GET /api/v1/user/profile` | ❌ 无 `users` 表 | 无数据源 |
| `GET /api/v1/user/medical-id` | ❌ 无医疗表 | Final 要求本地存储 |
| `GET /api/v1/user/favourites` | ❌ 无收藏表 | 无数据源 |
| `GET /api/v1/user/emergency-contacts` | ❌ 无联系人表 | Final 要求本地存储 |

---

## 2. 总体判断

Final 版不会推翻现有场馆数据模型，但会显著改变以下边界：

1. **医疗 Profile 改为严格本地存储**，不应默认进入 MySQL。
2. **MySQL 只同步账户、收藏场馆、通知偏好等非医疗数据**。
3. **报告和确认从"允许匿名"改为"必须登录"**。
4. **拥挤度需要真正的 12 小时时序预测**，而不是单个 `forecast_1h`。
5. **RAG 需要可检索的数据投影和索引**，但聊天记录默认不得服务端持久化。
6. **US-14 Medical Passport PDF 主要读取本地 Profile**，对服务器数据库没有直接写入需求。

---

## 3. 必须调整的数据库设计

### 3.1 新增账户及同步数据表

Final 明确支持可选账户和跨设备同步，但只同步收藏与通知偏好。建议新增：

#### `users`

```sql
CREATE TABLE users (
  user_id VARCHAR(36) PRIMARY KEY,
  auth_subject VARCHAR(255) UNIQUE,  -- JWT subject / OAuth ID
  email VARCHAR(255),
  display_name VARCHAR(128),
  preferred_language VARCHAR(10) DEFAULT 'en',
  account_status ENUM('active','suspended','deleted') DEFAULT 'active',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  INDEX idx_users_email (email),
  INDEX idx_users_auth (auth_subject)
);
```

**不要在该表保存医疗情况、过敏、药物、血型、家庭地址或医疗照片。**

#### `user_favorite_venues`

```sql
CREATE TABLE user_favorite_venues (
  user_id VARCHAR(36) NOT NULL,
  venue_id VARCHAR(36) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, venue_id),
  CONSTRAINT fk_fav_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_fav_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);
```

#### `notification_preferences`

```sql
CREATE TABLE notification_preferences (
  pref_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  venue_id VARCHAR(36),  -- 场馆提醒时使用，NULL 表示全局偏好
  notification_type ENUM('crowd_alert','closure_alert','quiet_hours') NOT NULL,
  enabled BOOLEAN DEFAULT TRUE,
  threshold TINYINT UNSIGNED,  -- 拥挤度阈值
  quiet_start TIME,  -- 安静时段开始
  quiet_end TIME,    -- 安静时段结束
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_notif_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE,
  UNIQUE KEY uq_user_notif_type (user_id, venue_id, notification_type)
);
```

若需要保存设备 Push Token，应拆分 `user_devices`，避免把设备状态塞进偏好表。

---

### 3.2 不应新增服务器端医疗 Profile 表

Final 要求 Profile、医疗信息、照片和聊天会话严格保存在 AsyncStorage 或本地 SQLite，并支持本地完整清除。

**OpenAPI 冲突点：**

| 端点 | 问题 | Final 要求 |
|------|------|-----------|
| `GET /api/v1/user/medical-id` | 返回血型、过敏、药物 | 仅本地存储 |
| `GET /api/v1/user/emergency-contacts` | 返回完整联系人 | 仅本地存储 |
| `GET /api/v1/user/profile` | 含 `spoken_languages`、`address` | 仅账户显示信息 |

因此 memory 中原计划的服务器端 `Profile & Medical ID CRUD` 与 Final 存在冲突：

- `/api/v1/profile` 不应默认保存医疗数据到 MySQL。
- `DELETE /api/v1/account` 只能删除服务器端账户、收藏、通知和报告数据。
- 本地医疗数据必须由客户端单独执行 wipe。
- 若未来允许医疗资料跨设备同步，必须作为显式 opt-in 功能重新设计，包括加密、同意记录、撤回和保留策略，不能沿用普通 Profile CRUD。

**建议 OpenAPI 修改：**
- 移除 `GET /api/v1/user/medical-id` 和 `GET /api/v1/user/emergency-contacts`
- `UserProfile` 仅保留 `user_id`, `account_state`, `full_name`, `email`, `preferred_language`
- Medical ID 和 Emergency Contacts 由客户端本地 API 处理

---

### 3.3 报告表必须绑定认证用户

当前 `user_reports` 使用：

- `anonymous BOOLEAN`
- `reported_by VARCHAR(50)`
- 没有到 `users` 的外键

**Final Mockup 明确要求 (Page 6-B)：**
> "Login Requirement: If not logged in, shows a mandatory alert: *To help keep ClearPath data accurate and prevent spam, you must be logged in to submit or verify community reports.* [Login / Sign Up] vs. [Cancel]"

建议：

```sql
-- 新增用户外键
ALTER TABLE user_reports ADD COLUMN user_id VARCHAR(36) NOT NULL AFTER report_id;
ALTER TABLE user_reports ADD CONSTRAINT fk_report_user
  FOREIGN KEY (user_id) REFERENCES users(user_id);

-- 移除匿名字段
ALTER TABLE user_reports DROP COLUMN anonymous;
ALTER TABLE user_reports DROP COLUMN reported_by;

-- 历史数据迁移：为旧匿名报告创建系统用户
-- INSERT INTO users (user_id, display_name) VALUES ('system-anonymous', 'Anonymous (Legacy)');
-- UPDATE user_reports SET user_id = 'system-anonymous' WHERE user_id IS NULL;
```

当前 Path A/Path B 已可由 `venue_id NULL/非 NULL + latitude/longitude` 表达，无需拆两张报告表。

---

### 3.4 报告确认必须防止重复投票

当前 `report_confirmations` 没有 `user_id`，无法验证"登录用户"或"唯一用户确认"。

**Final Mockup 明确要求 (Page 6-C)：**
> "confirmation string (*Is this still an issue? (3 users confirmed)*)"

"3 users confirmed" 暗示按用户去重计数，但当前 Schema 无法实现。

建议新增：

```sql
ALTER TABLE report_confirmations ADD COLUMN user_id VARCHAR(36) NOT NULL;
ALTER TABLE report_confirmations ADD CONSTRAINT fk_confirmation_user
  FOREIGN KEY (user_id) REFERENCES users(user_id);
ALTER TABLE report_confirmations ADD UNIQUE KEY uq_report_user (report_id, user_id);
```

如果允许用户修改选择，使用 upsert 更新 `action`，不要插入多条确认。报告上的确认总数应聚合计算，或维护带事务保护的缓存计数。

---

### 3.5 报告类别需要迁移

Final 的核心类别包括：

- `elevator_broken`
- `long_wait_time`
- `ramp_blocked`
- `closed_early`

当前 `user_reports.issue_type` 缺少后三项，但包含旧版其他类别：

| 当前 Schema | Final 需求 | 状态 |
|------------|-----------|------|
| `elevator_broken` | `elevator_broken` | ✅ |
| `wheelchair_lift_broken` | — | 需确认 |
| `toilet_out_of_order` | — | 需确认 |
| `large_crowd` | `long_wait_time` | ⚠️ 重命名？ |
| `protest_or_blockage` | `ramp_blocked` | ❌ 缺失 |
| `entrance_closed` | `closed_early` | ⚠️ 重命名？ |

必须扩展 ENUM；更稳妥的设计是改成 `report_categories` 字典表，避免每次产品调整都执行 ENUM migration：

```sql
CREATE TABLE report_categories (
  category_id VARCHAR(64) PRIMARY KEY,
  display_name VARCHAR(128) NOT NULL,
  applies_to_venue_types JSON,  -- 限制适用场馆类型
  icon_name VARCHAR(64),
  sort_order TINYINT UNSIGNED DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE
);
```

---

### 3.6 12 小时预测需要正规时序结构

当前 `busyness_scores` 只有一个整数 `forecast_1h`，无法可靠表达 12 个小时的预测点。

**OpenAPI 冲突：**
- `Venue.busyness_forecast_12h` 定义为 12 元素数组 `[{offset_hours, percent, level}]`
- 但 Schema 只有 `forecast_1h INT`，无法支撑

**Final Mockup 要求 (Page 6-D)：**
> "interactive '12-Hour Wait Time Forecast Chart'"

memory 中"API 层将 `forecast_1h` 转换为 12h 数组"的方案不成立：单值不能生成真实 12 小时序列。

建议新增 `busyness_forecasts`：

```sql
CREATE TABLE busyness_forecasts (
  forecast_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  venue_id VARCHAR(36) NOT NULL,
  forecast_for DATETIME NOT NULL,          -- 预测的目标时间点
  predicted_score TINYINT UNSIGNED NOT NULL, -- 0-100
  predicted_level ENUM('quiet','moderate','busy') NOT NULL,
  estimated_wait_minutes INT UNSIGNED,
  model_version VARCHAR(64) NOT NULL,
  features_snapshot_id VARCHAR(128),
  generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_forecast (venue_id, forecast_for, model_version),
  INDEX idx_forecast_venue_time (venue_id, forecast_for),
  CONSTRAINT fk_forecast_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);
```

`busyness_scores` 保留实时观测；`busyness_forecasts` 保存未来时点。这样支持 12 小时图、最佳出行窗口和模型版本追踪。

---

### 3.7 四级拥挤度需统一命名

Final 使用四级显示体系。当前数据库与 OpenAPI 存在不一致：

| 层级 | Schema ENUM | OpenAPI Venue | Final UI (Page 6-A) |
|------|------------|---------------|---------------------|
| 低 | `low` | `quiet` | Quiet |
| 中 | `medium` | `moderate` | Moderate |
| 高 | `high` | `busy` | Busy |
| 第四级 | `unknown` | ❌ 无 | ❌ 无 |

**需要确认 Final UI 的准确标签与阈值，并建立单一映射。** 若第四级是 `very_high` 而不是 `unknown`，必须修改 ENUM；如果第四级只是无数据状态，则当前模型可保留，但文档和 API 必须明确。

---

### 3.8 RAG 数据层

Final 要求从 `venues + busyness_scores` 检索真实数据，并返回来源场馆和距离。

最低要求：

- 为 `venues(latitude, longitude)`、`venue_type`、`district`、语言和无障碍过滤字段建立合适索引。
- 以场馆为单位生成可检索文档投影，包含语言、无障碍、营业、警告和实时拥挤度。
- 保存 embedding 的方案需单独确定。MySQL 可保存向量 JSON/BLOB，但不适合高质量向量近邻检索；可以使用外部向量库，同时以 `venue_id` 作为权威关联键。
- 不要默认创建服务端 `chat_history` 表，因为 Final 明确要求聊天历史仅保存在客户端，除非用户显式 opt-in。

---

## 4. 现有设计已基本满足的部分

- `venues` 已包含 district、语言、无障碍和警告字段。
- `venue_language` 支持多语言场馆能力。
- `venue_accessibility`、`restroom_profiles`、`pedestrian_ramps` 支持无障碍筛选。
- `user_reports.venue_id` 可空及 GPS 字段支持报告 Path A/Path B。
- `status + expires_at` 索引支持两小时 TTL 查询。
- `report_confirmations` 已与报告级联删除。
- `venue_source_links` 和 `source_confidence` 支持 RAG 来源追踪。
- `external_context_cache` 可缓存天气或外部实时上下文。

---

## 5. Final 带来的需求冲突

### 5.1 本地 Profile vs 服务器 Profile CRUD

| | Final | 当前 Pipeline |
|---|-------|--------------|
| 医疗数据 | 严格本地保存 | 计划 MySQL CRUD |
| 账户信息 | 仅同步显示字段 | 含医疗字段 |
| 删除 | 本地 wipe + 服务器账户删除 | 未明确 |

**建议**：以 Final 的隐私边界为准：服务器 Profile 只保留账户显示信息和偏好，医疗数据留在客户端。

### 5.2 登录后报告 vs 匿名报告

| | Final | 当前 Schema + API |
|---|-------|-------------------|
| 提交报告 | 必须登录 | 允许匿名 |
| 确认报告 | 必须登录，按用户去重 | 无用户标识 |
| 游客权限 | 仅查看 | 可提交、可确认 |

**必须由产品负责人确认最终规则。** 若采用 Final，应迁移到 `user_id` 外键并在 API 层强制认证。

### 5.3 语言默认过滤

Final 的功能描述仍写"登录后默认应用语言筛选"，但 Final US-01 接受标准写"只预选，不自动应用"。这会影响：

- `users.preferred_language` 是否只是 UI 默认值；
- 地图查询是否自动追加 language 参数；
- 是否需要服务器保存筛选状态。

**建议**：数据库只保存 `preferred_language`，是否自动应用由客户端行为控制，不额外保存"当前筛选结果"。

### 5.4 12 小时预测数据来源

| | Final | 当前实现 |
|---|-------|---------|
| 数据结构 | 12 个时间点 | 单值 `forecast_1h` |
| API 返回 | `busyness_forecast_12h[]` | 无 |
| 图表渲染 | 真实时序 | 伪造数组 |

**建议**：新增 `busyness_forecasts` 表，停止把单个 `forecast_1h` 伪装成 12 小时数组。

### 5.5 报告类别集合

Final 文档与当前 Schema 的类别不完全匹配：

- `long_wait_time` vs `large_crowd`：语义不同
- `ramp_blocked` vs `protest_or_blockage`：完全不同
- `closed_early` vs `entrance_closed`：可能重叠

**建议**：产品负责人冻结最终类别集合，然后迁移。

---

## 6. Final 接受标准完整性

Final 包含 14 个用户故事和 57 条接受标准。此前"只有 US-01 有标准"的判断源于遗漏 Word 内容控件内嵌表格，现已更正。Schema 迁移前仍必须冻结以下决定：

| 决策项 | 选项 | 影响 |
|-------|------|------|
| 报告是否必须登录 | 是 / 否 | Schema + API 认证层 |
| 报告类别最终集合 | 4-6 个类别 | ENUM 或字典表 |
| 四级拥挤度的第四级含义 | `very_high` / `unknown` | ENUM 定义 |
| 医疗数据是否绝不云同步 | 绝不 / opt-in 加密 | 服务器端设计 |
| RAG embedding 存储位置 | MySQL / 外部向量库 | 基础设施选型 |

---

## 7. 推荐实施顺序

| 阶段 | 任务 | 涉及文件 |
|------|------|---------|
| **Phase 1: 基础** | 同步两份 Schema 文件 (docker/ 与 Data+ML/) | `001_clearpath_schema.sql` |
| **Phase 1: 基础** | 冻结上述五项产品决策 | 文档确认 |
| **Phase 2: 用户** | 新增 `users`、`user_favorite_venues`、`notification_preferences` | Schema |
| **Phase 2: 用户** | 更新 OpenAPI 移除 Medical ID 端点 | `openapi.yaml` |
| **Phase 3: 报告** | 为报告和确认增加 `user_id`、外键及唯一约束 | Schema |
| **Phase 3: 报告** | 将报告类别从 ENUM 迁移为字典表 | Schema + ETL |
| **Phase 4: 预测** | 新增 `busyness_forecasts`，停止伪造 12 小时数组 | Schema + ETL |
| **Phase 5: RAG** | 建立 RAG 场馆投影和索引，不保存聊天历史 | Schema + 索引 |
| **Phase 6: 验证** | 更新 OpenAPI、mock data、ETL 验证和级联删除测试 | 测试文件 |

---

## 8. 风险结论

**最高风险**不是现有 13 张表本身，而是：

1. **按旧 Pipeline 实现服务器医疗 Profile** — 违反 Final 隐私边界，可能导致 HIPAA 合规问题。
2. **继续允许无法追踪用户身份的报告/确认** — 无法执行唯一用户确认、账户删除不完整。
3. **12 小时预测数据失真** — 单值伪造数组无法支撑真实图表。

若不先解决这些冲突，会产生隐私设计返工、无法执行唯一用户确认、账户删除不完整和 12 小时预测数据失真的问题。

---

## 9. 附录：Mobile Mockup 关键页面与 Schema 映射

| Mockup 页面 | 关键功能 | Schema 支持 | 缺口 |
|------------|---------|------------|------|
| Page 1: Language Search | 双语命名选择器 | `users.preferred_language` | ✅ |
| Page 2: Legal & Privacy | HIPAA 合规声明 | — | 需文档 |
| Page 3: Location Permission | GPS 权限 | 客户端 | ✅ |
| Page 4: Secure Login Wall | 登录/游客分支 | `users` 表 | ❌ 缺失 |
| Page 5: Login & Registration | 凭证输入 | `users` 表 | ❌ 缺失 |
| Page 6: Main Map | 场馆标记 + 拥挤度 | `venues` + `busyness_scores` | ⚠️ 缺 12h 预测 |
| Page 6-A: Filter Bottom Sheet | 时间/拥挤度过滤 | `busyness_forecasts` | ❌ 缺失 |
| Page 6-B: Reporting Modal | Path A/B + 登录拦截 | `user_reports` | ⚠️ 缺 `user_id` |
| Page 6-C: Verification | 确认/解决按钮 | `report_confirmations` | ⚠️ 缺 `user_id` |
| Page 6-D: Clinic Details | 12 小时图表 | `busyness_forecasts` | ❌ 缺失 |
| Page 6-E: Map Routing | 步行/公交/驾车 | `external_context_cache` | ✅ |
| Page 7: AI Chatbot | Gemini RAG | 向量库 | 待定 |
| Page 8: SOS Overlay | 紧急信息展示 | 本地 Medical ID | ✅ 本地 |
| Page 9: Profile & Medical | 医疗资料编辑 | 本地存储 | ✅ 本地 |
| Page 10: Settings | 账户删除 | `users.deleted_at` | ❌ 缺失 |
