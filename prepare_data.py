from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
CDC_DIR = PROJECT_DIR.parent
ODIS_PATH = CDC_DIR / "Open Data Index for Schools (ODIS)" / "index_scores_v3_2026.csv"
NCES_PATH = CDC_DIR / "supplemental_data" / "NCES_2024_25" / "EDGE_GEOCODE_PUBLICSCH_2425.xlsx"
OUTPUT_DIR = PROJECT_DIR / "outputs"
WEB_DIR = PROJECT_DIR / "web"

DOMAINS = ["Economic", "Education", "Health", "Housing", "Crime"]
INDICATORS = [
    "Unemployment",
    "Poverty",
    "Access to broadband internet",
    "Single-parent households",
    "Linguistic isolation",
    "Access to healthcare",
    "Infant mortality rate",
    "SNAP recipients",
    "Low birth weight",
    "Lead exposure risk",
    "Housing vacancy rate",
    "Housing affordability",
    "Park access",
    "Violent crime rate",
    "Incarceration rate",
    "Less than HS",
    "2-year college or higher",
]


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    text = text.lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "", text)


def normalize_zip(value: object) -> str:
    digits = re.sub(r"\D", "", str(value))
    return digits[:5].zfill(5)


def load_sources() -> tuple[pd.DataFrame, pd.DataFrame]:
    odis = pd.read_csv(
        ODIS_PATH,
        dtype={"Zip Code": "string", "FIPS County Code": "string", "NCESSCH": "string"},
        na_values=["N/A", "Null"],
    )
    odis = odis.loc[odis["State"].eq("NC")].copy()

    nces = pd.read_excel(
        NCES_PATH,
        dtype={"NCESSCH": "string", "ZIP": "string", "CNTY": "string", "STFIP": "string"},
    )
    nces = nces.loc[nces["STATE"].eq("NC")].copy()

    for frame, name_col, zip_col, city_col in [
        (odis, "Name", "Zip Code", "City"),
        (nces, "NAME", "ZIP", "CITY"),
    ]:
        frame["_name"] = frame[name_col].map(normalize_text)
        frame["_zip"] = frame[zip_col].map(normalize_zip)
        frame["_city"] = frame[city_col].map(normalize_text)
    return odis, nces


def match_locations(odis: pd.DataFrame, nces: pd.DataFrame) -> pd.DataFrame:
    """Match ODIS to NCES without relying on ODIS's damaged scientific-notation ID."""
    rows: list[dict[str, object]] = []

    for odis_index, school in odis.iterrows():
        candidates = nces.loc[
            nces["_name"].eq(school["_name"]) & nces["_zip"].eq(school["_zip"])
        ]
        method = "exact_name_zip"
        score = 100.0

        if len(candidates) != 1:
            candidates = nces.loc[
                nces["_name"].eq(school["_name"]) & nces["_city"].eq(school["_city"])
            ]
            method = "exact_name_city"

        if len(candidates) != 1:
            candidates = nces.loc[nces["_name"].eq(school["_name"])]
            method = "unique_exact_name"

        if len(candidates) == 1:
            match = candidates.iloc[0]
        else:
            candidates = nces.loc[nces["_zip"].eq(school["_zip"])].copy()
            method = "fuzzy_name_same_zip"
            if candidates.empty:
                candidates = nces.loc[
                    nces["NMCNTY"].astype("string").str.lower().eq(str(school["County"]).lower())
                ].copy()
                method = "fuzzy_name_same_county"

            if candidates.empty:
                match = None
                score = 0.0
            else:
                candidates["_similarity"] = candidates["_name"].map(
                    lambda name: 100 * SequenceMatcher(None, school["_name"], name).ratio()
                )
                match = candidates.nlargest(1, "_similarity").iloc[0]
                score = float(match["_similarity"])

        accepted = match is not None and (
            method.startswith("exact")
            or method == "unique_exact_name"
            or score >= 80.0
        )

        rows.append(
            {
                "odis_index": odis_index,
                "nces_name": match["NAME"] if match is not None else pd.NA,
                "nces_id": match["NCESSCH"] if accepted else pd.NA,
                "latitude": pd.to_numeric(match["LAT"], errors="coerce") if accepted else np.nan,
                "longitude": pd.to_numeric(match["LON"], errors="coerce") if accepted else np.nan,
                "match_method": method if accepted else "unmatched_review_required",
                "match_score": score,
                "suggested_nces_name": match["NAME"] if match is not None else pd.NA,
            }
        )

    matches = pd.DataFrame(rows).set_index("odis_index")
    return odis.join(matches)


