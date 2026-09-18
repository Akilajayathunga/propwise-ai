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
    const empty = document.createElement("div");
    empty.className = "plan-empty-state";
    const strong = document.createElement("strong");
    strong.textContent = "Plan needs adjustment";
    const small = document.createElement("span");
    small.textContent = firstWarning(option) || "This land option is too tight or missing exact dimensions for a valid concept plan.";
    empty.append(strong, small);
    preview.appendChild(empty);
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
  actions.appendChild(actionButton("View ad details", () => openAdDetailsModal(option)));
  actions.appendChild(actionButton("Show budget summary", () => openBudgetSummaryModal(option)));
  actions.appendChild(fileDownloadButton("Download plan", planning.png_url || planning.svg_url));

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
  [
    ["Budget doc", planning.budget_doc_url],
    ["SVG", planning.svg_url],
  ].forEach(([label, path]) => downloads.appendChild(downloadLink(label, path)));
  [
    ["Plan image", planning.png_url],
    ["Budget CSV", planning.budget_csv_url],
    ["DXF", planning.dxf_url],
    ["Plan JSON", planning.json_url],
  ].forEach(([label, path]) => downloads.appendChild(fileDownloadButton(label, path)));

  const warning = document.createElement("p");
  warning.className = "plan-notice";
  warning.textContent = "Conceptual AI-assisted plan - not construction-ready. Final design, cost, site suitability and approvals must be verified by qualified professionals.";

  modalContent.append(header, planTabs, planPreview, budgetBlock, downloads, warning, details);
  modal.classList.remove("hidden");
}

function openAdDetailsModal(option) {
  const property = option.property || {};
  const ad = property.full_ad || option.technical_data?.source_property || {};
  const caption = ad.description || property.description || ad.title || property.title || "No ad caption text was supplied in the dataset.";
  const contactNumber = extractContactNumber(caption) || extractContactNumber(JSON.stringify(ad)) || "Not mentioned in ad";
  modalContent.innerHTML = "";

  const title = document.createElement("h2");
  title.textContent = "Ad details";

  const header = document.createElement("div");
  header.className = "modal-summary";
  [
    ["Listing ID", property.listing_id || ad.listing_id],
    ["Location", [property.location || ad.location, property.district || ad.district].filter(Boolean).join(", ")],
    ["Listing type", ad.listing_type || "sale"],
    ["Property type", ad.property_type || "land"],
    ["Land size", formatPerches(property.land_size_perches || ad.land_size_perches)],
    ["Price", formatMoney(property.land_price_lkr || ad.sale_total_price_lkr || ad.price_lkr)],
    ["Contact number", contactNumber],
    ["Verified", ad.is_verified === undefined ? null : ad.is_verified ? "Yes" : "No"],
    ["Match score", property.agent2_score === undefined ? null : `${Math.round(Number(property.agent2_score) * 100)}%`],
  ]
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .forEach(([label, value]) => header.appendChild(summaryItem(label, value)));

  const address = document.createElement("p");
  address.className = "muted";
  address.textContent = [ad.address, ad.geo_region, ad.posted_date].filter(Boolean).join(" - ");

  const features = document.createElement("div");
  features.className = "ad-section";
  const featureTitle = document.createElement("h3");
  featureTitle.textContent = "Ad features";
  const featureList = document.createElement("ul");
  (property.features || []).forEach((feature) => {
    const item = document.createElement("li");
    item.textContent = feature;
    featureList.appendChild(item);
  });
  if (!featureList.children.length) {
    const item = document.createElement("li");
    item.textContent = "No feature text supplied in the dataset.";
    featureList.appendChild(item);
  }
  features.append(featureTitle, featureList);

  const captionPanel = document.createElement("div");
  captionPanel.className = "caption-panel";
  const captionTitle = document.createElement("h3");
  captionTitle.textContent = "Seller ad caption";
  const captionText = document.createElement("p");
  captionText.textContent = caption;
  captionPanel.append(captionTitle, captionText);

  const textBox = document.createElement("textarea");
  textBox.className = "ad-textbox";
  textBox.readOnly = true;
  textBox.value = formatAdText(property, ad);

  const fullAdPanel = document.createElement("div");
  fullAdPanel.className = "full-ad-panel";
  const fullAdTitle = document.createElement("h3");
  fullAdTitle.textContent = "Full ad record";
  fullAdPanel.append(fullAdTitle, textBox);

  modalContent.append(title, header, address, captionPanel, features, fullAdPanel);
  modal.classList.remove("hidden");
}

