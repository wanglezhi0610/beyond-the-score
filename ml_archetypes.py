from __future__ import annotations

import json
import os
import re
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
CDC_DIR = PROJECT_DIR.parent
OUTPUT_DIR = PROJECT_DIR / "outputs" / "ml"
FIGURE_DIR = OUTPUT_DIR / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("MPLCONFIGDIR", str(OUTPUT_DIR / ".mplconfig"))
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.ticker import PercentFormatter, StrMethodFormatter
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import StandardScaler


RANDOM_STATE = 2026
SELECTED_K = 6
DOMAINS = ["Economic", "Education", "Health", "Housing", "Crime"]

SCHOOL_PATH = PROJECT_DIR / "outputs" / "nc_school_sensitivity.csv"
EDUCATION_PATH = CDC_DIR / "supplemental_data" / "LiNC" / "education.csv"
EMPLOYMENT_PATH = (
    CDC_DIR / "supplemental_data" / "LiNC" / "employment-and-income-linc.csv"
)

PALETTE = ["#2171b5", "#6baed6", "#74c476", "#fd8d3c", "#e6550d", "#a50f15"]


def normalize_county(value: object) -> str:
    text = str(value).lower().replace("&", "and")
    text = re.sub(r"\bcounty\b", "", text)
    key = re.sub(r"[^a-z0-9]+", "", text)
    # LiNC contains two county-label typos in historical/source rows.
    # Salisbury is the county seat of Rowan; "Herford" is a misspelling of Hertford.
    return {"salisbury": "rowan", "herford": "hertford"}.get(key, key)


def load_schools() -> pd.DataFrame:
    schools = pd.read_csv(
        SCHOOL_PATH,
        dtype={"FIPS County Code": "string", "nces_id": "string"},
    )
    schools["county_fips"] = schools["FIPS County Code"].str.zfill(5)
    schools["county_key"] = schools["County"].map(normalize_county)
    schools["imputed_domain_count"] = schools[DOMAINS].isna().sum(axis=1)
    schools["imputed_domains"] = schools[DOMAINS].isna().apply(
        lambda row: ", ".join(row.index[row].tolist()), axis=1
    )
    return schools


def evaluate_k_values(x_scaled: np.ndarray) -> pd.DataFrame:
    rows: list[dict[str, float | int | bool | str]] = []
    total_variation = float(np.square(x_scaled - x_scaled.mean(axis=0)).sum())

    for k in range(3, 9):
        model = KMeans(n_clusters=k, n_init=50, random_state=RANDOM_STATE)
        labels = model.fit_predict(x_scaled)
        seed_aris = []
        for seed in range(20):
            alternate = KMeans(n_clusters=k, n_init=10, random_state=seed)
            seed_aris.append(adjusted_rand_score(labels, alternate.fit_predict(x_scaled)))

        sizes = np.bincount(labels)
        rows.append(
            {
                "k": k,
                "silhouette": silhouette_score(x_scaled, labels),
                "inertia": model.inertia_,
                "variance_explained": 1 - model.inertia_ / total_variation,
                "calinski_harabasz": calinski_harabasz_score(x_scaled, labels),
                "davies_bouldin": davies_bouldin_score(x_scaled, labels),
                "minimum_cluster_size": int(sizes.min()),
                "largest_cluster_size": int(sizes.max()),
                "mean_seed_ari": float(np.mean(seed_aris)),
                "minimum_seed_ari": float(np.min(seed_aris)),
                "selected": k == SELECTED_K,
                "selection_note": (
                    "Selected for interpretable stress archetypes while retaining high seed stability"
                    if k == SELECTED_K
                    else ""
                ),
            }
        )
    return pd.DataFrame(rows)


