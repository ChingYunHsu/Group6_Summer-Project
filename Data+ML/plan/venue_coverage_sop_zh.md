# 场地空间覆盖测试标准操作规程（SOP）

> 日期：2026-06-15  
> 范围：Citi Bike、MTA 地铁、NYC 交通数据的空间覆盖测试  
> 输入：`Data+ML/test/6.8-6.12_DB/tests/output/venues_clean.csv`  
> 状态：已批准的实施计划

## 1. 目标

衡量在合理 GPS 半径范围内，有多少项目场地至少拥有一个可用的数据源点。
本阶段仅衡量空间特征可用性，不评估预测质量、相关性或生产模型权重。

测试半径：

```text
100m、200m、300m、400m、500m
```

数据源归因顺序：

```text
Citi Bike → Citi Bike + MTA → Citi Bike + MTA + Traffic
```

在审查结果之前，不定义通过/失败的覆盖阈值。

## 2. 固定决策

### 2.1 场地数据集

- 使用当前提供的 `venues_clean.csv`。
- 预期输入规模：`venue_id` 去重前 4,838 行。
- 不重复 ETL 已完成的坐标验证。
- 按 `venue_id` 对场地行去重，保留第一行。
- 相同坐标但不同 `venue_id` 的记录保留为单独的分母记录。
- 在运行元数据中记录重复 `venue_id` 计数。
- 在本 SOP 期间不根据 `borough` 清洗或排除记录。

### 2.2 必需的分组维度

生成以下维度的结果：

- 总体（Overall）
- `venue_type`（场地类型）
- `district`（区域）

初始版本不生成 `venue_type × district` 交叉表。

当前预期的场地类型包括：

```text
emergencyasset（应急资产）
healthcare（医疗保健）
restroom（卫生间）
```

### 2.3 数据源优先级

1. Citi Bike GBFS
2. MTA 地铁
3. NYC 交通

NYC 行人传感器从主要覆盖序列中排除，因为其有效空间覆盖过于稀疏。
它们仍适合在后续模型校准中使用。

BestTime 从本覆盖测试中排除，因为它是付费的场地级数据源，且不太可能与大多数应急资产和卫生间匹配。

## 3. 交通数据接入决策

保留 NYC 交通作为候选空间数据源，但不将
`Data+ML/test/6.8-6.12_DB/dqr/busyness_ingestion.py` 重复用作生产接入管道。

当前处置方案：

```text
数据源：保留用于覆盖测试
现有接入实现：仅为原型
当前预测权重：0
覆盖测试期间的数据库写入：禁止
```

交通数据仅在以下条件满足后才可能获得未来模型权重：

- 场地-时段重复聚合已修正；
- 数据库写入真正满足幂等性；
- 历史数据源年份和预测时间戳语义已修正；
- 与行人或交通衍生的活动指标的相关性已测量；
- 消融测试表明可测量的预测改进。

仅凭空间覆盖不能作为交通数据预测行人或场地繁忙程度的证据。

## 4. 文件清单

创建：

```text
Data+ML/test/6.8-6.12_DB/dqr/venue_coverage.py
Data+ML/test/6.8-6.12_DB/run_venue_coverage.py
Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py
```

计划文档：

```text
Data+ML/plan/venue_coverage_sop.md
```

本工作不修改 `busyness_scores` 或 `busyness_forecasts` 表。

## 5. CLI 接口契约

从项目根目录运行：

```bash
python Data+ML/test/6.8-6.12_DB/run_venue_coverage.py \
  --venue-file Data+ML/test/6.8-6.12_DB/tests/output/venues_clean.csv \
  --radii 100,200,300,400,500 \
  --sources citibike,mta,traffic \
  --mta-year 2025 \
  --traffic-year 2025 \
  --output-dir Data+ML/test/6.15-5.20/output
```

默认值：

```text
--radii          100,200,300,400,500
--sources        citibike,mta,traffic
--mta-year       2025
--traffic-year   2025
--page-size      5000
--connect-timeout 2
--read-timeout   5
--max-retries    3
```

`--sources` 的顺序定义了增量组合归因。

CLI 必须拒绝以下情况：

