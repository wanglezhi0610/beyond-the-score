# CDC Submission Draft

Replace every `YOUR-USERNAME`, `YOUR-REPOSITORY`, `YOUR-VIDEO-LINK`, and team-member placeholder before submitting.

## Project title

**Beyond the Score: NC School Community Stress Explorer**

## One-line tagline

An explainable AI tool that audits subjective stress-score weights and reveals distinct school-community stress archetypes for more context-aware public decisions.

## About the project

### Inspiration

A single composite score can make a complicated community look simple. The Open Data Index for Schools (ODIS) combines economic, education, health, housing, and crime indicators, but its final score depends on analyst-selected weights. We wanted to ask two questions that a ranking alone cannot answer:

1. **Would a school still look highly stressed if the priorities behind the score changed?**
2. **Do schools with similar overall scores actually face different combinations of challenges?**

Our project was inspired by the idea that responsible AI for social good should not hide assumptions. It should help educators, community organizations, and policymakers see uncertainty, compare structurally similar communities, and ask better resource-allocation questions.

### What it does

Beyond the Score has two connected parts.

First, the interactive map lets a user change the weights assigned to the five ODIS domains. The map immediately recalculates each North Carolina school's **Community Stress Score**, while a sensitivity layer shows which schools remain stable and which move substantially under reasonable alternative priorities. We sampled 2,500 weight combinations, constraining every domain to 10%–40%, rather than treating one weighting scheme as unquestionable.

Second, our machine-learning pipeline uses K-means clustering on the five standardized ODIS domain scores. It does **not** use the existing composite score as an input. The model groups 600 North Carolina schools into six interpretable community-stress archetypes, such as broadly lower stress, housing-concentrated stress, education-and-health pressure, multidomain elevated stress, and economic-and-crime-concentrated stress. This reframes the question from “Which school ranks worse?” to “What pattern of challenges surrounds this school?”

We then join two NC OSBM LiNC datasets after clustering: county education resources and county employment/income conditions. These data provide context for comparing archetypes and identifying counties that may deserve closer human review. They are not used to force the clusters or claim that a policy caused an outcome.

### How we built it

We cleaned the ODIS records in Python and matched North Carolina schools to 2024–25 NCES EDGE public-school geocodes. The current map includes 588 successfully matched schools; 12 unmatched records are retained for manual review rather than silently discarded.

For the map, we used HTML, CSS, JavaScript, D3.js, and TopoJSON. Users can adjust five weights that always sum to 100%, zoom and pan, switch between stress and sensitivity views, and inspect school-level tooltips. When a school is missing a domain, the selected weights are renormalized over the domains available for that school.

For the machine-learning analysis, we standardized the five domain scores and evaluated K from 3 through 8 using silhouette score, inertia, Calinski–Harabasz score, Davies–Bouldin score, minimum cluster size, and stability across 20 random initializations. Although K=4 had the highest silhouette score (0.2610), we selected K=6 because it preserved useful, interpretable distinctions while retaining a minimum cluster size of 60 and strong random-initialization stability (mean adjusted Rand index = 0.9684). The selected model's silhouette score was 0.2527. PCA was used only for visualization; the clustering used all five standardized domains.

We used two supplemental LiNC sources:

- **Education (2024):** spending per student, instructional personnel per 1,000 students, attendance, funding shares, and high-school dropout rate.
- **Employment and Income:** 2024 unemployment, 2024 HUD median family income, and 2023 poverty rate.

LiNC variables were joined only after clustering, so the archetypes describe ODIS stress patterns rather than available resources. A transparent review rule flags counties in the top quartile of mean school-community stress and below the North Carolina county median for spending per student or instructional personnel. The 13 flagged counties are conversation starters, not automated funding recommendations.

### Responsible AI and social good

Our AI contribution is not prediction for prediction's sake. It is an **explainable, human-in-the-loop decision-support system**:

- It exposes how subjective weights affect a school's score.
- It replaces one-dimensional ranking with interpretable multivariate archetypes.
- It identifies comparable peer communities without using student-level personal data.
- It keeps resource context separate from the model, making the logic easier to audit.
- It explicitly avoids causal claims, punitive school labels, and automated policy decisions.

The goal is to help decision-makers tailor questions and possible interventions to the pattern of need. A housing-concentrated community may require a different partnership from a community facing simultaneous economic, health, and crime pressures, even if their composite scores are similar.

### Challenges