async function openBudgetSummaryModal(option) {
  const planning = option.planning || {};
  const budget = option.budget || {};
  modalContent.innerHTML = "";

  const title = document.createElement("h2");
  title.textContent = "Budget summary";

  const topActions = document.createElement("div");
  topActions.className = "modal-actions";
  topActions.appendChild(fileDownloadButton("Download Excel", planning.budget_excel_url));
  topActions.appendChild(fileDownloadButton("Download CSV", planning.budget_csv_url));
  topActions.appendChild(downloadLink("Open full budget report", planning.budget_doc_url));

  const summary = document.createElement("div");
  summary.className = "modal-summary";
  [
    ["Land price", formatCompactMoney(budget.land_price_lkr)],
    ["Construction expected", formatCompactMoney(budget.construction_expected_lkr)],
    ["Expected total", formatCompactMoney(budget.total_expected_lkr)],
    ["Budget status", friendlyStatus(budget.budget_status)],
  ].forEach(([label, value]) => summary.appendChild(summaryItem(label, value)));

  const itemCount = document.createElement("p");
  itemCount.className = "muted";
  itemCount.textContent = "Loading budget item costs...";

  const table = document.createElement("table");
  table.className = "budget-table";
  table.innerHTML = "<thead><tr><th>Item</th><th>Unit</th><th>Qty basis</th><th>Rate</th><th>Approx. cost</th></tr></thead><tbody></tbody>";

  modalContent.append(title, topActions, summary, itemCount, table);
  modal.classList.remove("hidden");

  try {
    const csvText = await fetchTextFile(planning.budget_csv_url);
    const items = extractMarketBudgetItems(csvText);
    itemCount.textContent = `${items.length} budget items loaded from the generated CSV sheet.`;
    const body = table.querySelector("tbody");
    body.innerHTML = "";
    items.forEach((item) => {
      const row = document.createElement("tr");
      [item.name, item.unit, item.quantity, formatMoneyValue(item.rate), formatMoneyValue(item.cost)].forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = value || "Not provided";
        row.appendChild(cell);
      });
      body.appendChild(row);
    });
  } catch (error) {
    itemCount.textContent = "Budget CSV is not available yet. Open the full budget report or generate this option again.";
  }
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

function fileDownloadButton(label, path) {
  const button = actionButton(label, () => downloadFile(path));
  if (!firstPlanUrl(path)) {
    button.disabled = true;
    button.setAttribute("aria-disabled", "true");
  }
  return button;
}

function openPlanFile(path) {
  const url = firstPlanUrl(path);
  if (!url) {
    showError("Budget file is not available for this option.");
    return;
  }
  window.open(url, "_blank", "noreferrer");
}

async function downloadFile(path) {
  const url = firstPlanUrl(path);
  if (!url) return;
  const response = await fetch(url);
  if (!response.ok) {
    showError(`Unable to download ${fileNameFromPath(path)}.`);
    return;
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = fileNameFromPath(path);
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

async function fetchTextFile(path) {
  const url = firstPlanUrl(path);
  if (!url) throw new Error("Missing file URL");
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Unable to load ${fileNameFromPath(path)}`);
  return response.text();
}

function extractMarketBudgetItems(csvText) {
  const rows = csvText.split(/\r?\n/).map(parseCsvLine).filter((row) => row.length);
  const headerIndex = rows.findIndex((row) => row[0] === "market_item");
  if (headerIndex === -1) return [];
  return rows.slice(headerIndex + 1).filter((row) => row[0]).map((row) => ({
    name: row[0],
    unit: row[1],
    quantity: row[2] || "Reference only",
    rate: row[3],
    cost: row[4],
  }));
}

function parseCsvLine(line) {
  const values = [];
  let current = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];
    if (char === '"' && quoted && next === '"') {
      current += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      values.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  values.push(current);
  return values;
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

function firstWarning(option) {
  const warnings = option?.warnings || option?.technical_data?.warnings || [];
  return Array.isArray(warnings) && warnings.length ? warnings[0] : "";
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

function fileNameFromPath(path) {
  if (!path) return "propwise-file";
  const normalized = String(path).replaceAll("\\", "/");
  return normalized.split("/").pop() || "propwise-file";
}

function formatAdText(property, ad) {
  const caption = ad.description || property.description || ad.title || property.title || "";
  const details = {
    title: ad.title || property.title,
    caption,
    listing_id: property.listing_id || ad.listing_id,
    location: property.location || ad.location,
    district: property.district || ad.district,
    address: ad.address,
    listing_type: ad.listing_type || "sale",
    property_type: ad.property_type || "land",
    land_size_perches: property.land_size_perches || ad.land_size_perches,
    price_lkr: property.land_price_lkr || ad.sale_total_price_lkr || ad.price_lkr,
    contact_number: extractContactNumber(caption) || extractContactNumber(JSON.stringify(ad)) || "Not mentioned in ad",
    verified: ad.is_verified === undefined ? null : ad.is_verified,
    posted_date: ad.posted_date,
    features: property.features || [],
  };
  return JSON.stringify(details, null, 2);
}

function extractContactNumber(text) {
  if (!text) return "";
  const match = String(text).match(/(?:\+94|0)?(?:\s|-|\.)?(?:7\d)(?:\s|-|\.)?\d{3}(?:\s|-|\.)?\d{4}/);
  return match ? match[0].replace(/\s+/g, " ").trim() : "";
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

function formatMoneyValue(value) {
  if (value === null || value === undefined || value === "") return "Reference only";
  const number = Number(value);
  if (Number.isNaN(number)) return String(value);
  return `Rs. ${number.toLocaleString("en-LK", { maximumFractionDigits: 0 })}`;
}

function formatPerches(value) {
  if (value === null || value === undefined) return "Not provided";
  return `${Number(value).toLocaleString("en-LK")} perches`;
}

function formatCompactMoney(value) {
  if (value === null || value === undefined) return "Not provided";
  const number = Number(value);
  if (Math.abs(number) >= 1_000_000) return `Rs. ${(number / 1_000_000).toFixed(1)}M`;
  return `Rs. ${number.toLocaleString("en-LK")}`;
}
