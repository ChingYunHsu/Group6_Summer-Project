# ClearPath 执行计划 (DB Schema 重点)

> 更新日期：2026-06-09

---

## Phase 1: 基础同步与决策冻结

**目标**: 统一 Schema 文件, 冻结产品决策

- [ ] 同步两份 `001_clearpath_schema.sql` (docker/mysql/init/ ↔ Data+ML/test/6.2-6.5_DB/)
- [ ] 冻结 5 项产品决策:

| 决策项 | 选项 | 影响 |
|-------|------|------|
| 报告是否必须登录 | 是 / 否 | Schema + API 认证层 |
| 报告类别最终集合 | 4-8 个类别 | ENUM 或字典表 |
| 四级拥挤度第四级含义 | `very_high` / `unknown` | ENUM 定义 |
| 医疗数据是否绝不云同步 | 绝不 / opt-in 加密 | 服务器端设计 |
| RAG embedding 存储位置 | MySQL / 外部向量库 | 基础设施选型 |

---

## Phase 2: 用户与账户表

**目标**: 建立认证基础

### 新建 `users` 表

```sql
CREATE TABLE users (
  user_id VARCHAR(36) PRIMARY KEY,
  auth_subject VARCHAR(255) UNIQUE,
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

### 新建 `user_favorite_venues` 表

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

### 新建 `notification_preferences` 表

```sql
CREATE TABLE notification_preferences (
  pref_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  venue_id VARCHAR(36),
  notification_type ENUM('crowd_alert','closure_alert','quiet_hours') NOT NULL,
  enabled BOOLEAN DEFAULT TRUE,
  threshold TINYINT UNSIGNED,
  quiet_start TIME,
  quiet_end TIME,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_notif_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE,
  UNIQUE KEY uq_user_notif_type (user_id, venue_id, notification_type)
);
```

---

## Phase 3: 报告系统改造

**目标**: 绑定认证用户, 防重复投票

### 改造 `user_reports`

```sql
-- 新增用户外键
ALTER TABLE user_reports ADD COLUMN user_id VARCHAR(36) NOT NULL AFTER report_id;
ALTER TABLE user_reports ADD CONSTRAINT fk_report_user
  FOREIGN KEY (user_id) REFERENCES users(user_id);

-- 移除匿名字段
ALTER TABLE user_reports DROP COLUMN anonymous;
ALTER TABLE user_reports DROP COLUMN reported_by;
```

### 改造 `report_confirmations`

```sql
ALTER TABLE report_confirmations ADD COLUMN user_id VARCHAR(36) NOT NULL;
ALTER TABLE report_confirmations ADD CONSTRAINT fk_confirmation_user
  FOREIGN KEY (user_id) REFERENCES users(user_id);
ALTER TABLE report_confirmations ADD UNIQUE KEY uq_report_user (report_id, user_id);
```

### 报告类别迁移 (可选)

如果产品决定使用字典表而非 ENUM:

```sql
CREATE TABLE report_categories (
  category_id VARCHAR(64) PRIMARY KEY,
  display_name VARCHAR(128) NOT NULL,
  applies_to_venue_types JSON,
  icon_name VARCHAR(64),
  sort_order TINYINT UNSIGNED DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE
);
```

---

## Phase 4: 拥挤度预测

**目标**: 支持 12 小时预测图表

### 新建 `busyness_forecasts` 表

```sql
CREATE TABLE busyness_forecasts (
  forecast_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  venue_id VARCHAR(36) NOT NULL,
  forecast_for DATETIME NOT NULL,
  predicted_score TINYINT UNSIGNED NOT NULL,
  predicted_level ENUM('quiet','moderate','busy') NOT NULL,
  estimated_wait_minutes INT UNSIGNED,
  model_version VARCHAR(64) NOT NULL,
  generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_forecast (venue_id, forecast_for, model_version),
  INDEX idx_forecast_venue_time (venue_id, forecast_for),
  CONSTRAINT fk_forecast_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);
```

**职责分离**:
- `busyness_scores` → 实时观测 (当前时刻拥挤度, 保留 `forecast_1h` 用于快速查询)
- `busyness_forecasts` → 未来 12h 时序预测 (ML pipeline 写入, 支持模型版本追踪)

**API 查询**: `WHERE venue_id = ? AND forecast_for >= NOW() ORDER BY forecast_for LIMIT 12`

---

## Phase 5: RAG 数据层

**目标**: 支持 Gemini RAG 查询

- [ ] 为 `venues(latitude, longitude)`、`venue_type`、`district` 建立索引
- [ ] 生成可检索的场馆文档投影 (含语言、无障碍、营业、警告、实时拥挤度)
- [ ] 确定 embedding 存储方案 (MySQL JSON/BLOB vs 外部向量库)
- [ ] 不创建服务端 `chat_history` 表 (Final 要求聊天历史仅客户端)

---

## Phase 6: OpenAPI 与验证

**目标**: 确保 API 与 DB 一致

- [ ] 更新 mock_data.py 对齐新 schema
- [ ] 更新 ETL notebook 验证新表结构
- [ ] 级联删除测试 (删除用户 → 收藏、通知、报告一并清除)
- [ ] 第二次 ETL 幂等性验证 (不产生重复行)
- [ ] MySQL 5.7 COMMENT 语法兼容性检查

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