def semantic_labels(
    centers_raw: pd.DataFrame, centers_z: pd.DataFrame
) -> dict[int, str]:
    """Assign reproducible human-reviewed names from centroid shape and level."""
    available = set(centers_raw.index.tolist())
    labels: dict[int, str] = {}

    broad_lower = centers_raw.loc[list(available), DOMAINS].mean(axis=1).idxmin()
    labels[int(broad_lower)] = "Broadly Lower Stress"
    available.remove(broad_lower)

    economic_crime = (
        centers_z.loc[list(available), ["Economic", "Crime"]].mean(axis=1).idxmax()
    )
    labels[int(economic_crime)] = "Economic and Crime Concentrated"
    available.remove(economic_crime)

    education_health = (
        centers_z.loc[list(available), ["Education", "Health"]].mean(axis=1).idxmax()
    )
    labels[int(education_health)] = "Education and Health Pressure"
    available.remove(education_health)

    centered = centers_raw.loc[list(available), DOMAINS].sub(
        centers_raw.loc[list(available), DOMAINS].mean(axis=1), axis=0
    )
    housing = centered["Housing"].idxmax()
    labels[int(housing)] = "Housing-Concentrated Stress"
    available.remove(housing)

    multidomain = centers_raw.loc[list(available), DOMAINS].mean(axis=1).idxmax()
    labels[int(multidomain)] = "Multidomain Elevated Stress"
    available.remove(multidomain)

    remaining = available.pop()
    labels[int(remaining)] = "Moderate Stress, Lower Housing"
    return labels


def fit_archetypes(schools: pd.DataFrame):
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    x_imputed = imputer.fit_transform(schools[DOMAINS])
    x_scaled = scaler.fit_transform(x_imputed)

    diagnostics = evaluate_k_values(x_scaled)
    model = KMeans(n_clusters=SELECTED_K, n_init=50, random_state=RANDOM_STATE)
    raw_cluster = model.fit_predict(x_scaled)

    centers_raw = pd.DataFrame(
        scaler.inverse_transform(model.cluster_centers_), columns=DOMAINS
    )
    centers_z = pd.DataFrame(model.cluster_centers_, columns=DOMAINS)
    names_by_raw_cluster = semantic_labels(centers_raw, centers_z)

    label_order = [
        "Broadly Lower Stress",
        "Moderate Stress, Lower Housing",
        "Housing-Concentrated Stress",
        "Education and Health Pressure",
        "Multidomain Elevated Stress",
        "Economic and Crime Concentrated",
    ]
    archetype_id_by_name = {name: index + 1 for index, name in enumerate(label_order)}

    result = schools.copy()
    result["raw_cluster"] = raw_cluster
    result["archetype"] = result["raw_cluster"].map(names_by_raw_cluster)
    result["archetype_id"] = result["archetype"].map(archetype_id_by_name)

    for domain_index, domain in enumerate(DOMAINS):
        result[f"model_{domain.lower()}"] = x_imputed[:, domain_index]

    result["distance_to_centroid"] = np.linalg.norm(
        x_scaled - model.cluster_centers_[raw_cluster], axis=1
    )
    result["most_elevated_domain_vs_state"] = [
        DOMAINS[index] for index in np.argmax(x_scaled, axis=1)
    ]
    result["sensitivity_class"] = pd.cut(
        result["score_range_90"],
        bins=[-np.inf, 5, 8, np.inf],
        labels=["Stable", "Moderately sensitive", "Highly sensitive"],
        right=False,
    ).astype("string")

    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    pca_coordinates = pca.fit_transform(x_scaled)
    result["pca_1"] = pca_coordinates[:, 0]
    result["pca_2"] = pca_coordinates[:, 1]

    profile_rows = []
    for raw_id, name in names_by_raw_cluster.items():
        members = result["raw_cluster"].eq(raw_id)
        row: dict[str, object] = {
            "archetype_id": archetype_id_by_name[name],
            "archetype": name,
            "school_count": int(members.sum()),
            "share_of_schools": float(members.mean()),
            "median_stress_score": float(result.loc[members, "equal_weight_score"].median()),
            "median_sensitivity_range": float(result.loc[members, "score_range_90"].median()),
            "highly_sensitive_share": float(
                result.loc[members, "sensitivity_class"].eq("Highly sensitive").mean()
            ),
        }
        for domain in DOMAINS:
            row[f"{domain.lower()}_centroid"] = float(centers_raw.loc[raw_id, domain])
            row[f"{domain.lower()}_z"] = float(centers_z.loc[raw_id, domain])
        profile_rows.append(row)

    profiles = pd.DataFrame(profile_rows).sort_values("archetype_id")
    return result, profiles, diagnostics, x_scaled, model, pca


