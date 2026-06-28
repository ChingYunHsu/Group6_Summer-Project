# Healthcare Busyness ML SOP

## 1. Data Introduction

The ML busyness model is scoped to `healthcare` venues only.

Target output:

```text
busyness_level = quiet | moderate | busy
prediction_confidence = max model class probability
```

`restroom` and `emergencyasset` / AED venues are excluded from supervised busyness prediction because their data semantics are different:

- `restroom`: Google Popular Times coverage is extremely sparse and often belongs to parent venues such as parks, restaurants, libraries, or public facilities rather than the restroom itself.
- `emergencyasset` / AED: usage is rare, emergency-driven, and not meaningfully predicted by traffic, weather, or consumer activity patterns. The useful product signal is presence/location confidence, not busyness.

Recommended venue strategy:

```text
healthcare -> ML busyness prediction
restroom   -> availability / access confidence or rule fallback
AED        -> presence / location confidence / static facility display
```

Primary data inputs:

```text
venues_clean.csv
venue_label_status.csv
SerpAPI / Google Maps popular_times cache
Citi Bike proximity data
weather features
traffic / mobility proxy features
time features
```

Supervised labels come only from healthcare venues with explicit Google `popular_times`.

Important rule:

```text
no_popular_times != not busy
```

Venues without `popular_times` are inference targets, not negative training samples.

## 2. Feature Introduction

### Venue Static Features

Candidate static features:

```text
venue_id
venue_type
district
latitude
longitude
rating
review_count
source_confidence
quality_score
accessible_status
open_now
opening_hours_available
```

The first ML model should filter to:

```text
venue_type = healthcare
```

### Spatial Features

Candidate spatial features:

```text
district
latitude
longitude
distance_to_nearest_citibike_station
nearby_citibike_station_count
distance_to_nearest_subway_station
traffic_segment_distance
```

These features represent local activity intensity and accessibility.

### Mobility / Traffic Feature Groups

Coverage analysis shows that Citi Bike dominates spatial coverage, while MTA and traffic add smaller marginal venue coverage. This does not automatically mean MTA or traffic are useless for prediction, because coverage only measures whether a nearby data source exists.

Treat mobility features as separate feature groups:

```text
citibike_features -> primary mobility proxy
mta_features      -> transit accessibility / station activity proxy
traffic_features  -> sparse road activity context
```

Do not decide feature inclusion by coverage alone. Use model ablation and feature importance to test whether MTA or traffic add measurable predictive value beyond Citi Bike.

### Time Features

Busyness prediction must be tied to time.

Recommended time features:

```text
hour
day_of_week
is_weekend
month
season
is_holiday
```

### Weather Features

Candidate weather features:

```text
temperature
precipitation
wind_speed
weather_condition
is_rain
is_extreme_weather
```

Weather may be weaker for healthcare than for consumer venues, but it is still useful as a control feature.

## 3. Prediction Features

The training dataset should be built at:

```text
venue_id + day + hour
```

Each row should represent one healthcare venue at one prediction time.

Recommended feature matrix columns:

```text
venue_id
district
latitude
longitude
review_count
rating
quality_score
citibike_nearest_m
hour
day_of_week
is_weekend
month
weather_condition
temperature
precipitation
```

The target label should be converted from Google `popular_times` values:

```text
0-30   -> quiet
31-65  -> moderate
66-100 -> busy
```

If Google `popular_times` provides hourly arrays, expand them into supervised rows:

```text
venue_id + day + hour -> busyness_level
```

## 4. Model Training Parameter Analysis

### Baseline Models

Recommended baseline models:

```text
LogisticRegression
RandomForestClassifier
```

Recommended primary baseline:

```text
LogisticRegression
```

Rationale:

- Works better as a small-data baseline.
- More interpretable than tree ensembles.
- Provides `predict_proba()` for class confidence.
- Easier to explain in a report.

Random Forest should be used as a comparison model:

- Captures non-linear relationships.
- Provides `predict_proba()` via tree voting ratios.
- May overfit when labelled venue count is small.

### Logistic Regression Parameters

Recommended grid:

```text
multi_class = "multinomial"
class_weight = "balanced"
max_iter = 1000
C = [0.1, 1.0, 10.0]
```

### Random Forest Parameters

Recommended grid:

```text
n_estimators = [100, 300]
max_depth = [3, 5, None]
min_samples_leaf = [2, 5, 10]
class_weight = "balanced"
```

### Split Strategy

Avoid putting the same venue in both train and test.

Recommended validation:

```text
GroupKFold grouped by venue_id
```

Alternative:

```text
grouped train/test split by venue_id
```

Do not evaluate random hourly rows from the same venue across both train and test because this can overstate accuracy.

### Feature Group Ablation

The model should test whether each traffic data source provides incremental value.

Use the same model family and the same grouped splits for each experiment:

```text
Baseline: venue + time + weather
Baseline + Citi Bike
Baseline + Citi Bike + MTA
Baseline + Citi Bike + MTA + Traffic
```

Compare:

```text
macro_f1
balanced_accuracy
busy_recall
log_loss
```

Recommended default:

```text
primary baseline = venue + time + weather + Citi Bike
experimental variants = + MTA, + Traffic
```

