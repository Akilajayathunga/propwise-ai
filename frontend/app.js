const apiBaseUrl = "http://127.0.0.1:8000";

const form = document.querySelector("#requirements-form");
const queryInput = document.querySelector("#query");
const submitButton = document.querySelector("#submit-button");
const intentTitle = document.querySelector("#intent-title");
const confidence = document.querySelector("#confidence");
const message = document.querySelector("#message");
const fieldGrid = document.querySelector("#field-grid");
const jsonBlock = document.querySelector("#json-block");
const jsonOutput = document.querySelector("#json-output");
const propertiesPanel = document.querySelector("#properties-panel");
const planningPanel = document.querySelector("#planning-panel");
const optionsTitle = document.querySelector("#options-title");
const modal = document.querySelector("#option-modal");
const modalContent = document.querySelector("#modal-content");
const modalClose = document.querySelector("#modal-close");

let latestOptions = [];

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) {
    showError("Please enter a property request.");
    return;
  }

  setLoading(true);
  resetResults("Understanding your request...");

  try {
    const requirements = await postJson("/api/v1/requirements/parse", { query });
    showRequirements(requirements);

    if (shouldSearchProperties(requirements.intent)) {
      message.textContent = requirements.intent === "LAND_AND_HOUSE" ? "Finding land options..." : "Searching properties...";
      const searchResult = await postJson("/api/v1/property-search", { requirements, top_n: 10 });

      if (requirements.intent === "LAND_AND_HOUSE") {
        message.textContent = "Generating land and house combinations...";
        const evaluation = await postJson("/api/v1/planning/evaluate-land-house", {
          requirements,
          property_results: searchResult.results,
        });
        showLandHouseOptions(evaluation, requirements);
      } else {
        showProperties(searchResult);
      }
    }

    if (requirements.intent === "PLAN_HOUSE") {
      message.textContent = "Generating conceptual plan...";
      showPlanning(await postJson("/api/v1/planning/generate", buildPlanningRequest(requirements, null)));
    }

    message.classList.add("hidden");
  } catch (error) {
    showError(error instanceof Error ? error.message : "Unable to reach the backend.");
  } finally {
    setLoading(false);
  }
});

modalClose.addEventListener("click", closeModal);
modal.addEventListener("click", (event) => {
  if (event.target.dataset.closeModal !== undefined) closeModal();
});

async function postJson(path, body) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
  return response.json();
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Working..." : "Send";
}

function resetResults(text) {
  message.className = "empty-text";
  message.textContent = text;
  message.classList.remove("hidden");
  fieldGrid.classList.add("hidden");
  jsonBlock.classList.add("hidden");
  propertiesPanel.classList.add("hidden");
  planningPanel.classList.add("hidden");
}

function showError(errorMessage) {
  intentTitle.textContent = "Unable to parse";
  confidence.classList.add("hidden");
  fieldGrid.classList.add("hidden");
  jsonBlock.classList.add("hidden");
  propertiesPanel.classList.add("hidden");
  planningPanel.classList.add("hidden");
  message.className = "error-text";
  message.textContent = errorMessage;
  message.classList.remove("hidden");
}

function showRequirements(result) {
  intentTitle.textContent = requirementTitle(result.intent);
  confidence.textContent = `${Math.round((result.confidence || 0) * 100)}%`;
  confidence.classList.remove("hidden");

  const items = [
    ["Goal", requirementTitle(result.intent)],
    ["Location", result.location],
    ["Home", homeSummary(result)],
    ["Project budget", formatCompactMoney(result.total_project_budget_lkr)],
    ["Land budget", formatCompactMoney(result.maximum_land_budget_lkr)],
    ["Construction budget", formatCompactMoney(result.construction_budget_lkr)],
    ["Property type", result.property_type],
  ].filter(([, value]) => value && value !== "Not provided");

  fieldGrid.innerHTML = "";
  items.forEach(([label, value]) => fieldGrid.appendChild(summaryItem(label, value)));
  fieldGrid.classList.remove("hidden");

  jsonOutput.textContent = JSON.stringify(result, null, 2);
  jsonBlock.classList.remove("hidden");
}

