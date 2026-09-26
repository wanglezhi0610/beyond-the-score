(() => {
  const payload = window.NC_SENSITIVITY_DATA;
  const allSchools = payload.schools;
  const schools = allSchools.filter(school => school.lat !== null && school.lon !== null);
  const domains = payload.metadata.domains;

  let weights = [20, 20, 20, 20, 20];
  let selectedSchool = null;
  let countySummary = new Map();
  let svg;
  let viewport;
  let zoomBehavior;
  let projection;
  let currentZoom = 1;

  const rootStyle = getComputedStyle(document.documentElement);
  const colors = ["--low", "--mid-low", "--mid", "--mid-high", "--high"]
    .map(variable => rootStyle.getPropertyValue(variable).trim());

  const controls = d3.select("#weight-controls")
    .selectAll("div")
    .data(domains)
    .join("div")
    .attr("class", "weight-control");

  controls.html((domain, index) => `
    <label for="weight-${index}"><span>${domain}</span><output id="weight-value-${index}">20%</output></label>
    <input id="weight-${index}" type="range" min="0" max="100" step="1" value="20" aria-label="${domain} weight">
  `);

  controls.select("input").on("input", function(_, domain) {
    rebalance(domains.indexOf(domain), Number(this.value));
    updateAll();
  });

  d3.select("#reset").on("click", () => {
    weights = [20, 20, 20, 20, 20];
    updateAll();
  });
  d3.select("#color-mode").on("change", updateMapEncoding);

  function rebalance(changedIndex, newValue) {
    newValue = Math.max(0, Math.min(100, newValue));
    const remainder = 100 - newValue;
    const otherTotal = weights.reduce(
      (sum, value, index) => index === changedIndex ? sum : sum + value,
      0,
    );
    const next = weights.slice();
    next[changedIndex] = newValue;
    next.forEach((value, index) => {
      if (index === changedIndex) return;
      next[index] = otherTotal === 0 ? remainder / 4 : value / otherTotal * remainder;
    });
    weights = next;
  }

  function weightedScore(school) {
    let numerator = 0;
    let denominator = 0;
    school.domains.forEach((value, index) => {
      if (value !== null) {
        numerator += value * weights[index];
        denominator += weights[index];
      }
    });
    return denominator ? numerator / denominator : NaN;
  }

  function calculateCurrentScores() {
    allSchools.forEach(school => {
      school.currentScore = weightedScore(school);
      school.scoreChange = school.currentScore - school.baselineScore;
    });

    countySummary = d3.rollup(
      schools,
      values => ({
        score: d3.median(values, value => value.currentScore),
        change: d3.median(values, value => value.scoreChange),
        sensitivity: d3.median(values, value => value.scoreRange),
        count: values.length,
      }),
      value => value.countyFips,
    );
  }

  function stressBin(value) {
    if (value < 20) return 0;
    if (value < 30) return 1;
    if (value < 40) return 2;
    if (value < 50) return 3;
    return 4;
  }

  function changeBin(value) {
    if (value < -5) return 0;
    if (value < -2) return 1;
    if (value <= 2) return 2;
    if (value <= 5) return 3;
    return 4;
  }

  function sensitivityBin(value) {
    if (value < 3) return 0;
    if (value < 5) return 1;
    if (value < 8) return 2;
    if (value < 12) return 3;
    return 4;
  }

  function currentMode() {
    return document.getElementById("color-mode").value;
  }

  function schoolColor(school) {
    if (currentMode() === "change") return colors[changeBin(school.scoreChange)];
    if (currentMode() === "sensitivity") return colors[sensitivityBin(school.scoreRange)];
    return colors[stressBin(school.currentScore)];
  }

  function schoolRadius(school) {
    if (currentMode() === "change") return 5.2 + Math.min(5.8, Math.abs(school.scoreChange) * 0.72);
    if (currentMode() === "sensitivity") return 5.2 + Math.min(5.8, school.scoreRange * 0.30);
    return 6.2;
  }

  function countyColor(feature) {
    const summary = countySummary.get(String(feature.id).padStart(5, "0"));
    if (!summary) return null;
    if (currentMode() === "change") return colors[changeBin(summary.change)];
    if (currentMode() === "sensitivity") return colors[sensitivityBin(summary.sensitivity)];
    return colors[stressBin(summary.score)];
  }

  function updateControls() {
    weights.forEach((weight, index) => {
      document.getElementById(`weight-${index}`).value = weight;
      document.getElementById(`weight-value-${index}`).value = `${weight.toFixed(0)}%`;
      document.getElementById(`weight-value-${index}`).textContent = `${weight.toFixed(0)}%`;
    });
  }

  function updateSummary() {
    const changedFive = schools.filter(school => Math.abs(school.scoreChange) >= 5).length;
    const medianShift = d3.median(schools, school => Math.abs(school.scoreChange));
    document.getElementById("mapped-count").textContent = schools.length.toLocaleString();
    document.getElementById("changed-five").textContent = changedFive.toLocaleString();
    document.getElementById("median-shift").textContent = `${medianShift.toFixed(1)} pts`;
  }

  function drawLegend() {
    const labels = currentMode() === "change"
      ? ["Decrease >5", "Decrease 2–5", "Within ±2", "Increase 2–5", "Increase >5"]
      : currentMode() === "sensitivity"
        ? ["<3", "3–5", "5–8", "8–12", "12+ score pts"]
        : ["0–20", "20–30", "30–40", "40–50", "50–100 stress"];

    d3.select("#legend").selectAll("span.legend-item")
      .data(labels)
      .join("span")
      .attr("class", "legend-item")
      .html((label, index) => `<span class="legend-swatch" style="background:${colors[index]}"></span>${label}`);
  }

  function updateMapEncoding() {
    drawLegend();
    if (!svg) return;

    viewport.selectAll("path.county")
      .transition().duration(180)
      .attr("fill", feature => countyColor(feature) || rootStyle.getPropertyValue("--surface-soft").trim());

    viewport.selectAll("circle.school")
      .transition().duration(180)
      .attr("fill", schoolColor)
      .attr("r", school => schoolRadius(school) / Math.sqrt(currentZoom));
  }

  function countyContext(school) {
    return countySummary.get(school.countyFips) || { score: NaN, change: NaN };
  }

  function renderDetail(school) {
    if (!school) return;
    selectedSchool = school;
    viewport.selectAll("circle.school").classed("selected", value => value === school);
    const county = countyContext(school);
    const rows = domains.map((domain, index) => {
      const value = school.domains[index];
      const width = value === null ? 0 : value;
      return `<div class="domain-row"><span>${domain}</span><div class="bar-track"><div class="bar" style="width:${width}%"></div></div><strong>${value === null ? "n.a." : value.toFixed(0)}</strong></div>`;
    }).join("");

    const signedChange = `${school.scoreChange >= 0 ? "+" : ""}${school.scoreChange.toFixed(1)}`;
    const countyChange = `${county.change >= 0 ? "+" : ""}${county.change.toFixed(1)}`;

    document.getElementById("detail").innerHTML = `
      <h2>${school.name}</h2>
      <p class="school-meta">${school.district}<br>${school.city}, ${school.county}</p>
      <div class="score-definition"><strong>Community Stress Score</strong><span>0 = lower measured stress · 100 = higher measured stress</span></div>
      <div class="detail-metrics">
        <div><strong>${school.currentScore.toFixed(1)}</strong><span>Current stress score</span></div>
        <div><strong>${signedChange}</strong><span>Change from equal weights</span></div>
        <div><strong>${school.scoreP05.toFixed(1)}–${school.scoreP95.toFixed(1)}</strong><span>Scenario score range</span></div>
        <div><strong>${countyChange}</strong><span>County median change</span></div>
      </div>
      <h2>Domain scores</h2>
      <div class="domain-list">${rows}</div>
      <p class="method-note">${school.availableIndicators}/17 underlying indicators available. ${school.sab ? "School attendance boundary available." : "Attendance boundary unavailable; ODIS uses a ZIP/tract proxy."}</p>
    `;
  }

  function updateAll() {
    calculateCurrentScores();
    updateControls();
    updateSummary();
    updateMapEncoding();
    if (selectedSchool) renderDetail(selectedSchool);
  }

  function showSchoolTooltip(event, school) {
    const tip = document.getElementById("tooltip");
    tip.hidden = false;
    tip.innerHTML = `<strong>${school.name}</strong><br>${school.county}<br>Stress score: ${school.currentScore.toFixed(1)}<br>Change: ${school.scoreChange >= 0 ? "+" : ""}${school.scoreChange.toFixed(1)}<br>Sensitivity: ${school.scoreRange.toFixed(1)} score points`;
    tip.style.left = `${event.clientX + 12}px`;
    tip.style.top = `${event.clientY + 12}px`;
  }

  function showCountyTooltip(event, feature) {
    const summary = countySummary.get(String(feature.id).padStart(5, "0"));
    if (!summary) return;
    const tip = document.getElementById("tooltip");
    tip.hidden = false;
    tip.innerHTML = `<strong>County summary</strong><br>${summary.count} mapped schools<br>Median stress score: ${summary.score.toFixed(1)}<br>Median change: ${summary.change >= 0 ? "+" : ""}${summary.change.toFixed(1)}`;
    tip.style.left = `${event.clientX + 12}px`;
    tip.style.top = `${event.clientY + 12}px`;
  }

  function hideTooltip() {
    document.getElementById("tooltip").hidden = true;
  }

  function configureZoom(width, height) {
    zoomBehavior = d3.zoom()
      .scaleExtent([1, 8])
      .translateExtent([[0, 0], [width, height]])
      .extent([[0, 0], [width, height]])
      .on("zoom", event => {
        currentZoom = event.transform.k;
        viewport.attr("transform", event.transform);
        viewport.selectAll("circle.school")
          .attr("r", school => schoolRadius(school) / Math.sqrt(currentZoom));
        document.getElementById("zoom-slider").value = event.transform.k;
      });
    svg.call(zoomBehavior);

    d3.select("#zoom-in").on("click", () => svg.transition().duration(180).call(zoomBehavior.scaleBy, 1.4));
    d3.select("#zoom-out").on("click", () => svg.transition().duration(180).call(zoomBehavior.scaleBy, 1 / 1.4));
    d3.select("#zoom-reset").on("click", () => svg.transition().duration(180).call(zoomBehavior.transform, d3.zoomIdentity));
    d3.select("#zoom-slider").on("input", function() {
      svg.call(zoomBehavior.scaleTo, Number(this.value));
    });
  }

  async function drawMap() {
    const width = 850;
    const height = 620;
    svg = d3.select("#map").append("svg")
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("aria-label", "North Carolina school-community stress scores, changes, and weighting sensitivity");
    viewport = svg.append("g");

    try {
      const us = await d3.json("https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json");
      const countyFeatures = topojson.feature(us, us.objects.counties).features
        .filter(feature => String(feature.id).padStart(5, "0").startsWith("37"));
      projection = d3.geoAlbers().fitExtent([[22, 22], [width - 22, height - 22]], {
        type: "FeatureCollection",
        features: countyFeatures,
      });
      const path = d3.geoPath(projection);
      viewport.append("g").selectAll("path")
        .data(countyFeatures)
        .join("path")
        .attr("class", "county")
        .attr("d", path)
        .attr("fill", feature => countyColor(feature) || rootStyle.getPropertyValue("--surface-soft").trim())
        .on("mousemove", showCountyTooltip)
        .on("mouseleave", hideTooltip);
    } catch (error) {
      projection = d3.geoAlbers()
        .center([-79.3, 35.4])
        .rotate([0, 0])
        .parallels([33, 45])
        .scale(6500)
        .translate([width / 2, height / 2]);
    }

    viewport.append("g").selectAll("circle")
      .data(schools)
      .join("circle")
      .attr("class", "school")
      .attr("cx", school => projection([school.lon, school.lat])[0])
      .attr("cy", school => projection([school.lon, school.lat])[1])
      .attr("r", schoolRadius)
      .attr("fill", schoolColor)
      .attr("tabindex", 0)
      .attr("aria-label", school => `${school.name}, ${school.county}, stress score ${school.currentScore.toFixed(1)}`)
      .on("mousemove", showSchoolTooltip)
      .on("mouseleave", hideTooltip)
      .on("click", (_, school) => renderDetail(school))
      .on("keydown", (event, school) => {
        if (event.key === "Enter" || event.key === " ") renderDetail(school);
      });

    configureZoom(width, height);
    updateMapEncoding();
  }

  calculateCurrentScores();
  updateControls();
  updateSummary();
  drawLegend();
  drawMap();
})();
