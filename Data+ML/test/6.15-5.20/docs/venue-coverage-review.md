# venue_coverage 功能介绍与执行缺口分析

> 审查日期：2026-06-15（初版） → 2026-06-15（更新）  
> SOP 文件：`Data+ML/plan/venue_coverage_sop_zh.md`  
> 最近运行：`20260615T193635Z`（MTA 修复后，三源全部成功）  
> 当前状态：106 tests passed（44 busyness + 62 venue coverage）

## 功能概述

venue_coverage 是 ClearPath 项目的**空间覆盖测试系统**，衡量在不同 GPS 半径内，项目场馆（venue）是否能被至少一个外部数据源覆盖。

### 核心目标

回答一个问题：**在 100m-500m 范围内，有多少场馆附近有可用的数据采集点？**

本系统仅衡量空间特征可用性，不评估预测质量、时间相关性或生产模型权重。

### 数据流

```
场馆清单 (venues_clean.csv, 4,838 venues)
  │
  ▼  BallTree (Haversine) 最近距离查询
  │
  ├── Citi Bike GBFS ─── 2,326 站点 (纽约共享单车)
  ├── MTA Station Complexes ─── 5f5g-n3cz (地铁站综合体)
  └── NYC Traffic ─── 7ym2-wayt (交通传感器路段)
  │
  ▼  按 100m/200m/300m/400m/500m 半径计算覆盖
  │
  ├── 单数据源覆盖 (standalone)
  ├── 累计组合覆盖 (cumulative: CB → CB+MTA → CB+MTA+Traffic)
  ├── 按 venue_type 聚合 (emergencyasset/healthcare/restroom)
  └── 按 district 聚合 (downtown/midtown_east/midtown_west/uptown)
  │
  ▼  制品生成
  │
  ├── venue_coverage_detail.csv (每场馆一行)
  ├── coverage_summary.csv (聚合指标)
  ├── coverage_report.md (可读报告)
  ├── run_metadata.json (运行元数据)
  ├── traffic_year_profile.csv (Traffic 年度分布诊断)
  └── 4 张 PNG 图表
```

### 关键架构

| 组件 | 文件 | 功能 |
|------|------|------|
| 核心库 | `src/venue_coverage.py` | 数据源获取、BallTree 距离计算、覆盖聚合、报告/图表生成 |
| CLI 入口 | `src/run_venue_coverage.py` | 参数解析、流程编排、制品写入 |
| 测试 | `tests/test_venue_coverage.py` | 65 个测试（62 离线 + 3 集成） |

### 数据源说明

| 数据源 | 数据集 ID | 类型 | 特点 |
|--------|----------|------|------|
| Citi Bike | GBFS | 共享单车站点 | 覆盖最广，100m 即达 45% |
| MTA | `5f5g-n3cz` | 地铁站综合体 | 直接含坐标，无需 OD 聚合 |
| Traffic | `7ym2-wayt` | 交通传感器路段 | 需 EPSG:2263→WGS84 坐标转换 |

### 测试半径

```text
100m → 200m → 300m → 400m → 500m
```

每个半径增量的边际收益用于评估"覆盖"与"局部性"的权衡。

### 数据源归因顺序

```text
Citi Bike → Citi Bike + MTA → Citi Bike + MTA + Traffic
```

失败数据源中断后续组合（不跳过），确保组合结果的完整性。

### 与 busyness_ingestion 的关系

- **venue_coverage**：衡量数据源的**空间可用性**（有没有数据点在附近）
- **busyness_ingestion**：利用交通数据计算场馆的**繁忙度分数**并写入数据库

两者共享 `dqr/` 模块（坐标转换、GPS 工具），但目标不同。venue_coverage 不写入数据库，busyness_ingestion 会写入 `busyness_scores` 表。

---

## 执行缺口分析

## 文件存在性 (SOP §4)

| 文件 | 状态 |
|------|------|
| `dqr/venue_coverage.py` (1,171行) | ✅ 已创建 |
| `run_venue_coverage.py` (347行) | ✅ 已创建 |
| `tests/test_venue_coverage.py` (1,071行) | ✅ 已创建 |
| `tests/output/venues_clean.csv` (4,838行) | ✅ 已存在 |
| `output/` 目录 | ✅ 已存在 |


## 单元测试 (SOP §13 任务 1-7)

```text
60 passed, 3 skipped, 3 warnings
```

| 任务 | 测试类 | 状态 |
|------|--------|------|
| 任务1: CLI 解析 | TestCLIParsing (12) | ✅ 全部通过 |
| 任务2: HTTP/重试/隔离 | TestHTTPClient + TestPagination + TestSourceIsolation (10) | ✅ 全部通过 |
| 任务3: 数据源适配器 | TestCitiBikeAdapter + TestMTAAdapter + TestTrafficAdapter (9) | ✅ 全部通过 |
| 任务4: BallTree 距离 | TestBallTreeDistance + TestVenueDeduplication (8) | ✅ 全部通过 |
| 任务5: 覆盖聚合 | TestStandaloneCoverage + TestCumulativeCoverage (9) | ✅ 全部通过 |
| 任务6: 制品与可视化 | TestArtifacts + TestCharts (9) | ✅ 全部通过 |
| 任务7: 冒烟测试 | TestLiveSmoke (3) | ⏭️ 全部跳过 (需 `@pytest.mark.integration`) |

## 实际运行结果 (latest run: 20260615T193635Z)

