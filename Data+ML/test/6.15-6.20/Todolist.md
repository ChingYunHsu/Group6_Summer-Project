# Todolist — Venue Busyness 预测优化

## 核心问题

venue 自身的热力/拥挤度数据无法直接获取：

- Google Popular Times：无公开 API
- BestTime：单次查询，付费，无法批量训练
- Yelp/Google Places：无实时人流接口

**需要通过公开代理信号构建训练标签。**

---

## 已确认可用的代理数据源

### 1. MTA Subway Hourly Ridership ⭐ 最有价值

| 项 | 值 |
|---|---|
| 数据集 ID | `wujg-7c2s` |
| API | `https://data.ny.gov/resource/wujg-7c2s.json` |
| 粒度 | station_complex + hour |
| Manhattan 行数 | 36,828,057 |
| 时间范围 | 2020–2024（最新 2024-12-31） |
| 关键字段 | `station_complex_id`, `station_complex`, `ridership`, `transfers`, `latitude`, `longitude`, `borough`, `transit_timestamp` |
| 费用 | 免费 |

**价值**：每个站点每小时的进出站人数，直接反映附近区域的活动强度。

### 2. Citi Bike GBFS（已有）

| 项 | 值 |
|---|---|
| 端点 | station_information + station_status |
| 粒度 | 站点级实时 |
| Manhattan 站点 | ~2,328 |
| 费用 | 免费 |

**价值**：站点被借空/还满的频率反映周边活动。

### 3. NYC Traffic（已有）

| 项 | 值 |
|---|---|
| 数据集 ID | `7ym2-wayt` |
| 粒度 | 路段级/小时 |
| Manhattan 路段 | 28（稀疏） |
| 费用 | 免费 |

**价值**：district 级别聚合后可作为辅助特征。

---

## 待办事项

### Phase 1：MTA 数据接入（优先级 P0）

- [ ] **接入 MTA Hourly Ridership API**
  - 数据集 `wujg-7c2s`，Manhattan 筛选 `borough='Manhattan'`
  - 按 `station_complex_id` + `transit_timestamp` 聚合 ridership
  - 输出：每个 station_complex 每小时的总 ridership

- [ ] **MTA 站点 → venue 映射**
  - 用 haversine 距离把 venue 匹配到最近的 MTA 站点
  - 复用 venue_coverage 的 BallTree 逻辑
  - 关联表：`venue_id → nearest_station_complex_id → distance_m`

- [ ] **存储设计**
  - 新表 `mta_hourly_ridership`：`station_complex_id, hour, ridership, transfers`
  - 或直接在 ETL 中按需查询，不持久化（数据量大：36M+ 行）

### Phase 2：多源活动指数（优先级 P0）

- [ ] **构建 district + hour 级活动指数**
  ```python
  activity_index = w1 * citibike_norm + w2 * mta_norm + w3 * traffic_norm
  ```
  - 每个数据源按 district + hour 归一化到 0-100
  - 权重 w1/w2/w3 初始设为 1/1/1，后续根据相关性调整

- [ ] **验证时间相关性**
  - 按 district 分组计算 Pearson/Spearman 相关系数
  - 对齐 24h 曲线，检查高峰时段一致性
  - 预期：MTA ridership 与 venue busyness r > 0.7

### Phase 3：模型训练（优先级 P1）

- [ ] **训练数据构建**
  - 输入特征：MTA ridership (hour, district) + Citi Bike activity + Traffic volume + 时间特征 (hour, day_of_week, is_holiday)
  - 标签：多源活动指数（activity_index）
  - 训练集：2020-2023，验证集：2024

- [ ] **模型选型**
  - 基线：LightGBM / XGBoost（tabular data）
  - 进阶：LSTM / Prophet（时序预测）
  - 输出：未来 12h 的 activity_index 预测

- [ ] **评估指标**
  - MAE / RMSE：预测值与实际活动指数的偏差
  - 排序精度：预测的高峰/低谷时段是否准确
  - 消融实验：有/无 Traffic 对预测精度的影响

### Phase 4：生产集成（优先级 P2）

- [ ] **替换现有 busyness_scores 表**
  - 用 MTA + Citi Bike 活动指数替代纯 Traffic 分数
  - 保持 district 级别粒度

- [ ] **定时更新管道**
  - 每小时拉取 MTA ridership（增量查询 `transit_timestamp > last_update`）
  - 重新计算活动指数并更新 busyness_scores

- [ ] **前端 API 适配**
  - `get_venue_busyness` 返回新的活动指数
  - `get_venue_busyness_forecast` 返回 12h 预测

---

## 数据量估算

| 数据源 | 每天行数 | 每月行数 | 存储需求 |
|--------|---------|---------|---------|
| MTA hourly (Manhattan) | ~250K | ~7.5M | ~1.5GB/月 |
| Citi Bike | ~55K | ~1.6M | ~300MB/月 |
| Traffic | ~672 | ~20K | ~5MB/月 |

MTA 数据量最大，建议按需查询而非全量存储。

---

## 风险与注意事项

1. **MTA 数据截止 2024-12-31**：需要确认 2025 数据是否已发布
2. **payment_method 维度**：metrocard vs omny 可能有统计口径差异，聚合时需注意
3. **station_complex 重复坐标**：同一 complex_id 可能有多行（不同 payment_method），聚合时按 complex_id + hour 去重
4. **Citi Bike 实时 vs 历史**：GBFS 只提供实时状态，历史数据需另行获取
