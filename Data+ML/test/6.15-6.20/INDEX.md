# Busyness & Venue Coverage — 文件索引

> 整理日期：2026-06-15  
> 来源目录：`Data+ML/test/6.8-6.12_DB/`

## 目录结构

```text
6.15-5.20/
├── src/                          # 源代码
│   ├── busyness_ingestion.py     # Busyness ETL 管道 (440行)
│   ├── venue_coverage.py         # 空间覆盖测试核心 (1,190行)
│   └── run_venue_coverage.py     # CLI 入口 (350行)
├── tests/                        # 测试文件
│   ├── conftest.py               # Pytest 共享 fixtures
│   ├── test_busyness_ingestion.py  # Busyness 测试 (44 tests)
│   └── test_venue_coverage.py      # 覆盖测试 (65 tests)
├── output/                       # 运行输出
│   └── venue_coverage/           # 最近一次覆盖运行结果
│       ├── venue_coverage_detail.csv
│       ├── coverage_summary.csv
│       ├── coverage_report.md
│       ├── run_metadata.json
│       ├── coverage_by_radius.png
│       ├── incremental_coverage.png
│       ├── venue_type_coverage_heatmap.png
│       └── uncovered_venue_distribution.png
└── docs/                         # 文档与审查
    ├── venue_coverage_sop_zh.md  # 空间覆盖 SOP (中文)
    ├── busynessreview.md         # Busyness 代码审查笔记
    └── venue-coverage-review.md  # 覆盖测试执行缺口分析
```

> **依赖**：`src/` 下的源文件通过 `sys.path` 引用 `Data+ML/test/6.8-6.12_DB/dqr/` 共享模块，不重复存放。

## 文件说明

### 源代码

| 文件 | 行数 | 功能 |
|------|------|------|
| `busyness_ingestion.py` | 440 | NYC 交通数据 → venue busyness 分数的 ETL 管道 |
| `venue_coverage.py` | 1,190 | Citi Bike / MTA / Traffic 空间覆盖测试核心 |
| `run_venue_coverage.py` | 350 | 覆盖测试 CLI 入口，支持 `--radii`, `--sources` 等参数 |

### 测试

| 文件 | 测试数 | 覆盖范围 |
|------|--------|---------|
| `test_busyness_ingestion.py` | 44 (44 pass) | 分类、GPS转换、距离、聚合、venue匹配、预测、DB写入、API获取、pipeline |
| `test_venue_coverage.py` | 65 (62 pass, 3 skip) | CLI、HTTP重试、数据源适配器、BallTree、覆盖聚合、制品契约、图表、MTA站点综合体、Traffic年度诊断 |

### 输出 (latest run: 20260615T150606Z)

| 数据源 | 状态 | 数据集 | 100m 覆盖率 | 500m 覆盖率 |
|--------|------|--------|------------|------------|
| Citi Bike | ✅ ok | GBFS | 45.3% | 98.5% |
| MTA | ✅ 已修复 | `5f5g-n3cz` (站点综合体) | 待运行 | 待运行 |
| Traffic | ✅ ok | `7ym2-wayt` | 1.2% | 14.7% |

### 文档

| 文件 | 内容 |
|------|------|
| `venue_coverage_sop_zh.md` | 空间覆盖测试标准操作规程 |
| `busynessreview.md` | busyness_ingestion.py 代码审查与测试解释 |
| `venue-coverage-review.md` | 功能介绍与执行缺口分析 (P0-P3) |

## 运行命令

```bash
# Busyness 测试
.venv-1/bin/python -m pytest -q Data+ML/test/6.15-5.20/tests/test_busyness_ingestion.py

# 覆盖测试
.venv-1/bin/python -m pytest -q Data+ML/test/6.15-5.20/tests/test_venue_coverage.py

# 覆盖测试 (线上冒烟)
python Data+ML/test/6.15-5.20/src/run_venue_coverage.py \
  --venue-file Data+ML/test/6.8-6.12_DB/tests/output/venues_clean.csv \
  --radii 100,200,300,400,500 \
  --sources citibike,mta,traffic \
  --output-dir Data+ML/test/6.15-5.20/output/venue_coverage
```
