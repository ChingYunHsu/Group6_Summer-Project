# SerpAPI 繁忙度覆盖 — 演示文稿备注

## 1. 核心结论

我们构建了一套基于 SerpAPI 的弱标签管线，用于采集 NYC 医疗场所的 Google Popular Times 信号。

针对医疗场所集合：

| 指标 | 数值 |
|---|---:|
| 医疗场所总数 | 1,086 |
| SerpAPI 匹配并验证的场所 | 743 |
| 拥有 Google Popular Times 的场所 | 161 |
| 验证后仍无 Popular Times 的场所 | 582 |
| 未匹配到搜索结果的场所 | 343 |
| 预计小时级弱标签数量 | 161 × 7 × 24 = 27,048 |

最终演示措辞：

> 基于 SerpAPI 构建 NYC 医疗场所繁忙度标签管线，对 1,086 个医疗场所进行覆盖筛查，识别出 161 个拥有 Google Popular Times 信号的场所，生成约 2.7 万条小时级代理繁忙度标签用于 ML 训练。

## 2. 标签的含义

ML 目标并非真实人流量地面真值。

目标是：

> Google Popular Times 代理繁忙度

即模型预测的是 Google 历史 Popular Times 信号所隐含的典型繁忙度模式，而非实时测量的占用率。

可接受的原因：

- Google Popular Times 提供高分辨率的每周模式。
- 每个被标记的场所最多提供 7 天 × 24 小时的小时级标签。
- 该信号适合作为演示和基线建模的代理目标。
- 其局限性是明确且可辩护的：这是一个弱标签，而非官方行人计数数据集。

## 3. 特征时间对齐

Google Popular Times 被视为典型每周模式，而非精确带时间戳的历史观测。

监督学习粒度为：

```text
prediction_group_id + day_of_week + hour
```

而非：

```text
venue + exact_date + exact_timestamp
```

对特征设计的影响：

| 特征组 | 是否需要严格时间戳对齐 | 原因 |
|---|---|---|
| `review_count`、`rating` | 否 | 慢速变化的场所可见性特征 |
| `nearest_subway_distance_m` | 否 | 静态空间可达性 |
| `nearest_citibike_distance_m` | 否 | 站点位置可达性代理 |
| `poi_density_300m` | 否 | 静态周边活动代理 |
| `capacity`、`hospital_level` | 无需严格对齐 | 慢速变化的设施规模/类型代理 |
| `day_of_week`、`hour` | 是 | 这是核心的每周模式索引 |
| 实时交通/天气 | 不作为实时因果观测 | 标签并非实时测量的人流量 |

如果添加交通或天气特征，应保守地将其定义为典型上下文代理，例如：

```text
typical_traffic_by_district_day_hour
typical_weather_by_season_hour
```

推荐的首个基线：

```text
场所静态特征 + 空间特征 + day_of_week + hour
```

这样可以避免在 Google Popular Times 与外部上下文数据之间过度声明因果或实时对齐关系。

## 4. 繁忙度等级语义

产品级繁忙度枚举有四种显示状态：

```text
quiet | moderate | busy | no_data
```

对于医疗 ML 模型，学习到的预测状态为：

```text
quiet | moderate | busy
```

`no_data` 不是监督训练类别。它是当没有 ML 预测可用时的默认显示/API 回退状态，特别是对于当前医疗 ML 范围之外的场所类型。

推荐映射：

| 场景 | 显示等级 |
|---|---|
| 医疗场所，预测分数 `< 30` | `quiet` |
| 医疗场所，预测分数 `30-70` | `moderate` |
| 医疗场所，预测分数 `> 70` | `busy` |
| 洗手间/AED/超出范围的场所 | `no_data` |
| 医疗场所但无可用预测 | `no_data` |
| 医疗场所但超出营业时间 | `no_data` |

重要区分：

```text
Google Popular Times busyness_score = 0 是有效的安静信号。
缺少预测 = no_data。
超出营业时间 = 服务时显示 no_data，而非模型训练类别。
```

## 5. 覆盖提升结果

最终数据库驱动搜索和 Place 验证轮次之前：

| 状态 | 数量 |
|---|---:|
| 拥有 Popular Times 的医疗场所 | 125 |

最终轮次之后：

