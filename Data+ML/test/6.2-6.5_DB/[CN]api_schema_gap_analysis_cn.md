# ClearPath API 与数据库 Schema 差距分析

**日期（Date）:** 2026-06-02  
**数据来源（Sources）:** `src/mock_data.py`、Team6_Contract.pdf（端点共享契约）、`docker/mysql/init/001_clearpath_schema.sql`

---

## 1. 概述（Overview）

本文档合并了两份分析：

1. **API 契约 vs Schema** — 从共享 PDF 契约到 MySQL 表的字段级映射。
2. **模拟数据 vs Schema** — 从 `src/mock_data.py` 到 MySQL 表的字段级映射。

目标：识别每个差距（gap），判断需要 Schema 变更还是 API 层解决，并给出统一的优先级实施计划。

---

## 2. 场所字段映射（Field Mapping — Venues）

### 2.1 GET /api/v1/venues（场所列表）

| API 字段 | 类型 | Mock 数据字段 | 数据库列 | 状态 |
|-----------|------|--------------|----------|------|
| venue_id | string | venue_id | venues.venue_id | ✅ 已对齐 |
| name | string | name | venues.name | ✅ 已对齐 |
| category | string | venue_type | venues.venue_type | ⚠️ 枚举值需对齐 |
| lat | number | latitude | venues.latitude | ✅ 已对齐 |
| lng | number | longitude | venues.longitude | ✅ 已对齐 |
| distance_m | number | — | — | ✅ API 层计算，无需存储 |
| address | string | — | venues.address | ✅ 已对齐 |
| **accessibility.wheelchair_friendly** | bool | accessible_status | — | ❌ **需新增表** |
| **accessibility.step_free_route** | bool | accessibility_features | — | ❌ **需新增表** |
| **accessibility.accessible_toilet** | bool | accessibility_features | — | ❌ **需新增表** |
| **accessibility.entrance_width_cm** | int | — | — | ❌ **需新增表** |
| **warnings.active_warning** | bool | active_warning | — | ❌ **需从报告推导** |
| **warnings.warning_detail** | string | — | — | ❌ **需新增表** |
| **warnings.wait_alert** | bool | — | — | ❌ **需新增表** |
| **warnings.replacement_suggestion** | object[] | — | — | ❌ **需新增表** |
| **language.language_tag** | string[] | language_tags | — | ❌ **需新增表** |
| **language.language_support_level** | string | — | — | ❌ **需新增表** |
| **language.chatbot_enabled** | bool | — | — | ❌ **需新增表** |
| **language.chatbot_welcoming_message** | string | — | — | ❌ **需新增表** |
| **busyness.busyness_score** | int | busyness_percent | busyness_scores.score | ✅ 已对齐 |
| **busyness.busyness_status** | string | busyness_level | busyness_scores.level | ⚠️ 枚举映射需确认 |
| **busyness.busyness_color** | string | — | — | ✅ API 层计算 |
| **busyness.estimated_wait_minutes** | int | avg_wait_minutes | busyness_scores.estimated_wait_minutes | ✅ 已对齐 |
| **busyness.forecast_1h** | int | — | — | ❌ **需新增列** |
| **busyness.forecast_4h** | int | — | — | ❌ **需新增列** |
| **busyness.forecast_8h** | int | — | — | ❌ **需新增列** |

### 2.2 GET /api/v1/venues/{venue_id}（场所详情 — 额外字段）

| API 字段 | 类型 | Mock 数据字段 | 数据库列 | 状态 |
|-----------|------|--------------|----------|------|
| phone | string | — | venues.phone | ✅ 已对齐 |
| hours | string | — | venues.opening_hours | ✅ 已对齐 |
| **photos** | string[] | — | — | ❌ **需新增列** |
| **rating** | float | — | — | ❌ **需新增列** |
| source | string | — | venues.source_confidence | ⚠️ 字段名不匹配 |
| data_confidence | float | — | venues.source_confidence | ✅ 已对齐 |
| created_at | string | — | venues.created_at | ✅ 已对齐 |
| open_now | bool | open_now | — | ⚠️ **API 层计算** |
| weather_risk | string | weather_risk | — | ❌ **需新增列或计算** |

---

## 3. 报告字段映射（Field Mapping — Reports）

### 3.1 POST /api/v1/reports（创建报告）