function showLandHouseOptions(evaluation, requirements) {
  const list = document.querySelector("#property-list");
  const count = document.querySelector("#property-count");
  const analysis = document.querySelector("#market-analysis");

  latestOptions = evaluation.options || [];
  propertiesPanel.classList.remove("hidden");
  optionsTitle.textContent = "Best Land + House Options";
  count.textContent = `${evaluation.returned} options`;
  analysis.textContent = evaluation.warnings?.length
    ? friendlyWarnings(evaluation.warnings)
    : `Showing combinations for ${homeSummary(requirements)}.`;
  analysis.classList.remove("hidden");
  list.className = "option-grid";
  list.innerHTML = "";

  if (!latestOptions.length) {
    const empty = document.createElement("p");
    empty.className = "empty-text";
    empty.textContent = "No land and house combinations could be evaluated.";
    list.appendChild(empty);
    return;
  }

  latestOptions.forEach((option, index) => list.appendChild(optionCard(option, index)));
}

function optionCard(option, index) {
  const property = option.property || {};
  const house = option.house || {};
  const budget = option.budget || {};
  const planning = option.planning || {};
  const card = document.createElement("article");
  card.className = "option-card";

  const top = document.createElement("div");
  top.className = "option-topline";
  const badge = document.createElement("span");
  badge.className = "match-badge";
  badge.textContent = index === 0 ? "Best match" : `Option ${index + 1}`;
  const score = document.createElement("strong");
  score.textContent = `${Math.round(option.combination_score || 0)}%`;
  top.append(badge, score);

  const title = document.createElement("h3");
  title.textContent = `${property.location || "Land"}${property.land_size_perches ? ` - ${property.land_size_perches} perches` : ""}`;

  const subtitle = document.createElement("p");
  subtitle.className = "muted";
  subtitle.textContent = [property.district, property.title].filter(Boolean).join(" - ");

  const preview = document.createElement("button");
  preview.className = "plan-preview";
  preview.type = "button";
  preview.addEventListener("click", () => openOptionModal(option));
  const svgUrl = firstPlanUrl(planning.svg_url);
  if (svgUrl) {
    const img = document.createElement("img");
    img.src = svgUrl;
    img.alt = "Conceptual floor plan preview";
    preview.appendChild(img);
  } else {
    preview.textContent = "Plan needs adjustment";
  }

  const houseLine = document.createElement("div");
  houseLine.className = "house-line";
  houseLine.textContent = `${formatCount(house.bedrooms, "Bed")} - ${formatCount(house.bathrooms, "Bath")} - ${formatCount(house.floors, "Floor")} - ${formatCount(house.parking_spaces, "Parking")}`;

  const area = document.createElement("p");
  area.className = "muted";
  area.textContent = `Approx. ${formatValue(house.estimated_floor_area_sqft)} sqft`;

  const budgetBlock = document.createElement("div");
  budgetBlock.className = "project-budget";
  [
    ["Land price", formatCompactMoney(budget.land_price_lkr)],
    ["Construction estimate", constructionRange(budget)],
    ["Expected total", formatCompactMoney(budget.total_expected_lkr)],
    ["Maximum total budget", formatCompactMoney(budget.total_project_budget_lkr)],
    ["Expected margin", formatCompactMoney(budget.expected_margin_lkr)],
  ].forEach(([label, value]) => budgetBlock.appendChild(budgetRow(label, value)));

  const status = document.createElement("div");
  status.className = `status-badge ${String(budget.budget_status || "").toLowerCase().replaceAll("_", "-")}`;
  status.textContent = friendlyStatus(budget.budget_status);

  const actions = document.createElement("div");
  actions.className = "option-actions";
  actions.appendChild(actionButton("View details", () => openOptionModal(option)));
  actions.appendChild(downloadLink("SVG", planning.svg_url));
  actions.appendChild(downloadLink("DXF", planning.dxf_url));

  card.append(top, title, subtitle, preview, houseLine, area, budgetBlock, status, actions);
  return card;
}

