# School-community stress archetypes

## What the pipeline does

`ml_archetypes.py` clusters all 600 North Carolina ODIS schools using only the five standardized ODIS domain scores: Economic, Education, Health, Housing, and Crime. The composite score is not included because it is derived from those domains.

The pipeline then adds two external county-level context sources:

1. **LiNC Education (2024):** spending per student, instructional personnel per 1,000 students, attendance rate, funding shares, and high-school dropouts per 1,000 enrolled students.
2. **LiNC Employment and Income:** 2024 unemployment, 2024 HUD median family income, and 2023 poverty rate.

LiNC variables are not used to create the clusters. They are joined afterward to describe the county resource environment surrounding each school archetype.

## Why K=6

The script evaluates K=3 through K=8 using silhouette score, inertia, Calinski-Harabasz, Davies-Bouldin, minimum cluster size, and adjusted Rand index across 20 random initializations.

K=4 has the highest silhouette score (0.2610). K=6 was selected because it separates six interpretable stress structures, retains 60 schools in the smallest group, and remains stable across random initializations (mean adjusted Rand index 0.9684). This is an interpretation choice, not a claim that six is the uniquely correct number of social categories.

## Reproduce the analysis

From `weight_sensitivity_map`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
MPLBACKEND=Agg .venv/bin/python ml_archetypes.py
```

The run is deterministic through `random_state=2026` and `n_init=50`.

## Main outputs

- `outputs/ml/school_archetypes.csv`: school cluster, domain profile, sensitivity class, PCA coordinates, imputation disclosure, and distance to centroid.
- `outputs/ml/cluster_profiles.csv`: cluster sizes, domain centroids, median stress, and sensitivity summaries.
- `outputs/ml/model_selection.csv`: diagnostics for K=3 through K=8.
- `outputs/ml/nearest_peers.csv`: five nearest schools within each archetype.
- `outputs/ml/county_context.csv`: cleaned and derived LiNC county metrics.
- `outputs/ml/county_cluster_context.csv`: county archetype composition and resource-alignment review flag.
- `outputs/ml/run_summary.json`: compact reproducibility and coverage summary.
- `outputs/ml/archetype_web_data.json`: compact school, county, profile, and model-selection payload for a separate web archetype explorer.
- `outputs/ml/figures/`: model-selection, centroid, PCA, and resource-context figures.

## Data handling decisions

- Seven schools have at least one missing domain. The script median-imputes only for model fitting and exposes the number and names of imputed domains in the school output.
- Education metrics use 2024 rather than 2025 because the LiNC 2025 membership values contain clear county-level anomalies for some counties. Using a common 2024 education year also aligns with the 2024 employment indicators.
- LiNC labels Rowan County as `Salisbury County` for 2024 public high-school enrollment. The script normalizes that source label to Rowan County and records the correction in `county_context.csv`.
- County metrics remain county-level context. They must not be described as school-specific resources.
- The resource-alignment flag is a review rule, not a funding recommendation. It identifies counties in the top quartile of mean ODIS stress and below the NC county median for spending per student or instructional personnel.

## Interpretation boundaries

- Clusters are descriptive archetypes, not causal explanations.
- Cluster numbers and names are not school rankings.
- Distance to centroid measures how typical a school is for its assigned cluster; it is not model confidence or probability.
- PCA is used only for visualization. K-means uses all five standardized domain scores.
- LiNC comparisons can identify resource-alignment questions and peer communities, but they cannot establish policy effectiveness without longitudinal intervention and comparison data.
