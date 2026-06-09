# ClearPath 数据库修复方案

**日期**: 2026-06-03  
**目标**: 对齐数据库 Schema 与 eq_sprint1 后端 API 代码

---

## 冲突汇总

| 级别 | 数量 | 说明 |
|------|:----:|------|
| 🔴 关键冲突 | 2 | venue_type 枚举值不匹配、API 未处理全部 action |
| 🟡 缺失字段 | 15 | venues 缺 11 列，reports 缺 4 列 |
| 🟠 冗余字段 | 7 | Schema 有但 API 未使用 |
| 🔵 行为冲突 | 2 | reports 无鉴权、时间格式不一致 |

---

## 修复方案

### 方案一：修改 Schema（推荐）

**原则**：Schema 是数据源，API 是消费方。Schema 应该包容 API 需求。

#### Step 1: 修改 venues 表枚举

```sql
-- venue_type 扩展枚举值（添加 clinic, pharmacy, hospital 等）
ALTER TABLE venues MODIFY COLUMN venue_type ENUM(
    'restroom', 'healthcare', 'emergency_asset',
    'clinic', 'pharmacy', 'hospital', 'dentist', 'laboratory'
) NOT NULL;
```

#### Step 2: venues 表新增字段

```sql
-- 语言支持
ALTER TABLE venues ADD COLUMN IF NOT EXISTS language_tags JSON AFTER borough;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS primary_language VARCHAR(10) AFTER language_tags;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS secondary_language VARCHAR(10) AFTER primary_language;

-- 无障碍状态
ALTER TABLE venues ADD COLUMN IF NOT EXISTS accessible_status ENUM(
    'full_access', 'partial', 'step_free_route_only', 'none'
) DEFAULT 'none' AFTER secondary_language;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS accessibility_features JSON AFTER accessible_status;

-- 预警
ALTER TABLE venues ADD COLUMN IF NOT EXISTS active_warning BOOLEAN DEFAULT FALSE AFTER accessibility_features;

-- 照片和评分
ALTER TABLE venues ADD COLUMN IF NOT EXISTS photos JSON AFTER opening_hours;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS rating DECIMAL(3,2) AFTER photos;

-- 天气风险
ALTER TABLE venues ADD COLUMN IF NOT EXISTS weather_risk ENUM('low', 'medium', 'high') DEFAULT 'low' AFTER rating;
```

#### Step 3: user_reports 表新增字段

```sql
-- 匿名和描述
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS anonymous BOOLEAN DEFAULT FALSE AFTER accuracy_meters;
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS description TEXT AFTER anonymous;
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS photos JSON AFTER description;

-- 上报者
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS reported_by VARCHAR(50) DEFAULT 'anonymous' AFTER photos;

-- 过期时间（分钟数，与 API 对齐）
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS expires_in_minutes INT DEFAULT 120 AFTER status;

-- 多语言
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS default_language VARCHAR(10) AFTER expires_in_minutes;
ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS fallback_language VARCHAR(10) AFTER default_language;
```

#### Step 4: report_confirmations 表新增字段

```sql
ALTER TABLE report_confirmations ADD COLUMN IF NOT EXISTS language VARCHAR(10) AFTER action;
```

#### Step 5: busyness_scores 表新增字段

```sql
ALTER TABLE busyness_scores ADD COLUMN IF NOT EXISTS forecast_1h INT AFTER estimated_wait_minutes;
ALTER TABLE busyness_scores ADD COLUMN IF NOT EXISTS forecast_4h INT AFTER forecast_1h;
ALTER TABLE busyness_scores ADD COLUMN IF NOT EXISTS forecast_8h INT AFTER forecast_4h;
```

#### Step 6: 新增 3 张表

```sql
-- 场所无障碍表
CREATE TABLE IF NOT EXISTS venue_accessibility (
    venue_id VARCHAR(36) PRIMARY KEY,
    wheelchair_friendly BOOLEAN DEFAULT FALSE,
    step_free_route BOOLEAN DEFAULT FALSE,
    accessible_toilet BOOLEAN DEFAULT FALSE,
    entrance_width_cm INT,
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);

-- 场所语言表
CREATE TABLE IF NOT EXISTS venue_language (
    venue_id VARCHAR(36) PRIMARY KEY,
    language_tag JSON,
    language_support_level ENUM('full', 'partial', 'none') DEFAULT 'none',
    chatbot_enabled BOOLEAN DEFAULT FALSE,
    chatbot_welcoming_message TEXT,
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);

-- 场所预警表
CREATE TABLE IF NOT EXISTS venue_warnings (
    venue_id VARCHAR(36) PRIMARY KEY,
    active_warning BOOLEAN DEFAULT FALSE,
    warning_detail TEXT,
    wait_alert BOOLEAN DEFAULT FALSE,
    replacement_suggestion JSON,
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);
```

---

### 方案二：修改 API 层（备选）

如果不想改动 Schema，可以在 API 层做映射：

| API 字段 | Schema 字段 | 映射逻辑 |
|----------|------------|---------|
| venue_type | venue_type | API 层映射：clinic → healthcare |
| active_warning | 无 | 查询 reports 表计算 |
| open_now | 无 | 比较 opening_hours |
| expires_in_minutes | expires_at | 计算 (expires_at - NOW()) / 60 |
| confirmation_count | 无 | 聚合 report_confirmations |

**缺点**：每次查询都需要额外计算，性能差。

---

## 推荐方案

**选择方案一（修改 Schema）**，理由：
1. 数据一致性更好
2. 查询性能更高
3. 后端代码改动最小
4. 符合"Schema 是数据源"的设计原则

---

## 执行顺序

| Step | 操作 | 负责人 | 状态 |
|------|------|--------|------|
| 1 | 修改 venues 枚举 | Data Lead | ⏳ |
| 2 | venues 新增字段 | Data Lead | ⏳ |
| 3 | user_reports 新增字段 | Data Lead | ⏳ |
| 4 | report_confirmations 新增字段 | Data Lead | ⏳ |
| 5 | busyness_scores 新增字段 | Data Lead | ⏳ |
| 6 | 新增 3 张表 | Data Lead | ⏳ |
| 7 | 更新 001_clearpath_schema.sql | Data Lead | ⏳ |
| 8 | 更新 mock_data.py | Backend Lead | ⏳ |
| 9 | 更新 API 响应序列化 | Backend Lead | ⏳ |
| 10 | 更新单元测试 | 协作 | ⏳ |

---

## API 层计算字段（无需存储）

| 字段 | 计算逻辑 |
|------|---------|
| distance_m | Haversine 公式 |
| busyness_color | 根据 score 映射颜色 |
| live_report_count | COUNT active reports |
| badge_text | 根据确认次数推导 |
| open_now | 比较 opening_hours |
| confirmation_count | COUNT confirmations |
| latest_action | 最新 confirmation action |
