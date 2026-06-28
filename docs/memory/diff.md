# alex ↔ main 分支冲突分析

> 分析日期：2026-06-24

## 分支概况

| 分支 | 主要工作 |
|------|----------|
| **alex** | Data+ML（busyness、venue coverage、DQR pipeline）、sprint task 文档 |
| **main** | 前端（web/mobile Profile、Medical ID、SOS、Map）、后端 API（auth、JWT、medical ID endpoints）、OpenAPI 合同 |

## 冲突文件清单与建议

### 配置文件

| 文件 | 冲突内容 | 建议 | 理由 |
|------|----------|------|------|
| `.gitignore` | alex 无新增，main 添加了 `.claude/`, `superpowers/`, `.vscode/` 等 | **保留 main** | main 的忽略规则更完整 |
| `pyproject.toml` | 两边都修改 | **保留 main** | main 有 PR review 过的依赖更新 |

### 后端核心

| 文件 | 冲突内容 | 建议 | 理由 |
|------|----------|------|------|
| `src/app.py` | 两边都修改 | **保留 main** | main 新增了 medical ID、auth 路由 |
| `src/auth.py` | 两边都修改 | **保留 main** | main 实现了 JWT bearer auth |
| `src/settings.py` | 两边都修改 | **保留 main** | main 有更完整的配置 |
| `src/db.py` | 两边都修改 | **保留 alex** | alex 的 DQR pipeline 数据库改动是独立的 |
| `src/api/auth.py` | 两边都修改 | **保留 main** | main 实现了完整的 login/token 端点 |

### 前端

| 文件 | 冲突内容 | 建议 | 理由 |
|------|----------|------|------|
| `frontend/web/src/pages/Profile.jsx` | 两边都修改 | **保留 main** | main 有 PR review 过的完整实现 |
| `frontend/web/src/data/userProfile.js` | alex 无实质改动 | **保留 main** | main 的 mock data 更完整 |
| `frontend/mobile/src/types/medical.ts` | 两边都修改 | **保留 main** | main 新增了 emergency contact 类型 |
| `frontend/mobile/src/data/mockMedicalId.ts` | 两边都修改 | **保留 main** | main 的 mock 数据更完整 |

### API 合同

| 文件 | 冲突内容 | 建议 | 理由 |
|------|----------|------|------|
| `openapi.yaml` | 两边都修改 | **保留 main** | main 有 v1.4.2 更新（medical ID + emergency contacts） |

### 文档

| 文件 | 冲突内容 | 建议 | 理由 |
|------|----------|------|------|
| `docs/memory/project-issues.md` | 两边都修改 | **保留 main** | main 的 issue tracking 更完整 |
| `docs/memory/execution-plan.md` | 两边都修改 | **保留 main** | main 有最新的 sprint 计划 |
| `docs/memory/[saved]sprint-tasks-1-4.md` | 两边都修改 | **保留 main** | main 有最新的 task 状态 |

### Data+ML

| 文件 | 冲突内容 | 建议 | 理由 |
|------|----------|------|------|
| `Data+ML/test/6.8-6.12_DB/dqr_cleaning_pipeline.ipynb` | 两边都修改 | **保留 alex** | alex 的 DQR pipeline 改动是独立工作 |

## 合并策略建议

**推荐：以 main 为基准，将 alex 的 Data+ML 改动 cherry-pick 过来**

```bash
# 1. 切到 main 分支
git checkout main
git pull origin main

# 2. 将 alex 的 Data+ML 相关 commit cherry-pick 过来
git cherry-pick de04557  # 6.24 busyness funcion preparation
git cherry-pick 467fcfb  # 6.17 busyness overview update
git cherry-pick 15ebbbf 9.15 venue_cover busyness resource analysis
git cherry-pick cd0e920  # 6.13 notebook separated into py files

# 3. 处理可能的冲突（主要是 Data+ML 文件）
# 4. push 到 main
```

**或者：直接用 main 覆盖冲突文件**

```bash
# 在 alex 分支上，用 main 的版本覆盖冲突文件
git checkout origin/main -- .gitignore pyproject.toml src/app.py src/auth.py \
  src/settings.py src/api/auth.py openapi.yaml \
  frontend/web/src/pages/Profile.jsx frontend/web/src/data/userProfile.js \
  frontend/mobile/src/types/medical.ts frontend/mobile/src/data/mockMedicalId.ts \
  docs/memory/

# 保留 alex 的
# src/db.py (数据库相关)
# Data+ML/test/6.8-6.12_DB/dqr_cleaning_pipeline.ipynb
```

## 注意事项

1. `.DS_Store` 冲突可以忽略，已在 `.gitignore` 中
2. 合并前建议先备份当前 alex 分支：`git branch alex-backup`
3. 如果选择以 main 为主，alex 分支的 Data+ML 工作需要确认是否已合入 main