def sample_plausible_weights(n: int = 2500, seed: int = 20260926) -> np.ndarray:
    """Sample domain weights where every domain remains between 10% and 40%."""
    rng = np.random.default_rng(seed)
    accepted: list[np.ndarray] = []
    while sum(len(batch) for batch in accepted) < n:
        batch = rng.dirichlet(np.ones(5), size=max(n, 4000))
        batch = batch[(batch.min(axis=1) >= 0.10) & (batch.max(axis=1) <= 0.40)]
        accepted.append(batch)
    return np.vstack(accepted)[:n]


def weighted_scores(domain_values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    available = ~np.isnan(domain_values)
    values = np.nan_to_num(domain_values, nan=0.0)
    numerator = weights @ values.T
    denominator = weights @ available.astype(float).T
    return numerator / denominator


def add_sensitivity_metrics(data: pd.DataFrame) -> pd.DataFrame:
    domain_values = data[DOMAINS].astype(float).to_numpy()
    scenarios = sample_plausible_weights()
    scenario_scores = weighted_scores(domain_values, scenarios)

    equal_weights = np.full((1, 5), 0.20)
    baseline_scores = weighted_scores(domain_values, equal_weights)[0]

    data = data.copy()
    data["equal_weight_score"] = baseline_scores
    data["score_p05"] = np.percentile(scenario_scores, 5, axis=0)
    data["score_p50"] = np.percentile(scenario_scores, 50, axis=0)
    data["score_p95"] = np.percentile(scenario_scores, 95, axis=0)
    data["score_range_90"] = data["score_p95"] - data["score_p05"]
    data["available_domains"] = data[DOMAINS].notna().sum(axis=1)
    data["available_indicators"] = data[INDICATORS].notna().sum(axis=1)
    return data


def export_outputs(data: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DIR.mkdir(parents=True, exist_ok=True)

    export_columns = [
        "Name",
        "School District",
        "County",
        "City",
        "Zip Code",
        "FIPS County Code",
        "SAB Available",
        "nces_id",
        "nces_name",
        "latitude",
        "longitude",
        "match_method",
        "match_score",
        *DOMAINS,
        "Composite Score",
        "equal_weight_score",
        "score_p05",
        "score_p50",
        "score_p95",
        "score_range_90",
        "available_domains",
        "available_indicators",
    ]
    data[export_columns].to_csv(OUTPUT_DIR / "nc_school_sensitivity.csv", index=False)

    unmatched = data.loc[data["latitude"].isna(), [
        "Name",
        "School District",
        "County",
        "City",
        "Zip Code",
        "match_score",
        "suggested_nces_name",
    ]]
    unmatched.to_csv(OUTPUT_DIR / "unmatched_nces_review.csv", index=False)

    records = []
    for _, row in data.iterrows():
        record = {
            "name": row["Name"],
            "district": row["School District"],
            "county": row["County"],
            "countyFips": str(row["FIPS County Code"]).zfill(5),
            "city": row["City"],
            "zip": str(row["Zip Code"]),
            "lat": None if pd.isna(row["latitude"]) else round(float(row["latitude"]), 6),
            "lon": None if pd.isna(row["longitude"]) else round(float(row["longitude"]), 6),
            "domains": [None if pd.isna(row[d]) else float(row[d]) for d in DOMAINS],
            "publishedScore": float(row["Composite Score"]),
            "baselineScore": round(float(row["equal_weight_score"]), 3),
            "scoreP05": round(float(row["score_p05"]), 2),
            "scoreP95": round(float(row["score_p95"]), 2),
            "scoreRange": round(float(row["score_range_90"]), 2),
            "availableDomains": int(row["available_domains"]),
            "availableIndicators": int(row["available_indicators"]),
            "sab": int(row["SAB Available"]),
            "matchMethod": row["match_method"],
        }
        records.append(record)

    payload = {
        "metadata": {
            "domains": DOMAINS,
            "mappedSchools": int(data["latitude"].notna().sum()),
            "totalNcSchools": len(data),
            "sensitivityScenarios": 2500,
            "weightFloor": 0.10,
            "weightCeiling": 0.40,
        },
        "schools": records,
    }
    with (WEB_DIR / "data.js").open("w", encoding="utf-8") as handle:
        handle.write("window.NC_SENSITIVITY_DATA = ")
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write(";\n")


def main() -> None:
    odis, nces = load_sources()
    matched = match_locations(odis, nces)
    analyzed = add_sensitivity_metrics(matched)
    export_outputs(analyzed)

    mapped = analyzed["latitude"].notna().sum()
    score_delta = (analyzed["equal_weight_score"] - analyzed["Composite Score"]).abs()
    print(f"Prepared {len(analyzed)} NC ODIS schools; mapped {mapped}; review {len(analyzed) - mapped}.")
    print(f"Median absolute difference from published rounded composite: {score_delta.median():.3f}.")
    print(f"Maximum absolute difference from published rounded composite: {score_delta.max():.3f}.")


if __name__ == "__main__":
    main()