def build_nearest_peers(
    school_results: pd.DataFrame, x_scaled: np.ndarray, peers_per_school: int = 5
) -> pd.DataFrame:
    distance_matrix = pairwise_distances(x_scaled, metric="euclidean")
    rows = []
    for index in range(len(school_results)):
        same_cluster = np.flatnonzero(
            school_results["archetype_id"].to_numpy()
            == school_results.iloc[index]["archetype_id"]
        )
        same_cluster = same_cluster[same_cluster != index]
        nearest = same_cluster[np.argsort(distance_matrix[index, same_cluster])][
            :peers_per_school
        ]
        source = school_results.iloc[index]
        for rank, peer_index in enumerate(nearest, start=1):
            peer = school_results.iloc[peer_index]
            rows.append(
                {
                    "school_name": source["Name"],
                    "school_district": source["School District"],
                    "county": source["County"],
                    "archetype": source["archetype"],
                    "peer_rank": rank,
                    "peer_school": peer["Name"],
                    "peer_district": peer["School District"],
                    "peer_county": peer["County"],
                    "standardized_distance": distance_matrix[index, peer_index],
                }
            )
    return pd.DataFrame(rows)


def read_linc(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path, sep=";", low_memory=False)
    data.columns = [column.replace("\ufeff", "") for column in data.columns]
    type_column = "Area Type" if "Area Type" in data.columns else "Type"
    data = data.loc[data[type_column].astype("string").str.strip().eq("County")].copy()
    data["county_key"] = data["Area Name"].map(normalize_county)
    data["Year"] = pd.to_numeric(data["Year"], errors="coerce")
    data["Value"] = pd.to_numeric(data["Value"], errors="coerce")
    return data


def extract_linc_metric(
    data: pd.DataFrame, variable: str, year: int, output_name: str
) -> pd.DataFrame:
    metric = data.loc[
        data["Variable"].eq(variable) & data["Year"].eq(year),
        ["county_key", "Value"],
    ].copy()
    if metric["county_key"].nunique() != 100:
        raise ValueError(
            f"Expected 100 counties for {variable} ({year}); found {metric['county_key'].nunique()}."
        )
    if metric["Value"].isna().any():
        raise ValueError(f"Missing values for {variable} ({year}).")
    return metric.rename(columns={"Value": output_name})