- 空半径列表；
- 非正数半径；
- 递减或重复的半径；
- 不支持的数据源名称；
- 页面大小大于 5,000；
- 缺少场地输入文件。

## 6. API 数据源契约

### 6.1 Citi Bike

端点：

```text
https://gbfs.lyft.com/gbfs/1.1/bkn/en/station_information.json
https://gbfs.lyft.com/gbfs/1.1/bkn/en/station_status.json
```

规则：

- 使用 `station_information` 获取 `station_id`、名称、纬度和经度。
- 使用 `station_status` 识别当前已安装且运行中的站点（如可用）。
- 通过 `station_id` 进行关联。
- 在本阶段不将自行车或停车桩视为场地客流量。
- 记录 feed `last_updated`、TTL、获取时间、原始站点数和保留点数。

标准化点格式：

```text
source = citibike
source_id = station_id
name = 站点名称
latitude（纬度）
longitude（经度）
source_timestamp（数据源时间戳）
```

### 6.2 MTA 地铁

默认数据集：

```text
2025 年起讫点客流量估计
数据集 ID：y2qv-fytt
API：https://data.ny.gov/resource/y2qv-fytt.json
```

规则：

- `--mta-year` 选择配置的数据集映射。
- 不下载全部 OD 行并在本地去重。
- 使用服务端 SoQL 查询和分组获取唯一的站点综合体及坐标。
- 在按站点 ID 去重前，同时包含起点和终点站点综合体。
- 如果请求的数据集不可用，不自动回退到其他年份。
- 记录请求年份、数据集 ID、查询语句、获取时间、原始 API 行数和保留点数。

标准化点格式：

```text
source = mta
source_id = station_complex_id
name = station_complex_name（站点综合体名称）
latitude（纬度）
longitude（经度）
source_timestamp（数据源时间戳）
```

### 6.3 NYC 交通

使用项目已引用的官方 NYC SODA 交通数据集：

```text
数据集 ID：7ym2-wayt
API：https://data.cityofnewyork.us/resource/7ym2-wayt.json
```

规则：

- 按请求的 `--traffic-year` 过滤。
- 使用服务端按 `segmentid` 分组。
- 每个路段请求一个代表性几何体。
- 将 EPSG:2263 路段几何体转换为 WGS84 坐标系。
- 每个路段使用一个代表性点进行覆盖测试。
- 不计算繁忙度分数。
- 不调用数据库插入代码。
- 记录年份、数据集 ID、查询语句、坐标转换失败数和保留点数。

标准化点格式：

```text
source = traffic
source_id = segmentid
name = 街道或路段标签
latitude（纬度）
longitude（经度）
source_timestamp（数据源时间戳）
```

## 7. API 执行策略

### 7.1 分页

- 最大页面大小：5,000。
- 当服务端分组结果仍超过一页时，使用 `$limit` 和 `$offset` 进行 SODA 分页。
- 仅当页面包含的记录数少于请求的页面大小时才停止。
- 每个数据源添加 20,000 个唯一点的安全上限。
- 如果超过安全上限，则使该数据源失败，而非静默截断。

### 7.2 超时与重试

使用：

```python
timeout = (2, 5)
```

含义：

- 连接超时：2 秒；
- 响应读取超时：5 秒。

每次失败请求最多重试三次，延迟如下：

```text
1 秒、2 秒、4 秒
```

重试连接错误、读取超时、HTTP 429 和 HTTP 5xx 响应。不重试其他 HTTP 4xx 响应。

### 7.3 故障隔离

每个数据源独立运行。

如果某个数据源在重试后仍然失败：

- 将其元数据状态设为 `failed`；
- 记录异常类型和简明错误信息；
- 继续处理成功获取的数据源；
- 不将失败数据源表示为零覆盖；
- 不生成任何包含失败数据源的组合结果。

示例：

```text
Citi Bike 成功，MTA 失败，Traffic 成功：
- 生成 Citi Bike 单独覆盖结果；
- 生成 Traffic 单独覆盖结果；
- 不生成 Citi Bike + MTA 组合；
- 不生成 Citi Bike + MTA + Traffic 组合。
```

## 8. 点位标准化与去重

对于每个数据源：