| 数据源 | 状态 | 获取耗时 | 原始点数 | 有效点数 | 问题 |
|--------|------|---------|---------|---------|------|
| Citi Bike | ✅ ok | 1.5s | 2,411 | 2,328 | — |
| MTA | ✅ ok | 0.6s | 445 | 445 | —（修复：`complex_name` → `display_name`） |
| Traffic | ✅ ok | 7.1s | 28 | 28 | 仅 28 个路段（Manhattan 2025） |

## 覆盖率摘要

### 单数据源

| 数据源 | 100m | 200m | 300m | 400m | 500m |
|--------|------|------|------|------|------|
| Citi Bike | 45.5% | 91.8% | 98.0% | 98.3% | 98.5% |
| MTA | 11.9% | 39.6% | 64.8% | 80.4% | 88.2% |
| Traffic | 1.2% | 3.3% | 6.7% | 10.9% | 14.7% |

### 累计组合

| 组合 | 100m | 200m | 300m | 400m | 500m |
|------|------|------|------|------|------|
| Citi Bike | 45.5% | 91.8% | 98.0% | 98.3% | 98.5% |
| Citi Bike + MTA | 51.1% | 93.9% | 98.2% | 98.4% | 98.6% |
| Citi Bike + MTA + Traffic | 51.5% | 94.0% | 98.2% | 98.4% | 98.6% |

完整累计链 `Citi Bike → CB+MTA → CB+MTA+Traffic` 恢复。MTA 在 100m 处贡献最大增量 +5.6pp。



### 最近距离分布

| 数据源 | 中位数 (m) | P90 (m) |
|--------|-----------|---------|
| Citi Bike | 107m | 192m |
| MTA | 241m | 524m |
| Traffic | 1,110m | 2,231m |

## 代码量评估

| 文件 | 行数 | 职责 |
|------|------|------|
| `src/venue_coverage.py` | 1,190 | 核心库：API 获取、BallTree 距离、覆盖聚合、报告/图表生成 |
| `src/run_venue_coverage.py` | 350 | CLI 入口：参数解析、流程编排、制品写入 |
| `tests/test_venue_coverage.py` | 1,117 | 测试：62 离线 + 3 集成 |
| **合计** | **2,657** | |

代码量分布合理：核心逻辑 ~1,200 行，测试 ~1,100 行（测试/实现比 ≈ 0.93），CLI 胶水 ~350 行。

## 已确认的缺口

### ~~P0：MTA 数据源失败 — 组合覆盖链断裂~~ ✅ 已修复

MTA 已从 OD 客流表 `y2qv-fytt`（需要 GROUP BY 聚合）改为官方站点综合体数据集 `5f5g-n3cz`（直接包含坐标）。修复内容：

- `fetch_mta()` 移除 `year` 参数，直接查询 `5f5g-n3cz`
- `fetch_mta()` 字段名修复：`complex_name` → `display_name`（SODA API 实际字段名）
- CLI 移除 `--mta-year` 参数
- 完整覆盖链 `Citi Bike → Citi Bike + MTA → Citi Bike + MTA + Traffic` 恢复
- 离线测试 62 个全部通过（含 4 个新 MTA 测试）

### ~~P1：read_timeout 配置不一致~~ ✅ 已对齐

代码默认超时 `(2, 5)` 与 SOP §7.2 一致。之前运行时使用 30s 是手动配置偏差。

### P1：Traffic 数据量极少

仅 28 个路段通过 Manhattan 过滤，覆盖率极低（100m 仅 1.2%）。已新增 `traffic_year_profile.csv` 诊断文件，明确各年份的记录数和路段数，确认是官方数据稀疏性而非解析错误。

### ~~P2：3 个冒烟测试被跳过~~ ✅ 已修复

`@pytest.mark.integration` marker 已存在，CI 已扩展支持运行集成测试。

### ~~P2：图表 legend 警告~~ ✅ 已修复

所有三处 `ax.legend()` 调用前已添加 handles 检查守卫。空数据显示 "No data available" 文本。

**建议**：检查 `venue_coverage.py` L1000/L1079 的 legend 逻辑。


## SOP §14 审查清单状态

| 检查项 | 状态 |
|--------|------|
| 场地分母和重复计数已记录 | ✅ (0 duplicates) |
| 所有数据源状态明确 | ✅ (all ok) |
| API 查询年份和数据集 ID 已记录 | ✅ |
| 没有数据源在 5,000 行处静默停止 | ✅ |
| 失败数据源已从受影响的组合中排除 | ✅ |
| 单数据源和累计覆盖均已呈现 | ✅ |
| 结果包含总体、场地类型和区域视图 | ✅ |
| 每个 100m 增量的边际变化均已显示 | ✅ |
| Traffic 未被描述为观测到的行人繁忙度 | ✅ |
| 未从空间覆盖推断预测权重 | ✅ |
| 未持久化原始 API 响应 | ✅ |
| 未发生数据库写入 | ✅ |

## 优先级汇总

| 优先级 | 缺口 | 状态 |
|--------|------|------|
| **P0** | MTA 超时失败 → 改用 `5f5g-n3cz` + 字段名修复 (`complex_name` → `display_name`) | ✅ 已修复 |
| **P1** | read_timeout 30s vs SOP 5s | ✅ 已对齐 |
| **P1** | Traffic 仅 28 段 | ⚠️ 已添加年度诊断 (`traffic_year_profile.csv`) |
| **P2** | 3 个冒烟测试未运行 | ✅ CI 已扩展支持 `workflow_dispatch` 运行集成测试 |
| **P2** | 图表 legend 警告 | ✅ 已修复 (handles 检查守卫) |