The largest data challenge was school matching. ODIS identifiers were not consistently usable for a direct join, so we created a conservative name-and-location matching process and preserved unmatched schools for review. We also had to keep school-level stress data separate from county-level LiNC context so that county averages were not misrepresented as school-specific resources.

The modeling challenge was that no single K is objectively “correct.” We balanced quantitative validation, cluster stability, minimum group size, and whether the groups told meaningfully different social stories. Seven schools also had at least one missing domain, so we median-imputed values only for fitting and disclosed every affected record in the output.

Finally, responsible communication was a challenge. Cross-sectional associations cannot establish policy effectiveness. We therefore describe clusters as archetypes, sensitivity as scenario analysis, and resource flags as prompts for human review.

### Accomplishments we are proud of

- Built a working interactive map with adjustable weights, zooming, tooltips, and clear stress/sensitivity legends.
- Mapped 588 North Carolina schools and retained an auditable list of 12 unmatched records.
- Clustered all 600 North Carolina ODIS schools into six stable and interpretable archetypes.
- Evaluated multiple K values and random initializations instead of presenting one unexplained model.
- Integrated two LiNC subject areas covering all 100 North Carolina counties.
- Produced school archetypes, nearest archetype peers, county context, model diagnostics, and reproducible visual outputs.
- Made uncertainty and interpretation limits part of the product rather than a footnote.

### What we learned

We learned that two schools can have similar composite scores but very different underlying stress profiles. We also learned that “explainable AI” is not only about explaining a model after it runs; it begins with exposing human choices such as weights, variables, geographic aggregation, and the number of clusters.

Technically, we learned how to combine geospatial matching, scenario simulation, unsupervised learning, cluster validation, PCA visualization, and data from different geographic levels. Most importantly, we learned that social-good analytics should support human judgment, not replace it.

### What's next

Next, we would add a second interactive **Archetype Explorer** to the website so users can filter clusters, compare domain profiles, and locate nearest peer communities. We would manually review the remaining geocode matches, test longitudinal data where comparable years are available, and co-design archetype names and resource questions with educators and community organizations. A future version would also include subgroup fairness checks and carefully designed outcome evaluation before making any claim about policy effectiveness.

## Built with

Use these tags/technologies:

- Python
- pandas
- NumPy
- scikit-learn
- Matplotlib
- Seaborn
- JavaScript
- D3.js
- TopoJSON
- HTML5
- CSS3
- GitHub
- GitHub Actions
- GitHub Pages
- ODIS
- NCES EDGE Geocodes
- NC OSBM LiNC

Do not list R, Power BI, SQL, or an external AI API unless the final submitted project actually uses them.

## Try it out links

- **Live demo:** `https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/`
- **Source code and reproducible outputs:** `https://github.com/YOUR-USERNAME/YOUR-REPOSITORY`
- **Video demo:** `YOUR-VIDEO-LINK`

The live site currently demonstrates the interactive weight-sensitivity map. The clustering code, diagnostics, and outputs are in the repository and project media.

## Track

**Social Sciences**

## Additional/external datasets

Paste this answer:

> Yes. We used the NCES EDGE School Geocodes for public-school locations (2024–25), NC OSBM LiNC Education data (2024), and NC OSBM LiNC Employment and Income data (2023–24). NCES coordinates support the school map. LiNC education and employment/income variables are joined after clustering as county-level context; they are not used as K-means training inputs. Our primary dataset is the Open Data Index for Schools (ODIS).

Suggested source links:

- ODIS: https://doi.org/10.7281/T170WN53
- NCES public-school locations: https://catalog.data.gov/dataset/public-school-locations-2024-25
- NC OSBM LiNC: https://linc.osbm.nc.gov/

## What is your project's purpose?

> Beyond the Score helps educators, community organizations, and policymakers understand both the uncertainty and the structure hidden by a single school-community stress score. It shows how rankings change when domain priorities change, then uses unsupervised learning to identify different combinations of economic, education, health, housing, and crime stress. The purpose is transparent, context-aware decision support—not ranking schools or automating funding decisions.

## How did your project incorporate AI for Social Good?

> We use explainable unsupervised machine learning to group 600 North Carolina schools into six recurring community-stress archetypes based on five standardized ODIS domains. This can help decision-makers distinguish, for example, housing-concentrated stress from multidomain stress and identify relevant peer communities. We pair the model with weight-sensitivity analysis and county resource context so users can audit assumptions instead of accepting a black-box ranking. The tool uses no student-level personal data, makes no causal or policy-effectiveness claims, and keeps people in control of interpretation and action.

## How did you build this project?

