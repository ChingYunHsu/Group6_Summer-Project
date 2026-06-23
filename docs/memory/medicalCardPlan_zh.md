## 医疗卡计划（最小实现版）

**目标**：只实现一个可用、可同步、可加密存储的用户医疗资料后端能力。  
**原则**：最小功能、最少代码、无多余防御、无兜底分支、无兼容旧路径。

### 1. 范围

- 只做后端、OpenAPI、数据库迁移和最少量测试。
- 不做 iOS / Android / Web UI 改造。
- 不做离线缓存、本地存储、历史版本、审计日志、回滚、冲突合并。
- 不做字段级加密、端到端加密、KMS、刷新令牌、令牌轮换、撤销列表。

### 2. 数据模型

只新增一张表：`user_medical_profiles`。

必须字段：

- `user_id`，主键，同时是外键，引用 `users(user_id)`
- `blood_type`
- `donor_status`
- `severe_allergies` JSON
- `conditions` JSON
- `medications` JSON
- `emergency_contacts` JSON
- `emergency_notes`
- `medical_pass_title`
- `created_at`
- `updated_at`

约束：

- `ON DELETE CASCADE`
- `ENCRYPTION='Y'`
- 不额外加触发器、视图、冗余表、索引优化表

### 3. 认证与访问

- 认证直接复用现有 `users` 表。
- 登录成功只返回一个 `access_token`。
- 医疗资料接口只认当前 JWT，不接受 `user_id` 入参。
- 不加备用认证路径，不加 guest 兜底，不加匿名写入。

### 4. API

只保留 3 个接口：

- `GET /api/v1/user/medical-profile`
- `PUT /api/v1/user/medical-profile`
- `DELETE /api/v1/user/medical-profile`

语义尽量简单：

- `GET`：有记录就返回，没有就返回空对象
- `PUT`：整行覆盖 / upsert
- `DELETE`：删除当前用户记录

不要增加：

- 部分更新
- patch 合并
- 状态机
- 草稿态
- 历史版本
- 兜底默认模板以外的额外分支

### 5. 字段边界

只把 Tier 2 医疗资料放进 `user_medical_profiles`。

保留在 `users` / 现有用户资料层的字段：

- `date_of_birth`
- `gender`
- `address`
- 其他基础账户资料

不要重复存储，不要同步两份来源，不要加字段映射缓存层。

### 6. 实施顺序

1. 先加 `user_medical_profiles` 表
2. 再接入最小认证读取
3. 再加 3 个 API
4. 最后补 OpenAPI 和最少测试

### 7. 测试

只保留核心测试：

- JWT 可以访问医疗资料接口
- `PUT` 能写入
- `GET` 能读回
- `DELETE` 能删掉
- `ON DELETE CASCADE` 生效
- 表加密配置存在

不写过度测试：

- 不测大量边界输入
- 不测复杂错误恢复
- 不测兼容旧字段
- 不测多端同步竞争

### 8. 代码原则

- 一个功能只保留一条主路径
- 失败就返回错误，不做自动修复
- 不写“看情况兜底”的逻辑
- 不写重复校验
- 不写与当前需求无关的抽象层
- 不预留暂时用不到的扩展点

### 9. 预期结果

交付后应满足：

- 用户可以登录
- 用户可以保存自己的医疗资料
- 用户可以读取和删除自己的医疗资料
- 数据落库到加密表
- 现有账号体系不被破坏