| 状态 | 数量 |
|---|---:|
| 拥有 Popular Times 的医疗场所 | 161 |
| 新增拥有 Popular Times 的场所 | 36 |

最终轮次执行摘要：

| 步骤 | 结果 |
|---|---:|
| 数据库驱动搜索调用 | 250 |
| 搜索匹配的场所 | 157 |
| 唯一 Place ID | 154 |
| Place API 验证 | 155 |
| 新增 Popular Times 场所 | 36 |
| Place 验证命中率 | 36 / 155 = 23.2% |

重要修正：

- 管线并未证明每个医疗场所都有 Google 档案。
- 它完成了当前 SerpAPI 覆盖工作流。
- 剩余的 `search_not_matched` 场所是在当前名称 + GPS 搜索策略下未能匹配的场所。

准确措辞：

> 我们完成了 1,086 个医疗场所的 SerpAPI 覆盖工作流。其中 743 个通过 SerpAPI 匹配并验证，161 个包含可用的 Google Popular Times 信号。

## 6. 为何停止 API 扩展

最终轮次产出：

```text
250 次搜索调用 → 36 个新 Popular Times 场所
= 每 100 次搜索调用产生 14.4 个新标签
```

这落在中间决策区间：

| 每 100 次搜索的产出 | 决策 |
|---|---|
| >= 15 | 继续 API 扩展 |
| 10-14 | 有条件继续 |
| < 10 | 停止 |

结果接近继续阈值，但更好的下一步是将新获取的标签处理为训练就绪的数据集，再花费更多 API 配额。

## 7. ML 影响

最终标记的场所数量在场所级别是有限的：

```text
161 个已标记场所
```

但小时级训练样本数量可用于基线模型：

```text
161 个场所 × 7 天 × 24 小时 = 27,048 个小时级标签
```

推荐的首个模型：

> 用于典型每周繁忙度预测的表格基线模型。

不推荐作为首个模型：

- LSTM
- SARIMA
- 实时滚动预测

原因：

- 数据不是实时历史时间序列。
- 它是来自 Google Popular Times 的典型每周模式。
- 表格模型更简单、可解释性更好，且与可用目标更匹配。

## 8. 产品/前端解读

前端预测应展示为：

> 基于场所和上下文特征的典型未来小时繁忙度估计。

而非：

> 实时人群预测。

建议前端展示：

- 12 小时繁忙度折线图。
- 将输出标注为"预测繁忙度模式"。
- 对拥有预测的医疗场所使用 `quiet`、`moderate` 和 `busy`。
- 对洗手间、AED、超出范围的场所或无预测的医疗场所使用 `no_data` 作为默认回退。

## 9. PPT 方法摘要

管线流程：

1. 从已清洗的医疗场所数据库出发。
2. 使用场所名称和 GPS 坐标查询 SerpAPI Google Maps Search。
3. 使用以下条件匹配返回的 Google Place 候选：
   - 空间阈值：200 米
   - 名称相似度阈值：0.4
4. 按 `serpapi_place_id` 去重。
5. 仅对匹配的唯一 Place 查询 SerpAPI Place API。
6. 提取可用的 Google Popular Times。
7. 存储标签状态：
   - `has_popular_times`（有 Popular Times）
   - `no_popular_times`（无 Popular Times）
   - `search_not_matched`（搜索未匹配）

## 10. 局限性

需披露的关键局限：

- Google Popular Times 是代理标签，而非官方人流量地面真值。
- 部分有效医疗场所因命名不匹配、缺少 Google 档案或地理空间对齐薄弱而未能匹配。
- 场所级已标记数量仍有限，为 161 个。
- 模型验证必须使用基于 `serpapi_place_id`/场所组的分组感知拆分，以避免小时级数据泄漏。

## 11. 简历/演示要点

中文：

> 构建 NYC 医疗场所繁忙度弱标签管线，基于 SerpAPI 完成 1,086 个场所的覆盖筛查，匹配并验证 743 个 Google Maps 场所，最终提取 161 个场所的 Google Popular Times 信号，生成约 2.7 万条小时级 ML 训练标签。

直接映射是我们的基线。ML 模型通过利用场所级和上下文特征，将 Google Popular Times 的弱标签迁移到未覆盖的场所，从而改进基线——同一区域、同一小时的两个诊所不会默认获得相同的分数。