def prepare_county_context(school_results: pd.DataFrame) -> pd.DataFrame:
    education = read_linc(EDUCATION_PATH)
    employment = read_linc(EMPLOYMENT_PATH)

    county = (
        school_results[["county_key", "county_fips", "County"]]
        .drop_duplicates("county_key")
        .rename(columns={"County": "county_name"})
    )
    if len(county) != 100:
        raise ValueError(f"Expected 100 NC counties in ODIS; found {len(county)}.")

    education_metrics = [
        ("Public School Expenditures (000s)", 2024, "total_expenditures_thousands_2024"),
        ("Public School Expenditures - Local (000s)", 2024, "local_expenditures_thousands_2024"),
        ("Public School Expenditures - Federal (000s)", 2024, "federal_expenditures_thousands_2024"),
        ("Public School Expenditures - State (000s)", 2024, "state_expenditures_thousands_2024"),
        ("Public School Final Average Daily Membership", 2024, "average_daily_membership_2024"),
        ("Public School Final Average Daily Attendance", 2024, "average_daily_attendance_2024"),
        ("Public School Instructional Personnel", 2024, "instructional_personnel_2024"),
        ("Public High School Final Enrollment", 2024, "high_school_enrollment_2024"),
        ("Public High School Dropouts", 2024, "high_school_dropouts_2024"),
    ]
    employment_metrics = [
        ("Unemployment Rate by Place of Residence (Percent)", 2024, "unemployment_rate_2024"),
        ("Estimated Median Family Income(HUD)", 2024, "median_family_income_hud_2024"),
        ("Percent of Persons in Poverty", 2023, "poverty_rate_2023"),
    ]

    for variable, year, output_name in education_metrics:
        county = county.merge(
            extract_linc_metric(education, variable, year, output_name),
            on="county_key",
            how="left",
            validate="one_to_one",
        )
    for variable, year, output_name in employment_metrics:
        county = county.merge(
            extract_linc_metric(employment, variable, year, output_name),
            on="county_key",
            how="left",
            validate="one_to_one",
        )

    county["spending_per_student_2024"] = (
        county["total_expenditures_thousands_2024"] * 1000
        / county["average_daily_membership_2024"]
    )
    county["instructional_personnel_per_1000_students_2024"] = (
        county["instructional_personnel_2024"]
        / county["average_daily_membership_2024"]
        * 1000
    )
    county["attendance_rate_2024"] = (
        county["average_daily_attendance_2024"]
        / county["average_daily_membership_2024"]
        * 100
    )
    county["local_funding_share_2024"] = (
        county["local_expenditures_thousands_2024"]
        / county["total_expenditures_thousands_2024"]
        * 100
    )
    county["state_funding_share_2024"] = (
        county["state_expenditures_thousands_2024"]
        / county["total_expenditures_thousands_2024"]
        * 100
    )
    county["federal_funding_share_2024"] = (
        county["federal_expenditures_thousands_2024"]
        / county["total_expenditures_thousands_2024"]
        * 100
    )
    county["dropouts_per_1000_high_school_students_2024"] = (
        county["high_school_dropouts_2024"]
        / county["high_school_enrollment_2024"]
        * 1000
    )
    county["source_name_correction_note"] = np.where(
        county["county_name"].eq("Rowan County"),
        "LiNC labels Rowan County as Salisbury County for 2024 public high-school enrollment; normalized to Rowan County.",
        "",
    )

    derived = [
        "spending_per_student_2024",
        "instructional_personnel_per_1000_students_2024",
        "attendance_rate_2024",
        "local_funding_share_2024",
        "state_funding_share_2024",
        "federal_funding_share_2024",
        "dropouts_per_1000_high_school_students_2024",
        "unemployment_rate_2024",
        "median_family_income_hud_2024",
        "poverty_rate_2023",
    ]
    if county[derived].isna().any().any():
        missing = county[derived].isna().sum()
        missing = missing.loc[missing.gt(0)].to_dict()
        affected = county.loc[
            county[derived].isna().any(axis=1), ["county_name", *derived]
        ]
        raise ValueError(
            "County context contains missing derived metrics after LiNC join. "
            f"Counts: {missing}. Affected rows: {affected.to_dict(orient='records')}"
        )
    return county.sort_values("county_fips")