function showProperties(result) {
  const list = document.querySelector("#property-list");
  const count = document.querySelector("#property-count");
  const analysisDiv = document.querySelector("#market-analysis");
  propertiesPanel.classList.remove("hidden");
  optionsTitle.textContent = "Found Properties";
  count.textContent = `${result.returned} of ${result.total_found} results`;
  list.className = "property-list";
  analysisDiv.textContent = result.warnings?.join(" ") || "Property matches from the local dataset.";
  analysisDiv.classList.remove("hidden");
  list.innerHTML = "";
  result.results.forEach((p) => {
    const card = document.createElement("div");
    card.className = "property-card";
    const title = document.createElement("h3");
    title.textContent = p.title || p.listing_id || "Property";
    const meta = document.createElement("div");
    meta.className = "property-meta";
    [`${p.location || "Unknown"} ${p.district ? `(${p.district})` : ""}`, `${p.property_type} / ${p.listing_type}`, `Score ${Number(p.score || 0).toFixed(2)}`].forEach((text) => {
      const span = document.createElement("span");
      span.textContent = text;
      meta.appendChild(span);
    });
    const price = document.createElement("div");
    price.className = "property-price";
    price.textContent = p.listing_type === "rent" ? `${formatMoney(p.rent_monthly_lkr)} / month` : formatMoney(p.sale_total_price_lkr || p.price_lkr);
    card.append(title, meta, price);
    list.appendChild(card);
  });
}

function showPlanning(result) {
  const score = document.querySelector("#planning-score");
  const budgetGrid = document.querySelector("#budget-grid");
  const warnings = document.querySelector("#planning-warnings");
  const preview = document.querySelector("#design-preview");
  const floorTabs = document.querySelector("#floor-tabs");
  const jsonOutput = document.querySelector("#planning-json-output");

  planningPanel.classList.remove("hidden");
  score.textContent = result.layout_score === null || result.layout_score === undefined ? "No score" : `${Math.round(result.layout_score)}%`;
  const roomSummary = summarizeRooms(result.plan?.rooms || []);
  budgetGrid.innerHTML = "";
  [
    ["Bedrooms", roomSummary.bedrooms],
    ["Bathrooms", roomSummary.bathrooms],
    ["Floors", result.plan?.floors?.length],
    ["Floor area", result.estimated_floor_area_sqft ? `${formatValue(result.estimated_floor_area_sqft)} sqft` : null],
    ["Budget status", friendlyStatus(result.budget_status)],
  ]
    .filter(([, value]) => value !== null && value !== undefined)
    .forEach(([label, value]) => budgetGrid.appendChild(summaryItem(label, value)));

  warnings.textContent = result.warnings?.join(" ") || "";
  warnings.classList.toggle("hidden", !result.warnings?.length);
  renderPlanPreview(preview, floorTabs, result.files?.svg || []);
  jsonOutput.textContent = JSON.stringify(result, null, 2);
}