| API 字段 | 类型 | Mock 数据字段 | 数据库列 | 状态 |
|-----------|------|--------------|----------|------|
| issue_type | string | issue_type | user_reports.issue_type | ⚠️ 枚举值需对齐 |
| venue_id | string | venue_id | user_reports.venue_id | ✅ 已对齐 |
| lat | number | latitude | user_reports.latitude | ✅ 已对齐 |
| lng | number | longitude | user_reports.longitude | ✅ 已对齐 |
| accuracy_m | number | — | user_reports.accuracy_meters | ⚠️ 字段名不匹配 |
| **anonymous** | bool | reported_by | — | ❌ **需新增列** |
| **description** | string | — | — | ❌ **需新增列** |
| **photos** | string[] | — | — | ❌ **需新增列** |

### 3.2 GET /api/v1/reports（报告列表）

| API 字段 | 类型 | Mock 数据字段 | 数据库列 | 状态 |
|-----------|------|--------------|----------|------|
| report_id | string | report_id | user_reports.report_id | ✅ 已对齐 |
| issue_type | string | issue_type | user_reports.issue_type | ✅ 已对齐 |
| venue_id | string | venue_id | user_reports.venue_id | ✅ 已对齐 |
| venue_name | string | — | — | ✅ JOIN venues.name |
| venue_category | string | — | — | ✅ JOIN venues.venue_type |
| lat | number | latitude | user_reports.latitude | ✅ 已对齐 |
| lng | number | longitude | user_reports.longitude | ✅ 已对齐 |
| accuracy_m | number | — | user_reports.accuracy_meters | ⚠️ 字段名不匹配 |
| status | string | status | user_reports.status | ✅ 已对齐 |
| created_at | string | created_at | user_reports.created_at | ✅ 已对齐 |
| expires_at | string | expires_in_minutes | user_reports.expires_at | ⚠️ 格式不同（时间戳 vs 时长） |
| **confirmations.count** | int | confirmation_count | — | ❌ **需聚合查询** |
| **confirmations.latest_action** | string | — | — | ❌ **需 JOIN report_confirmations** |
| **confirmations.latest_action_at** | string | — | — | ❌ **需 JOIN report_confirmations** |
| **photos** | string[] | — | — | ❌ **需新增列** |
| **language.default_language** | string | — | — | ❌ **需新增列** |
| **language.fallback_language** | string | — | — | ❌ **需新增列** |
| live_report_count | int | live_report_count | — | ⚠️ **计算字段：统计活跃报告数** |
| badge_text | string | badge_text | — | ⚠️ **API 层计算** |

### 3.3 POST /api/v1/reports/{report_id}/confirmations（报告确认）

| API 字段 | 类型 | Mock 数据字段 | 数据库列 | 状态 |
|-----------|------|--------------|----------|------|
| report_id | string | — | report_confirmations.report_id | ✅ 已对齐 |
| action | string | — | report_confirmations.action | ⚠️ 枚举值需对齐 |
| **language** | string | — | — | ❌ **需新增列** |

### 3.4 GET /api/v1/integrations/status（集成状态）

无直接数据库映射。返回外部服务连接状态。

---

## 4. Schema 变更清单（Required Schema Changes）

### 4.1 `venues` 表新增字段（场所表）

```sql
-- 新增联系信息（电话、照片、评分）
ALTER TABLE venues ADD COLUMN phone VARCHAR(64) AFTER opening_hours;
ALTER TABLE venues ADD COLUMN photos JSON AFTER phone;
ALTER TABLE venues ADD COLUMN rating DECIMAL(3,2) AFTER photos;

-- 新增天气风险等级
ALTER TABLE venues ADD COLUMN weather_risk ENUM('low', 'medium', 'high') DEFAULT 'low' AFTER rating;

-- 新增语言支持字段
ALTER TABLE venues ADD COLUMN language_tags JSON AFTER borough;
ALTER TABLE venues ADD COLUMN primary_language VARCHAR(10) AFTER language_tags;
ALTER TABLE venues ADD COLUMN secondary_language VARCHAR(10) AFTER primary_language;

-- 新增无障碍状态字段
ALTER TABLE venues ADD COLUMN accessible_status ENUM('full_access', 'partial', 'step_free_route_only', 'none') DEFAULT 'none' AFTER secondary_language;
ALTER TABLE venues ADD COLUMN accessibility_features JSON AFTER accessible_status;

-- 新增预警字段
ALTER TABLE venues ADD COLUMN active_warning BOOLEAN DEFAULT FALSE AFTER accessibility_features;
```

### 4.2 `user_reports` 表新增字段（用户报告表）

```sql
-- 新增匿名、描述、照片字段
ALTER TABLE user_reports ADD COLUMN anonymous BOOLEAN DEFAULT FALSE AFTER accuracy_meters;
ALTER TABLE user_reports ADD COLUMN description TEXT AFTER anonymous;
ALTER TABLE user_reports ADD COLUMN photos JSON AFTER description;
ALTER TABLE user_reports ADD COLUMN reported_by VARCHAR(50) DEFAULT 'anonymous' AFTER photos;

-- 新增多语言支持字段
ALTER TABLE user_reports ADD COLUMN default_language VARCHAR(10) AFTER reported_by;
ALTER TABLE user_reports ADD COLUMN fallback_language VARCHAR(10) AFTER default_language;
```

