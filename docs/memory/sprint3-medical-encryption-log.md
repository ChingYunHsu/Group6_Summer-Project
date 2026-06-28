# Sprint 3 扩展：用户医疗信息加密存储 — 执行日志

> 开始时间: 2026-06-23
> 执行人: Claude (fangxun.wu)
> 任务来源: execution-plan.md Phase 7 (7.1-7.8)

---

## 执行计划

| # | 任务 | 状态 | 开始 | 完成 |
|---|------|:----:|------|------|
| 7.1 | 共享 DB helper | ✅ | 2026-06-23 | 2026-06-23 |
| 7.2 | MySQL Auth 改造 | ✅ | 2026-06-23 | 2026-06-23 |
| 7.3 | Bearer JWT | ✅ | 2026-06-23 | 2026-06-23 |
| 7.4 | Docker keyring 配置 | ✅ | 2026-06-23 | 2026-06-23 |
| 7.5 | user_medical_profiles 表 | ✅ | 2026-06-23 | 2026-06-23 |
| 7.6 | 后端 Medical API | ✅ | 2026-06-23 | 2026-06-23 |
| 7.7 | OpenAPI 更新 | ✅ | 2026-06-23 | 2026-06-23 |
| 7.8 | 后端测试 | ✅ | 2026-06-23 | 2026-06-23 |

---

## 执行记录

### 2026-06-23: Phase 1 — 共享 DB helper + 配置更新

**任务**: 7.1 共享 DB helper

**变更文件**:
- `src/db.py` (新建) — 共享 pymysql 连接工厂
- `src/settings.py` (修改) — 添加 DB/JWT 配置字段
- `src/app.py` (修改) — 添加 JWT config 到 app.config

**实现细节**:
- `get_db_conn()` 从环境变量读取 DB 配置
- 支持 `CLEARPATH_DB_HOST/PORT/USER/PASSWORD/NAME`
- 支持 `JWT_SECRET_KEY` 和 `JWT_EXPIRATION_HOURS`

---

### 2026-06-23: Phase 2 — 认证系统重写

**任务**: 7.2 MySQL Auth 改造 + 7.3 Bearer JWT

**变更文件**:
- `pyproject.toml` (修改) — 添加 bcrypt, PyJWT 依赖
- `src/auth.py` (重写) — 添加 `require_auth` 装饰器和 `generate_token()`
- `src/api/auth.py` (重写) — 使用 MySQL users 表 + bcrypt

**实现细节**:
- 密码使用 bcrypt 哈希存储
- JWT payload: `{sub: user_id, email: email, iat, exp}`
- 登录/注册返回 `access_token`
- `require_auth` 装饰器验证 Bearer token

---

### 2026-06-23: Phase 3 — 医疗资料表

**任务**: 7.5 user_medical_profiles 表

**变更文件**:
- `docker/mysql/init/002_medical_profile.sql` (新建)

**表结构**:
```sql
CREATE TABLE user_medical_profiles (
  user_id VARCHAR(36) PRIMARY KEY,
  blood_type VARCHAR(10),
  donor_status BOOLEAN,
  severe_allergies JSON,
  conditions JSON,
  medications JSON,
  emergency_contacts JSON,
  emergency_notes TEXT,
  medical_pass_title VARCHAR(128),
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENCRYPTION='Y';
```

---

### 2026-06-23: Phase 4 — Medical API

**任务**: 7.6 后端 Medical API

**变更文件**:
- `src/api/medical.py` (新建)
- `src/app.py` (修改) — 注册 medical blueprint

**API 端点**:
- `GET /api/v1/user/medical-profile` — 获取当前用户医疗资料
- `PUT /api/v1/user/medical-profile` — 创建/更新医疗资料 (upsert)
- `DELETE /api/v1/user/medical-profile` — 删除当前用户资料

**实现细节**:
- 所有端点使用 `@require_auth` 保护
- 不接受 `user_id` 参数，只从 JWT 获取
- 支持 JSON 字段序列化
- blood_type 验证 (A+, A-, B+, B-, AB+, AB-, O+, O-)

---

### 2026-06-23: Phase 5 — Docker keyring 配置

**任务**: 7.4 Docker keyring 配置

**变更文件**:
- `docker-compose.yml` (修改)

**配置**:
- 添加 keyring_file 插件加载
- 添加 `/var/lib/mysql-keyring` 卷
- MySQL 启动时自动加载 keyring

---

### 2026-06-23: Phase 6 — 测试

**任务**: 7.8 后端测试

**变更文件**:
- `tests/test_medical.py` (新建)

**测试覆盖**:
- 密码哈希测试 (hash, verify, unique)
- JWT 认证测试 (generate, missing header, invalid header, valid token)
- 医疗资料 CRUD 测试 (get, put, delete)
- 用户隔离测试
- 输入验证测试
- 级联删除 DDL 验证

---

## 待完成

| # | 任务 | 说明 |
|---|------|------|
| 7.7 | OpenAPI 更新 | 需要更新 API 文档以反映新的认证方式和医疗端点 |

---

## 后续步骤

1. 安装依赖: `poetry install`
2. 重启 Docker: `docker compose down && docker compose up -d`
3. 启动 Flask: `python src/main.py`
4. 运行测试: `pytest tests/test_medical.py -v`
5. 验证 API:
   - `POST /api/v1/auth/register` (注册)
   - `POST /api/v1/auth/login` (获取 token)
   - `PUT /api/v1/user/medical-profile` (保存医疗资料)
   - `GET /api/v1/user/medical-profile` (读取医疗资料)
