# ODIS weight sensitivity map

This prototype tests how North Carolina school-community rankings change when the five ODIS domain weights change.

## Method

- The equal-weight reference assigns 20% to each domain.
- Interactive weights always sum to 100%.
- If a school is missing a domain, the selected weights are renormalized over its available domains, following the ODIS technical report.
- The map recalculates a 0–100 Community Stress Score whenever a weight changes. A higher score means greater stress on the measured community indicators; it is not a probability or school-performance rating.
- The score sensitivity range is the difference between the 95th and 5th percentile of a school's stress score over 2,500 sampled weight combinations.
- Every sampled domain weight remains between 10% and 40%. This is an explicit scenario range, not an official ODIS standard.

The current prototype changes only the five domain weights. It does not yet vary the weights of individual indicators within a domain.

## Build the prepared data

From this directory:

```bash
python3 -m pip install -r requirements.txt
python3 prepare_data.py
```

This creates:

- `outputs/nc_school_sensitivity.csv`: analysis-ready school data.
- `outputs/unmatched_nces_review.csv`: ODIS schools needing manual location review.
- `web/data.js`: compact data used by the browser prototype.

## Open the interactive map

Open `web/index.html` in a browser. The data are loaded from a local JavaScript file, so a local server is not required. D3 and the US county boundary file are loaded from jsDelivr.

## Publish with GitHub Pages

This folder includes `.github/workflows/pages.yml`, which publishes the contents of `web/` as a static GitHub Pages site.

1. Create a GitHub repository and place the contents of this `weight_sensitivity_map` folder at the repository root.
2. Push the repository's `main` branch.
3. In GitHub, open **Settings → Pages** and set **Source** to **GitHub Actions**.
4. Run the **Deploy dashboard to GitHub Pages** workflow if it does not start automatically.

The public address will be `https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/`.

## Source files

- `../Open Data Index for Schools (ODIS)/index_scores_v3_2026.csv`
- `../supplemental_data/NCES_2024_25/EDGE_GEOCODE_PUBLICSCH_2425.xlsx`

LiNC files are preserved for a later county-context layer. They are not used in this weight-sensitivity prototype because the core calculation should first be validated independently of supplemental variables.