### 4.3 `report_confirmations` 表新增字段（报告确认表）

```sql
ALTER TABLE report_confirmations ADD COLUMN language VARCHAR(10) AFTER action;
```

### 4.4 `busyness_scores` 表新增字段（拥挤度预测表）

```sql
-- 新增 1h/4h/8h 未来预测字段
ALTER TABLE busyness_scores ADD COLUMN forecast_1h INT AFTER estimated_wait_minutes;
ALTER TABLE busyness_scores ADD COLUMN forecast_4h INT AFTER forecast_1h;
ALTER TABLE busyness_scores ADD COLUMN forecast_8h INT AFTER forecast_4h;
```

### 4.5 新增表：`venue_accessibility`（场所无障碍表）

```sql
CREATE TABLE IF NOT EXISTS venue_accessibility (
    venue_id VARCHAR(36) PRIMARY KEY,
    wheelchair_friendly BOOLEAN DEFAULT FALSE,
    step_free_route BOOLEAN DEFAULT FALSE,
    accessible_toilet BOOLEAN DEFAULT FALSE,
    entrance_width_cm INT,
    CONSTRAINT fk_accessibility_venue
        FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);
```

### 4.6 新增表：`venue_language`（场所语言表）

```sql
CREATE TABLE IF NOT EXISTS venue_language (
    venue_id VARCHAR(36) PRIMARY KEY,
    language_tag JSON,
    language_support_level ENUM('full', 'partial', 'none') DEFAULT 'none',
    chatbot_enabled BOOLEAN DEFAULT FALSE,
    chatbot_welcoming_message TEXT,
    CONSTRAINT fk_language_venue
        FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);
```

### 4.7 新增表：`venue_warnings`（场所预警表）

```sql
CREATE TABLE IF NOT EXISTS venue_warnings (
    venue_id VARCHAR(36) PRIMARY KEY,
    active_warning BOOLEAN DEFAULT FALSE,
    warning_detail TEXT,
    wait_alert BOOLEAN DEFAULT FALSE,
    replacement_suggestion JSON,
    CONSTRAINT fk_warnings_venue
        FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
);
```

---

## 5. API 层计算字段（无需 Schema 变更）

以下字段出现在 API 响应中，但应在**运行时计算**，而非存储：

| 字段（Field） | 计算逻辑（Computation） |
|---------------|------------------------|
| `distance_m` | Haversine 公式：根据用户位置到场所的距离计算 |
| `busyness_color` | 根据 busyness_score 映射颜色（绿/黄/橙/红） |
| `live_report_count` | `SELECT COUNT(*) FROM user_reports WHERE venue_id = ? AND status = 'active'` |
| `badge_text` | 根据确认次数和报告状态推导 |
| `open_now` | 比较 `opening_hours` 与当前时间 |
| `confirmations.count` | `SELECT COUNT(*) FROM report_confirmations WHERE report_id = ?` |
| `confirmations.latest_action` | `SELECT action FROM report_confirmations WHERE report_id = ? ORDER BY created_at DESC LIMIT 1` |
| `venue_name` / `venue_category` | JOIN `venues` 表获取 |

---

## 6. 总结（Summary）

| 类别（Category） | 新增列 | 新增表 | API 层计算 |
|------------------|--------|--------|-----------|
| `venues` 场所表 | +10 字段 | — | 1（open_now） |
| `user_reports` 用户报告表 | +6 字段 | — | 2（live_report_count, badge_text） |
| `report_confirmations` 报告确认表 | +1 字段 | — | 1（language） |
| `busyness_scores` 拥挤度表 | +3 字段 | — | — |
| `venue_accessibility` 无障碍表 | — | ✅ 新增表 | — |
| `venue_language` 语言表 | — | ✅ 新增表 | — |
| `venue_warnings` 预警表 | — | ✅ 新增表 | — |
| 计算字段（Computed） | — | — | +8 字段 |

---

## 7. 下一步（Next Steps）

1. 更新 Docker 初始化 SQL（`docker/mysql/init/001_clearpath_schema.sql`），应用所有 Schema 变更。
2. 对齐 `src/mock_data.py`，匹配新增的数据库字段。
3. 更新 `src/api/venues.py` 和 `src/api/reports.py` 中的 API 响应序列化。
4. 在 `tests/test_database_plan.py` 中新增表和字段的单元测试。