function openOptionModal(option) {
  const property = option.property || {};
  const house = option.house || {};
  const budget = option.budget || {};
  const planning = option.planning || {};
  modalContent.innerHTML = "";

  const header = document.createElement("div");
  header.className = "modal-summary";
  header.append(
    summaryItem("Property", `${property.location || "Land"}${property.land_size_perches ? ` - ${property.land_size_perches} perches` : ""}`),
    summaryItem("House", `${formatCount(house.bedrooms, "Bed")} - ${formatCount(house.bathrooms, "Bath")} - ${formatCount(house.floors, "Floor")}`),
    summaryItem("Status", friendlyStatus(budget.budget_status)),
    summaryItem("Score", `${Math.round(option.combination_score || 0)}%`),
  );

  const planTabs = document.createElement("div");
  planTabs.className = "floor-tabs";
  const planPreview = document.createElement("div");
  planPreview.className = "design-preview modal-plan";
  renderPlanPreview(planPreview, planTabs, planning.svg_urls || [planning.svg_url].filter(Boolean));

  const budgetBlock = document.createElement("div");
  budgetBlock.className = "project-budget detail-budget";
  [
    ["Land purchase", formatCompactMoney(budget.land_price_lkr)],
    ["Construction low", formatCompactMoney(budget.construction_low_lkr)],
    ["Construction expected", formatCompactMoney(budget.construction_expected_lkr)],
    ["Construction high", formatCompactMoney(budget.construction_high_lkr)],
    ["Expected total", formatCompactMoney(budget.total_expected_lkr)],
    ["High total", formatCompactMoney(budget.total_high_lkr)],
    ["Maximum total budget", formatCompactMoney(budget.total_project_budget_lkr)],
    ["Expected margin", formatCompactMoney(budget.expected_margin_lkr)],
  ].forEach(([label, value]) => budgetBlock.appendChild(budgetRow(label, value)));

  const details = document.createElement("details");
  details.className = "json-block";
  const summary = document.createElement("summary");
  summary.textContent = "View technical data";
  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(option, null, 2);
  details.append(summary, pre);

  const downloads = document.createElement("div");
  downloads.className = "file-links";
  [["PNG", planning.png_url], ["SVG", planning.svg_url], ["DXF", planning.dxf_url], ["Plan JSON", planning.json_url]].forEach(([label, path]) => downloads.appendChild(downloadLink(label, path)));

  const warning = document.createElement("p");
  warning.className = "plan-notice";
  warning.textContent = "Conceptual AI-assisted plan - not construction-ready. Final design, cost, site suitability and approvals must be verified by qualified professionals.";

  modalContent.append(header, planTabs, planPreview, budgetBlock, downloads, warning, details);
  modal.classList.remove("hidden");
}

function closeModal() {
  modal.classList.add("hidden");
  modalContent.innerHTML = "";
}

function renderPlanPreview(container, tabs, svgPaths) {
  container.innerHTML = "";
  tabs.innerHTML = "";
  const urls = svgPaths.map(firstPlanUrl).filter(Boolean);
  if (!urls.length) {
    const empty = document.createElement("p");
    empty.className = "empty-text";
    empty.textContent = "Plan needs adjustment.";
    container.appendChild(empty);
    return;
  }
  const image = document.createElement("img");
  image.alt = "Generated conceptual floor plan";
  image.src = urls[0];
  container.appendChild(image);
  urls.forEach((url, index) => {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = index === 0 ? "floor-tab active" : "floor-tab";
    tab.textContent = index === 0 ? "Ground Floor" : `Floor ${index + 1}`;
    tab.addEventListener("click", () => {
      tabs.querySelectorAll(".floor-tab").forEach((button) => button.classList.remove("active"));
      tab.classList.add("active");
      image.src = url;
    });
    tabs.appendChild(tab);
  });
}

function buildPlanningRequest(requirements, searchResult) {
  const selectedProperty = requirements.intent === "LAND_AND_HOUSE" && searchResult?.results?.length ? searchResult.results[0] : null;
  return {
    intent: requirements.intent,
    selected_property: selectedProperty,
    location: requirements.location,
    land_size_perches: requirements.land_size_perches,
    total_project_budget_lkr: requirements.total_project_budget_lkr,
    construction_budget_lkr: requirements.construction_budget_lkr,
    bedrooms: requirements.bedrooms,
    bathrooms: requirements.bathrooms,
    floors: requirements.floors,
    parking_spaces: requirements.parking_spaces,
    preferred_style: requirements.preferred_style,
    finish_level: requirements.finish_level,
    office_required: requirements.office_required,
    balcony_required: requirements.balcony_required,
    family_lounge_required: requirements.family_lounge_required,
    utility_room_required: requirements.utility_room_required,
    other_requirements: requirements.preferences || [],
    candidate_count: 10,
  };
}

function shouldSearchProperties(intent) {
  return ["BUY_PROPERTY", "RENT_PROPERTY", "BUY_LAND", "LAND_AND_HOUSE", "COMPARE_PROPERTIES"].includes(intent);
}