def build_county_cluster_context(
    school_results: pd.DataFrame,
    county_context: pd.DataFrame,
    profiles: pd.DataFrame,
) -> pd.DataFrame:
    counts = pd.crosstab(school_results["county_fips"], school_results["archetype_id"])
    counts = counts.reindex(columns=range(1, SELECTED_K + 1), fill_value=0)
    counts.columns = [f"archetype_{column}_school_count" for column in counts.columns]
    shares = counts.div(counts.sum(axis=1), axis=0)
    shares.columns = [column.replace("school_count", "share") for column in counts.columns]

    summary = school_results.groupby("county_fips", as_index=True).agg(
        odis_school_count=("Name", "size"),
        mean_stress_score=("equal_weight_score", "mean"),
        median_sensitivity_range=("score_range_90", "median"),
    )
    composition = summary.join(counts).join(shares).reset_index()

    higher_stress_labels = {
        "Education and Health Pressure",
        "Multidomain Elevated Stress",
        "Economic and Crime Concentrated",
    }
    higher_stress_ids = profiles.loc[
        profiles["archetype"].isin(higher_stress_labels), "archetype_id"
    ].astype(int)
    composition["higher_stress_archetype_share"] = composition[
        [f"archetype_{cluster_id}_share" for cluster_id in higher_stress_ids]
    ].sum(axis=1)

    dominant_id = counts.idxmax(axis=1).str.extract(r"(\d+)", expand=False).astype(int)
    name_lookup = profiles.set_index("archetype_id")["archetype"]
    composition["dominant_archetype"] = composition["county_fips"].map(
        dominant_id.map(name_lookup)
    )

    combined = county_context.merge(
        composition, on="county_fips", how="left", validate="one_to_one"
    )
    stress_cutoff = combined["mean_stress_score"].quantile(0.75)
    spending_median = combined["spending_per_student_2024"].median()
    personnel_median = combined[
        "instructional_personnel_per_1000_students_2024"
    ].median()
    combined["resource_alignment_review"] = (
        combined["mean_stress_score"].ge(stress_cutoff)
        & (
            combined["spending_per_student_2024"].lt(spending_median)
            | combined["instructional_personnel_per_1000_students_2024"].lt(
                personnel_median
            )
        )
    )
    combined["review_rule"] = (
        "Top quartile of county mean school-community stress and below the NC county median "
        "for spending per student or instructional personnel per 1,000 students"
    )
    return combined.sort_values("county_fips")