1. 将 API 响应解析为标准化点模式。
2. 删除 API 坐标缺失、非数值或无法转换的记录。
3. 按 `source_id` 去重，保留第一条有效记录。
4. 如果多个剩余 ID 具有完全相同的纬度和经度，则保留一个坐标用于空间计算。
5. 保留以下计数：
   - 原始记录数；
   - 有效记录数；
   - 唯一 source ID 数；
   - 唯一坐标数；
   - 被拒绝的记录数。

不将原始 API 响应或标准化点快照持久化到磁盘。数据源点仅在运行期间存在于内存中。

## 9. 空间算法

使用 `sklearn.neighbors.BallTree`，度量方式为 Haversine。

每个成功数据源的处理流程：

1. 将数据源和场地坐标从度数转换为弧度。
2. 从唯一数据源坐标构建一个 BallTree。
3. 为每个去重后的场地查询最近的数据源点。
4. 使用以下公式将角度距离转换为米：

```text
distance_m = angular_distance × 6,371,008.8
```

5. 存储每个场地最近的 `source_id` 和最近距离。
6. 根据该单一最近距离结果计算所有半径标志。

不为每个半径单独重建或查询树。

覆盖规则：

```text
covered(source, radius) = nearest_distance_m <= radius
```

## 10. 覆盖指标

### 10.1 单数据源覆盖

对于每个数据源、半径和分组维度：

```text
venue_count（场地数）
covered_count（覆盖数）
coverage_rate（覆盖率）
newly_covered_count_vs_previous_radius（相对于前一半径的新增覆盖数）
marginal_gain_percentage_points（边际增益百分点）
```

在 100m 处，前一半径的覆盖数为零。

```text
coverage_rate = covered_count / venue_count
marginal_gain_pp = current_coverage_rate - previous_coverage_rate
```

### 10.2 组合覆盖

对于每个半径，按固定 CLI 顺序应用数据源：

```text
C1 = Citi Bike
C2 = Citi Bike 或 MTA
C3 = Citi Bike 或 MTA 或 Traffic
```

每个阶段报告：

```text
cumulative_covered_count（累计覆盖数）
cumulative_coverage_rate（累计覆盖率）
incremental_unique_covered_count（增量唯一覆盖数）
incremental_gain_percentage_points（增量增益百分点）
```

新添加数据源的增量计数仅包含在同一半径下尚未被先前数据源覆盖的场地。

### 10.3 距离分布

对于每个单数据源和分组维度报告：

```text
nearest_distance_median（最近距离中位数）
nearest_distance_p90（最近距离第 90 百分位）
nearest_distance_max（最近距离最大值）
```

## 11. 输出结构

每次运行直接写入 `--output-dir` 指定的目录，覆盖上次结果：

```text
Data+ML/test/6.15-5.20/output/
  venue_coverage_detail.csv
  coverage_summary.csv
  coverage_report.md
  run_metadata.json
  coverage_by_radius.png
  incremental_coverage.png
  venue_type_coverage_heatmap.png
  uncovered_venue_distribution.png
```

不保留历史运行记录。每次运行覆盖上一次的制品文件。

### 11.1 `venue_coverage_detail.csv`

每个去重后场地一行。

必需基础列：

```text
venue_id（场地ID）
venue_type（场地类型）
district（区域）
latitude（纬度）
longitude（经度）
```

每个成功数据源的列：

```text
{source}_nearest_source_id（最近数据源ID）
{source}_nearest_distance_m（最近距离_米）
{source}_covered_100m（100m覆盖）
{source}_covered_200m（200m覆盖）
{source}_covered_300m（300m覆盖）
{source}_covered_400m（400m覆盖）
{source}_covered_500m（500m覆盖）
```

失败数据源的列可以不存在，但失败必须在 `run_metadata.json` 和 `coverage_report.md` 中明确记录。

### 11.2 `coverage_summary.csv`

必需列：

```text
scope（范围）
group_name（分组名称）
group_value（分组值）
coverage_kind（覆盖类型）
source_or_combination（数据源或组合）
radius_m（半径_米）
venue_count（场地数）
covered_count（覆盖数）
coverage_rate（覆盖率）
incremental_covered_count（增量覆盖数）
marginal_gain_pp（边际增益百分点）
nearest_distance_median（最近距离中位数）
nearest_distance_p90（最近距离第90百分位）
```