> We cleaned ODIS and NCES data in Python, matched North Carolina schools to NCES coordinates, and generated 2,500 alternative domain-weight scenarios. We built the interactive map with D3.js, JavaScript, HTML, CSS, and TopoJSON. For machine learning, we standardized the five ODIS domains, evaluated K=3–8 with several quality and stability metrics, and selected a six-cluster K-means model. PCA supports visualization only. Finally, we joined NC OSBM LiNC education and employment/income metrics after clustering to add county context. GitHub Actions deploys the static map to GitHub Pages.

## What were some challenges?

> School identifiers did not support a perfect direct geocode join, so we used conservative name-and-location matching and preserved unmatched records for review. We also had to choose K without pretending there was one mathematically correct social taxonomy, handle seven schools with missing domain values transparently, reconcile school-level ODIS data with county-level LiNC data, and avoid turning cross-sectional patterns into unsupported causal claims.

## What are some accomplishments you are proud of?

> We built a working interactive map for 588 matched schools, clustered all 600 North Carolina ODIS schools, achieved strong six-cluster stability across random initializations (mean adjusted Rand index 0.9684), and integrated county context covering all 100 North Carolina counties. We are especially proud that the project makes uncertainty, missingness, geographic level, and interpretation boundaries visible to users.

## What did you learn?

> We learned that similar composite scores can hide very different patterns of community need. We also learned that responsible AI requires more than a model: it requires transparent preprocessing, sensitivity testing, multiple validation metrics, careful labels, and clear limits on what the data can prove. Technically, we gained experience with geospatial joins, scenario simulation, K-means, PCA, cluster stability, D3, and reproducible deployment.

## What's next?

> We plan to add an interactive Archetype Explorer, complete manual review of the remaining geocodes, validate the archetype language with educators and community partners, and incorporate longitudinal data where comparable measures exist. Before making resource or policy recommendations, we would add fairness checks and a causal evaluation design.

## Project media upload order

Upload these four images in this order:

1. `outputs/dashboard-preview.png` — caption: **Interactive map showing how school-community stress changes as domain priorities change.**
2. `outputs/ml/figures/cluster_profiles.png` — caption: **Six interpretable school-community stress archetypes learned from the five ODIS domains.**
3. `outputs/ml/figures/pca_clusters.png` — caption: **Two-dimensional PCA view of the six clusters; PCA is used for visualization, not model fitting.**
4. `outputs/ml/figures/resource_alignment.png` — caption: **County-level LiNC context used to surface resource-alignment questions, not causal conclusions.**

Use the dashboard preview as the cover image. The files are already below the 5 MB per-image limit.

## 90-second video plan

Record the screen in landscape orientation and keep the browser zoom large enough to read.

- **0–10 seconds:** “A single school-community stress score hides both subjective choices and different types of need. We built Beyond the Score to make those differences visible.”
- **10–35 seconds:** Show the map, move two domain-weight sliders, use the zoom control, and hover over a school. Explain that the color updates to show the Community Stress Score and that sensitivity captures how much the score changes across 2,500 reasonable weighting scenarios.
- **35–55 seconds:** Show `cluster_profiles.png`. Explain that K-means uses the five domains—not the composite score—to identify six recurring stress archetypes across 600 NC schools.
- **55–70 seconds:** Show `pca_clusters.png` and mention the K=3–8 validation and strong K=6 stability. Do not describe PCA separation as perfect.
- **70–82 seconds:** Show `resource_alignment.png`. Explain that LiNC education and employment/income metrics add county context after clustering.
- **82–90 seconds:** “This is human-in-the-loop AI: it reveals assumptions and helps communities ask better questions, but it does not rank schools, determine funding, or claim causality.”

Upload the video to YouTube as **Unlisted** or to another host that judges can open without requesting access, then paste its public link into the video field.

## Final submission checklist

- [ ] Replace every placeholder in this file.
- [ ] Add both team members and verify name spelling.
- [ ] Make the GitHub repository public for judging.
- [ ] Confirm the GitHub Pages demo opens in a private/incognito window.
- [ ] Confirm all sliders, zooming, reset, views, and tooltips work.
- [ ] Confirm the video opens without signing in or requesting permission.
- [ ] Upload the four media images and add captions.
- [ ] Upload `CDC_Beyond_the_Score_Submission.zip` in the file-upload field.
- [ ] Select **Social Sciences**.
- [ ] Credit ODIS, NCES EDGE, and NC OSBM LiNC.
- [ ] Do not claim that the resource flag proves policy effectiveness or recommends funding.
- [ ] Preview the submission page before clicking Submit.