MTA and traffic should enter the final baseline only if they improve grouped validation metrics consistently. If they do not improve performance, keep them in analysis outputs but exclude them from the production baseline.

## 5. Training

The reproducible ML pipeline should live in a `.py` file. The notebook should call or display its outputs, not contain the main training logic.

Recommended file:

```text
Data+ML/test/6.22-6.27/src/ml_healthcare_busyness.py
```

Recommended functions:

```text
load_data()
build_training_labels()
build_features()
split_train_test()
train_models()
evaluate_models()
save_model()
predict_unlabelled_healthcare()
save_outputs()
```

Recommended training flow:

```text
1. Load venues and label status.
2. Filter to healthcare venues.
3. Extract labelled healthcare venues from Google popular_times.
4. Expand popular_times into venue_id + day + hour rows.
5. Build static, spatial, temporal, weather, and mobility features.
6. Split with venue-level grouping.
7. Train Logistic Regression and Random Forest baselines.
8. Select the model using macro_f1 and busy-class recall.
9. Save metrics, predictions, and model artifacts.
```

Recommended outputs:

```text
output/ml/healthcare_training_dataset.csv
output/ml/healthcare_model_metrics.csv
output/ml/healthcare_predictions.csv
output/ml/healthcare_model.pkl
output/ml/feature_importance.csv
```

## 6. Prediction

Prediction should be generated for all healthcare venues:

```text
labelled healthcare   -> train / evaluate / predict
unlabelled healthcare -> predict only
```

Unlabelled healthcare venues should not be included in accuracy, F1, precision, or recall.

Recommended prediction output fields:

```text
venue_id
venue_name
venue_type
district
prediction_time
busyness_level
prediction_confidence
prediction_source
is_evaluated
model_name
model_version
```

Confidence definition:

```text
prediction_confidence = max(P(quiet), P(moderate), P(busy))
```

For Logistic Regression, this comes from class probabilities. For Random Forest, this comes from tree voting probabilities.

Important reporting note:

```text
prediction_confidence means the model's probability or voting confidence for the selected class.
It is not the same as true prediction accuracy.
```

Recommended source fields:

```text
healthcare -> prediction_source = ml_model
restroom   -> prediction_source = rule_fallback
AED        -> prediction_source = static_presence
```

Recommended applicability flags:

```text
healthcare with labels -> is_evaluated = true when used in validation
healthcare without labels -> is_evaluated = false
restroom -> busyness_level = null
AED -> busyness_level = null
```

## 7. Prediction Quality Analysis

### Evaluation Scope

Evaluate only healthcare venues with Google `popular_times` labels.

Do not compute model accuracy for unlabelled healthcare venues.

Recommended report wording:

```text
Supervised evaluation is restricted to healthcare venues with Google Popular Times labels.
Unlabelled healthcare venues are inference targets only; predictions are generated but not counted in accuracy metrics.
```

### Metrics

Recommended metrics:

```text
accuracy
macro_f1
weighted_f1
precision_by_class
recall_by_class
confusion_matrix
```

Priority metrics:

```text
macro_f1
busy recall
class distribution
confidence distribution
```

### Quality Checks

Minimum checks before accepting a baseline:

```text
macro_f1 is higher than majority-class baseline
busy recall is not zero
predictions do not collapse into a single class
confidence is not unrealistically concentrated near 1.0
train/test split is grouped by venue_id
```

### Traffic Feature Correlation and Marginal Value

Coverage rate is not enough to judge whether traffic data helps busyness prediction.

Use three levels of analysis:

```text
1. Simple association tests
2. Feature group ablation
3. Permutation importance
```

For simple association tests, use:

```text
Spearman correlation: numeric traffic feature vs busy_score
Kruskal-Wallis or ANOVA: traffic feature distribution across quiet/moderate/busy
mutual_info_classif: feature vs busyness_level
```

These are exploratory only. They should not replace model validation.

For feature group ablation, compare the fixed-split experiments listed above. This answers whether MTA or traffic improve prediction beyond Citi Bike.

For permutation importance, evaluate the trained model by shuffling each feature group:

```text
shuffle Citi Bike features -> metric drop
shuffle MTA features -> metric drop
shuffle traffic features -> metric drop
```

If shuffling traffic features does not reduce macro_f1, balanced_accuracy, or busy_recall, traffic has no measurable value under the current labelled sample.

Because only a small subset of healthcare venues has Google `popular_times`, conclusions must be phrased conservatively:

```text
Under the currently labelled healthcare sample, traffic features did not provide measurable incremental predictive value beyond Citi Bike and MTA.
```

Do not write:

```text
Traffic features are useless.
```

### Notebook Role

The notebook should be used for process explanation and result display:

```text
1. Data overview
2. Feature overview
3. Label coverage check
4. Training sample preview
5. Model parameter explanation
6. Training metrics display
7. Prediction result display
8. Prediction quality analysis
9. Final conclusion
```

The `.py` pipeline is the source of truth for repeatable training and prediction.

## Final Decision

Supervised busyness ML is restricted to healthcare venues.

Restroom and AED are excluded from the busyness model because they do not have reliable, semantically correct, public busyness labels:

```text
healthcare -> categorical busy-level ML
restroom   -> availability / access fallback
AED        -> static presence / location confidence
```