取值：

```text
scope: overall | venue_type | district
coverage_kind: standalone | cumulative
```

距离分布字段在单数据源行中填充，累计组合行留空。

### 11.3 `run_metadata.json`

必需部分：

```json
{
  "run_id": "YYYYMMDDTHHMMSSZ",
  "started_at": "ISO-8601 UTC",
  "completed_at": "ISO-8601 UTC",
  "timezone": "UTC",
  "venue_input": {},
  "parameters": {},
  "sources": {},
  "software": {},
  "artifacts": []
}
```

记录内容：

- 场地文件路径和行数；
- 唯一场地数和重复 `venue_id` 数；
- 半径和数据源顺序；
- MTA 和 Traffic 年份；
- API URL、数据集 ID、请求参数和查询语句；
- API 获取时间和最大数据源时间戳；
- 数据源数据年龄或 `timestamp_unavailable`；
- 原始、有效、唯一 ID、唯一坐标和被拒绝的计数；
- 数据源状态、重试次数和失败消息；
- Python 和包版本；
- 制品文件名。

### 11.4 `coverage_report.md`

必需章节：

1. 运行摘要
2. 数据源状态和时效性
3. 总体单数据源覆盖
4. 累计覆盖和数据源边际贡献
5. 按 `venue_type` 的覆盖
6. 按区域的覆盖
7. 最近距离分布
8. 未覆盖场地计数
9. 数据质量警告
10. 解读约束

不自动推荐生产半径。呈现 100m 到 500m 的边际结果供审查。

## 12. 静态可视化

使用 PNG 格式，1,600 × 900 像素，150 DPI。不生成交互式地图。

必需图表：

### `coverage_by_radius.png`（按半径覆盖）

- X 轴：半径
- Y 轴：覆盖率
- 每个单数据源一条线
- 有效累计组合的附加线

### `incremental_coverage.png`（增量覆盖）

- 按半径分组的条形图
- 显示每个数据源在组合顺序中的贡献百分点

### `venue_type_coverage_heatmap.png`（场地类型覆盖热力图）

- 行：场地类型
- 列：数据源/组合和半径
- 单元格：覆盖率

### `uncovered_venue_distribution.png`（未覆盖场地分布）

使用静态分组条形图，而非地图：

- X 轴：区域或场地类型
- Y 轴：仍未覆盖的计数
- 系列：半径或最终组合

每个图表必须包含标题、轴标签、适用的图例以及数据源/运行时间戳。

## 13. 测试驱动的实施任务

### 任务 1：CLI 解析与验证

文件：

```text
创建：Data+ML/test/6.8-6.12_DB/run_venue_coverage.py
创建：Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py
```

测试：

- 默认值正确解析；
- 可配置的 MTA 和 Traffic 年份被保留；
- 数据源顺序被保持；
- 无效半径和页面大小报错失败；
- 缺少场地文件时在 API 调用前失败。

运行：

```bash
pytest -q Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py -k cli
```

预期：CLI 测试通过。

### 任务 2：HTTP 客户端、重试与数据源隔离

文件：

```text
创建：Data+ML/test/6.8-6.12_DB/dqr/venue_coverage.py
修改：Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py
```

测试：

- 每个请求使用 `timeout=(2, 5)`；
- 瞬态失败使用 `1/2/4` 延迟重试三次；
- 不可重试的 4xx 立即失败；
- 分页在短页面时停止；
- 超过 20,000 个唯一点时数据源失败；
- 一个数据源失败不会停止其他数据源；
- 包含失败数据源的组合被省略。

运行：

```bash
pytest -q Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py -k 'http or retry or pagination or isolation'
```

预期：HTTP 行为测试在无实时网络访问的情况下通过。

### 任务 3：数据源适配器

文件：

```text
修改：Data+ML/test/6.8-6.12_DB/dqr/venue_coverage.py
修改：Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py
```

测试：

- Citi Bike 信息/状态关联；
- MTA 服务端唯一站点解析；
- Traffic 唯一路段解析和坐标转换；
- 请求年份出现在数据源查询中；
- 数据源 ID 去重；
- 重复坐标移除；
- 无效 API 坐标被拒绝并计数；
- 数据源时效性元数据被填充。