function summaryItem(label, value) {
  const item = document.createElement("div");
  item.className = "field-item";
  const title = document.createElement("span");
  title.textContent = label;
  const strong = document.createElement("strong");
  strong.textContent = formatValue(value);
  item.append(title, strong);
  return item;
}

function budgetRow(label, value) {
  const row = document.createElement("div");
  const labelEl = document.createElement("span");
  labelEl.textContent = label;
  const valueEl = document.createElement("strong");
  valueEl.textContent = value;
  row.append(labelEl, valueEl);
  return row;
}

function actionButton(label, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "text-button";
  button.textContent = label;
  button.addEventListener("click", handler);
  return button;
}

function downloadLink(label, path) {
  const link = document.createElement("a");
  link.className = "text-button";
  const url = firstPlanUrl(path);
  if (url) {
    link.href = url;
    link.target = "_blank";
    link.rel = "noreferrer";
  } else {
    link.href = "#";
    link.setAttribute("aria-disabled", "true");
  }
  link.textContent = label;
  return link;
}

function requirementTitle(intent) {
  const labels = {
    LAND_AND_HOUSE: "Buy land + build",
    PLAN_HOUSE: "Plan a house",
    BUY_PROPERTY: "Buy property",
    RENT_PROPERTY: "Rent property",
    BUY_LAND: "Buy land",
    COMPARE_PROPERTIES: "Compare properties",
    ESTIMATE_BUDGET: "Estimate budget",
  };
  return labels[intent] || "Property request";
}

function homeSummary(result) {
  const parts = [];
  if (result.bedrooms) parts.push(`${result.bedrooms}-bedroom home`);
  if (result.bathrooms) parts.push(`${result.bathrooms} bathrooms`);
  if (result.floors) parts.push(`${result.floors} floor${result.floors === 1 ? "" : "s"}`);
  return parts.join(", ") || null;
}

function constructionRange(budget) {
  if (!budget.construction_low_lkr || !budget.construction_high_lkr) return "Cost data required";
  return `${formatCompactMoney(budget.construction_low_lkr)} - ${formatCompactMoney(budget.construction_high_lkr)}`;
}

function friendlyStatus(status) {
  const labels = {
    WITHIN_BUDGET: "Within budget",
    POTENTIALLY_FEASIBLE: "Potentially feasible",
    TIGHT_BUDGET: "Tight budget",
    ABOVE_BUDGET: "Above budget",
    COST_DATA_UNAVAILABLE: "Construction cost data required",
  };
  return labels[status] || "Needs review";
}

function friendlyWarnings(warnings) {
  return warnings.join(" ").replaceAll("COST_DATA_UNAVAILABLE", "construction cost data required");
}

function formatCount(value, label) {
  if (value === null || value === undefined) return `0 ${label}`;
  return `${value} ${label}${Number(value) === 1 ? "" : "s"}`;
}

function firstPlanUrl(path) {
  if (!path) return "";
  const normalized = String(path).replaceAll("\\", "/");
  const marker = "storage/plans/";
  const index = normalized.indexOf(marker);
  if (index === -1) return "";
  return `${apiBaseUrl}/plans/${normalized.slice(index + marker.length)}`;
}

function summarizeRooms(rooms) {
  return rooms.reduce(
    (summary, room) => {
      if (room.type === "bedroom" || room.type === "master_bedroom") summary.bedrooms += 1;
      if (room.type === "bathroom") summary.bathrooms += 1;
      return summary;
    },
    { bedrooms: 0, bathrooms: 0 },
  );
}

function formatValue(value) {
  if (value === null || value === undefined || value === "") return "Not provided";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "None";
  if (typeof value === "number") return value.toLocaleString("en-LK");
  return String(value);
}

function formatMoney(value) {
  if (value === null || value === undefined) return "Not provided";
  return `LKR ${Number(value).toLocaleString("en-LK")}`;
}

function formatCompactMoney(value) {
  if (value === null || value === undefined) return "Not provided";
  const number = Number(value);
  if (Math.abs(number) >= 1_000_000) return `Rs. ${(number / 1_000_000).toFixed(1)}M`;
  return `Rs. ${number.toLocaleString("en-LK")}`;
}