def save_model_selection_plot(diagnostics: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    axes[0].plot(diagnostics["k"], diagnostics["silhouette"], marker="o", color="#086b62")
    axes[0].axvline(SELECTED_K, color="#c8423a", linestyle="--", linewidth=1.5)
    axes[0].set(title="Cluster separation", xlabel="Number of clusters (K)", ylabel="Silhouette score")
    axes[0].annotate(
        "Selected K=6",
        (SELECTED_K, diagnostics.loc[diagnostics["k"].eq(SELECTED_K), "silhouette"].iloc[0]),
        xytext=(8, 10),
        textcoords="offset points",
    )

    axes[1].plot(diagnostics["k"], diagnostics["mean_seed_ari"], marker="o", color="#2171b5")
    axes[1].axvline(SELECTED_K, color="#c8423a", linestyle="--", linewidth=1.5)
    axes[1].set(title="Random-initialization stability", xlabel="Number of clusters (K)", ylabel="Mean adjusted Rand index")
    axes[1].set_ylim(0.8, 1.01)
    fig.suptitle("K-means model selection: separation and stability", fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "model_selection.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_profile_plot(profiles: pd.DataFrame) -> None:
    ordered = profiles.sort_values("archetype_id")
    z_columns = [f"{domain.lower()}_z" for domain in DOMAINS]
    raw_columns = [f"{domain.lower()}_centroid" for domain in DOMAINS]
    z_values = ordered[z_columns].to_numpy()
    raw_annotations = ordered[raw_columns].round(1).astype(str).to_numpy()

    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    sns.heatmap(
        z_values,
        annot=raw_annotations,
        fmt="",
        cmap="RdYlBu_r",
        center=0,
        vmin=-1.5,
        vmax=1.5,
        linewidths=0.8,
        linecolor="white",
        cbar_kws={"label": "Centroid deviation from NC average (standard deviations)"},
        ax=ax,
    )
    ax.set_xticklabels(DOMAINS, rotation=0)
    ax.set_yticklabels(
        [f"{name} (n={count})" for name, count in zip(ordered["archetype"], ordered["school_count"])],
        rotation=0,
    )
    ax.set_xlabel("ODIS domain; cells show centroid score on the 0–100 scale")
    ax.set_ylabel("")
    ax.set_title("School-community stress archetypes", fontsize=15, fontweight="bold", pad=14)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "cluster_profiles.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_pca_plot(schools: pd.DataFrame, pca: PCA) -> None:
    fig, ax = plt.subplots(figsize=(10, 7))
    for archetype_id, group in schools.groupby("archetype_id", sort=True):
        name = group["archetype"].iloc[0]
        ax.scatter(
            group["pca_1"],
            group["pca_2"],
            s=34,
            alpha=0.72,
            color=PALETTE[int(archetype_id) - 1],
            label=f"{archetype_id}. {name}",
            edgecolors="none",
        )
        ax.scatter(
            group["pca_1"].mean(),
            group["pca_2"].mean(),
            s=150,
            marker="X",
            color=PALETTE[int(archetype_id) - 1],
            edgecolors="white",
            linewidths=1.2,
        )
    variance = pca.explained_variance_ratio_ * 100
    ax.set_xlabel(f"Principal component 1 ({variance[0]:.1f}% of variation)")
    ax.set_ylabel(f"Principal component 2 ({variance[1]:.1f}% of variation)")
    ax.set_title("Two-dimensional view of the six stress archetypes", fontsize=15, fontweight="bold")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    ax.axhline(0, color="#c8d2cf", linewidth=0.8)
    ax.axvline(0, color="#c8d2cf", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "pca_clusters.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_resource_alignment_plot(counties: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 7))
    for archetype_id, name in enumerate(
        [
            "Broadly Lower Stress",
            "Moderate Stress, Lower Housing",
            "Housing-Concentrated Stress",
            "Education and Health Pressure",
            "Multidomain Elevated Stress",
            "Economic and Crime Concentrated",
        ],
        start=1,
    ):
        group = counties.loc[counties["dominant_archetype"].eq(name)]
        ax.scatter(
            group["mean_stress_score"],
            group["spending_per_student_2024"],
            s=30 + group["odis_school_count"] * 5,
            color=PALETTE[archetype_id - 1],
            alpha=0.78,
            edgecolors="white",
            linewidths=0.7,
            label=name,
        )
    x_cutoff = counties["mean_stress_score"].quantile(0.75)
    y_cutoff = counties["spending_per_student_2024"].median()
    ax.axvline(x_cutoff, color="#5e6b68", linestyle="--", linewidth=1.1)
    ax.axhline(y_cutoff, color="#5e6b68", linestyle="--", linewidth=1.1)
    review = counties.loc[counties["resource_alignment_review"]].nlargest(
        8, "odis_school_count"
    )
    offsets = [(6, 6), (6, -12), (-6, 7), (-6, -12), (6, 12), (6, -18), (-6, 15), (-6, -20)]
    for (_, row), offset in zip(review.iterrows(), offsets):
        ax.annotate(
            row["county_name"].replace(" County", ""),
            (row["mean_stress_score"], row["spending_per_student_2024"]),
            xytext=offset,
            textcoords="offset points",
            fontsize=8,
            ha="left" if offset[0] > 0 else "right",
        )
    ax.set_xlabel("County mean school-community stress score")
    ax.set_ylabel("2024 public-school spending per student")
    ax.yaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
    ax.set_title("County resource context and school stress archetypes", fontsize=15, fontweight="bold")
    ax.text(
        0.01,
        0.01,
        "Dashed lines: 75th percentile of county mean stress and median county spending.",
        transform=ax.transAxes,
        fontsize=9,
        color="#5e6b68",
    )
    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        title="Dominant school archetype",
        fontsize=8,
    )
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "resource_alignment.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def export_results() -> None:
    schools = load_schools()
    school_results, profiles, diagnostics, x_scaled, model, pca = fit_archetypes(schools)
    peers = build_nearest_peers(school_results, x_scaled)
    county_context = prepare_county_context(school_results)
    county_cluster_context = build_county_cluster_context(
        school_results, county_context, profiles
    )

    school_columns = [
        "Name",
        "School District",
        "County",
        "county_fips",
        "City",
        "latitude",
        "longitude",
        *DOMAINS,
        "equal_weight_score",
        "score_p05",
        "score_p95",
        "score_range_90",
        "sensitivity_class",
        "archetype_id",
        "archetype",
        "most_elevated_domain_vs_state",
        "distance_to_centroid",
        "imputed_domain_count",
        "imputed_domains",
        *[f"model_{domain.lower()}" for domain in DOMAINS],
        "pca_1",
        "pca_2",
    ]
    school_results[school_columns].sort_values(
        ["archetype_id", "distance_to_centroid"]
    ).to_csv(OUTPUT_DIR / "school_archetypes.csv", index=False)
    profiles.to_csv(OUTPUT_DIR / "cluster_profiles.csv", index=False)
    diagnostics.to_csv(OUTPUT_DIR / "model_selection.csv", index=False)
    peers.to_csv(OUTPUT_DIR / "nearest_peers.csv", index=False)
    county_context.to_csv(OUTPUT_DIR / "county_context.csv", index=False)
    county_cluster_context.to_csv(
        OUTPUT_DIR / "county_cluster_context.csv", index=False
    )

    save_model_selection_plot(diagnostics)
    save_profile_plot(profiles)
    save_pca_plot(school_results, pca)
    save_resource_alignment_plot(county_cluster_context)

    best_silhouette_row = diagnostics.loc[diagnostics["silhouette"].idxmax()]
    selected_row = diagnostics.loc[diagnostics["k"].eq(SELECTED_K)].iloc[0]
    summary = {
        "schools_clustered": int(len(school_results)),
        "schools_with_imputed_domains": int(
            school_results["imputed_domain_count"].gt(0).sum()
        ),
        "selected_k": SELECTED_K,
        "highest_silhouette_k": int(best_silhouette_row["k"]),
        "highest_silhouette": round(float(best_silhouette_row["silhouette"]), 4),
        "selected_k_silhouette": round(float(selected_row["silhouette"]), 4),
        "selected_k_mean_seed_ari": round(float(selected_row["mean_seed_ari"]), 4),
        "selected_k_minimum_cluster_size": int(selected_row["minimum_cluster_size"]),
        "pca_two_component_variance_percent": round(
            float(pca.explained_variance_ratio_.sum() * 100), 1
        ),
        "counties_with_complete_linc_context": int(len(county_context)),
        "counties_flagged_for_resource_alignment_review": int(
            county_cluster_context["resource_alignment_review"].sum()
        ),
        "supplemental_sources": [
            "LiNC Education",
            "LiNC Employment and Income",
        ],
        "interpretation_boundary": (
            "Clusters describe recurring school-community stress profiles. LiNC metrics provide county context. "
            "Neither establishes causality or policy effectiveness."
        ),
    }
    (OUTPUT_DIR / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    web_school_columns = [
        "Name",
        "School District",
        "County",
        "county_fips",
        "latitude",
        "longitude",
        *DOMAINS,
        "equal_weight_score",
        "score_range_90",
        "sensitivity_class",
        "archetype_id",
        "archetype",
        "most_elevated_domain_vs_state",
        "distance_to_centroid",
        "pca_1",
        "pca_2",
    ]
    web_county_columns = [
        "county_name",
        "county_fips",
        "mean_stress_score",
        "dominant_archetype",
        "higher_stress_archetype_share",
        "spending_per_student_2024",
        "instructional_personnel_per_1000_students_2024",
        "attendance_rate_2024",
        "unemployment_rate_2024",
        "median_family_income_hud_2024",
        "poverty_rate_2023",
        "resource_alignment_review",
    ]
    web_payload = {
        "summary": summary,
        "profiles": json.loads(profiles.to_json(orient="records")),
        "modelSelection": json.loads(diagnostics.to_json(orient="records")),
        "schools": json.loads(
            school_results[web_school_columns].to_json(orient="records")
        ),
        "counties": json.loads(
            county_cluster_context[web_county_columns].to_json(orient="records")
        ),
    }
    (OUTPUT_DIR / "archetype_web_data.json").write_text(
        json.dumps(web_payload, separators=(",", ":")), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2))
    print("\nCluster profiles:")
    print(
        profiles[
            [
                "archetype_id",
                "archetype",
                "school_count",
                "median_stress_score",
                "median_sensitivity_range",
            ]
            + [f"{domain.lower()}_centroid" for domain in DOMAINS]
        ].round(2).to_string(index=False)
    )


if __name__ == "__main__":
    export_results()