运行：

```bash
pytest -q Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py -k source
```

预期：使用 fixture 或模拟响应的数据源适配器测试通过。

### 任务 4：BallTree 距离计算

文件：

```text
修改：Data+ML/test/6.8-6.12_DB/dqr/venue_coverage.py
修改：Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py
```

测试：

- 已知坐标对产生容差范围内的预期 Haversine 距离；
- 最近数据源 ID 正确；
- 精确 100m 边界被覆盖；
- 单次树查询支持全部五个半径标志；
- 场地去重仅通过 `venue_id` 进行；
- 相同坐标但不同场地 ID 保持独立。

运行：

```bash
pytest -q Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py -k 'distance or balltree or dedup'
```

预期：空间测试通过。

### 任务 5：覆盖聚合

文件：

```text
修改：Data+ML/test/6.8-6.12_DB/dqr/venue_coverage.py
修改：Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py
```

测试：

- 每个半径的单数据源覆盖；
- 半径边际计数和百分点计算；
- 累计数据源顺序；
- 增量唯一归因；
- 总体聚合；
- `venue_type` 聚合；
- 区域聚合；
- 无 `venue_type × district` 交叉表；
- 中位数和 P90 距离。

运行：

```bash
pytest -q Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py -k coverage
```

预期：聚合测试通过。

### 任务 6：制品与可视化

文件：

```text
修改：Data+ML/test/6.8-6.12_DB/dqr/venue_coverage.py
修改：Data+ML/test/6.8-6.12_DB/run_venue_coverage.py
修改：Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py
```

测试：

- 明细 CSV 契约；
- 汇总 CSV 契约；
- 元数据 JSON 契约；
- Markdown 必需章节；
- 全部四个 PNG 文件存在且非空；
- 创建带时间戳的运行目录；
- 仅在完全成功后更新 `latest/`；
- 不写入原始 API 响应或数据源点快照。

运行：

```bash
pytest -q Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py -k 'artifact or report or chart or metadata'
```

预期：输出契约测试通过。

### 任务 7：完整验证与线上冒烟测试

运行单元测试：

```bash
pytest -q Data+ML/test/6.8-6.12_DB/tests/test_venue_coverage.py
```

预期：所有覆盖测试通过。

运行线上 API 冒烟测试：

```bash
python Data+ML/test/6.8-6.12_DB/run_venue_coverage.py \
  --venue-file Data+ML/test/6.8-6.12_DB/tests/output/venues_clean.csv \
  --radii 100,200,300,400,500 \
  --sources citibike,mta,traffic \
  --mta-year 2025 \
  --traffic-year 2025 \
  --output-dir Data+ML/test/6.15-5.20/output
```

预期：

- 至少一个数据源成功时进程退出码为 0；
- 数据源失败可见且不被表示为零覆盖；
- 存在完整的带时间戳运行目录；
- `latest/` 指向新完成的结果；
- 未修改任何 MySQL 表。

## 14. 审查清单

在解读结果之前，确认：

- [ ] 场地分母和重复计数已记录。
- [ ] 所有数据源状态明确。
- [ ] API 查询年份和数据集 ID 已记录。
- [ ] 没有数据源在 5,000 行处静默停止。
- [ ] 失败数据源已从受影响的组合中排除。
- [ ] 单数据源和累计覆盖均已呈现。
- [ ] 结果包含总体、场地类型和区域视图。
- [ ] 每个 100m 增量的边际变化均已显示。
- [ ] Traffic 未被描述为观测到的行人繁忙度。
- [ ] 未从空间覆盖推断预测权重。
- [ ] 未持久化原始 API 响应。
- [ ] 未发生数据库写入。

## 15. 测试后决策

审查生成的覆盖报告后，决定：

1. 哪个半径提供了可接受的覆盖与局部性权衡。
2. Traffic 是否增加了足够的唯一空间覆盖以证明进一步验证工作的合理性。
3. 哪些场地类型或区域需要回退特征。
4. 是否添加行人传感器作为校准标签。
5. 是否从空间覆盖测试推进到时间相关性和模型消融分析。

在时间验证阶段完成之前，不分配生产权重。
