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

const fields = [
  ["Intent", "intent"],
  ["Location", "location"],
  ["District", "district"],
  ["Property type", "property_type"],
  ["Listing type", "listing_type"],
  ["Max budget LKR", "maximum_budget_lkr"],
  ["Total project budget LKR", "total_project_budget_lkr"],
  ["Construction budget LKR", "construction_budget_lkr"],
  ["Bedrooms", "bedrooms"],
  ["Bathrooms", "bathrooms"],
  ["Land size perches", "land_size_perches"],
  ["Floors", "floors"],
  ["Parking spaces", "parking_spaces"],
  ["Office required", "office_required"],
  ["Balcony required", "balcony_required"],
  ["Missing information", "missing_information"],
];

function formatValue(value) {
  if (value === null || value === undefined) return "Not provided";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "None";
  if (typeof value === "number") return value.toLocaleString("en-LK");
  return String(value);
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Working..." : "Send";
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
}

function showResult(result) {
  intentTitle.textContent = result.intent || "UNKNOWN";
  confidence.textContent = `${Math.round((result.confidence || 0) * 100)}%`;
  confidence.classList.remove("hidden");
  message.classList.add("hidden");

  fieldGrid.innerHTML = "";
  fields.forEach(([label, key]) => {
    const item = document.createElement("div");
    item.className = "field-item";

    const title = document.createElement("span");
    title.textContent = label;

    const value = document.createElement("strong");
    value.textContent = formatValue(result[key]);

    item.append(title, value);
    fieldGrid.appendChild(item);
  });

  jsonOutput.textContent = JSON.stringify(result, null, 2);
  fieldGrid.classList.remove("hidden");
  jsonBlock.classList.remove("hidden");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();

  if (!query) {
    showError("Please enter a property request.");
    return;
  }

  setLoading(true);
  message.className = "empty-text";
  message.textContent = "Parsing your request...";
  message.classList.remove("hidden");
  propertiesPanel.classList.add("hidden");
  planningPanel.classList.add("hidden");

  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/requirements/parse`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error(`Agent 1 request failed with status ${response.status}`);
    }

    const requirements = await response.json();
    showResult(requirements);

    let searchResult = null;
    if (shouldSearchProperties(requirements.intent)) {
      message.className = "empty-text";
      message.textContent = "Searching properties...";
      message.classList.remove("hidden");

      const searchResponse = await fetch(`${apiBaseUrl}/api/v1/property-search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ requirements: requirements, top_n: 10 }),
      });

      if (!searchResponse.ok) {
        throw new Error(`Agent 2 request failed with status ${searchResponse.status}`);
      }

      searchResult = await searchResponse.json();
      showProperties(searchResult);
    }

    if (shouldGeneratePlan(requirements.intent)) {
      message.className = "empty-text";
      message.textContent = "Generating conceptual plan...";
      message.classList.remove("hidden");

      const planningRequest = buildPlanningRequest(requirements, searchResult);
      const planningResponse = await fetch(`${apiBaseUrl}/api/v1/planning/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(planningRequest),
      });

      if (!planningResponse.ok) {
        throw new Error(`Agent 3 request failed with status ${planningResponse.status}`);
      }

      showPlanning(await planningResponse.json());
    }

    message.classList.add("hidden");

  } catch (error) {
    showError(error instanceof Error ? error.message : "Unable to reach the backend.");
  } finally {
    setLoading(false);
  }
});

function shouldSearchProperties(intent) {
  return ["BUY_PROPERTY", "RENT_PROPERTY", "BUY_LAND", "LAND_AND_HOUSE", "COMPARE_PROPERTIES"].includes(intent);
}

function shouldGeneratePlan(intent) {
  return ["PLAN_HOUSE", "LAND_AND_HOUSE"].includes(intent);
}

function buildPlanningRequest(requirements, searchResult) {
  const selectedProperty =
    requirements.intent === "LAND_AND_HOUSE" && searchResult && searchResult.results.length > 0
      ? searchResult.results[0]
      : null;

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

function showProperties(result) {
  const list = document.getElementById("property-list");
  const count = document.getElementById("property-count");
  const analysisDiv = document.getElementById("market-analysis");

  propertiesPanel.classList.remove("hidden");
  count.textContent = `${result.returned} of ${result.total_found} results`;

  const priceStats = result.analysis && result.analysis.price_stats ? result.analysis.price_stats : {};
  const analysisParts = [
    `Median: ${formatMoney(priceStats.median_price)}`,
    `Min: ${formatMoney(priceStats.min_price)}`,
    `Max: ${formatMoney(priceStats.max_price)}`,
    `Budget fit: ${formatValue(result.analysis ? result.analysis.budget_fit_pct : null)}%`,
    `Dataset size: ${formatValue(result.metadata ? result.metadata.dataset_size : null)}`,
  ];

  if (result.warnings && result.warnings.length > 0) {
    analysisParts.push(`Note: ${result.warnings.join(" ")}`);
  }
  analysisDiv.textContent = analysisParts.join(" | ");
  analysisDiv.classList.remove("hidden");

  list.innerHTML = "";

  if (result.results.length === 0) {
    list.innerHTML = `<p class="empty-text">No properties found matching these requirements.</p>`;
    return;
  }

  result.results.forEach((p) => {
    const card = document.createElement("div");
    card.className = "property-card";

    const title = document.createElement("h3");
    title.textContent = p.title || p.listing_id || "Property";

    const meta = document.createElement("div");
    meta.className = "property-meta";
    [
      `${p.location || "Unknown"} ${p.district ? `(${p.district})` : ""}`,
      `${formatValue(p.property_type)} / ${formatValue(p.listing_type)}`,
      `${formatValue(p.bedrooms)} beds`,
      `${formatValue(p.bathrooms)} baths`,
      `${formatValue(p.land_size_perches)} perches`,
      `Score ${Number(p.score || 0).toFixed(2)}`,
    ].forEach((text) => {
      const span = document.createElement("span");
      span.textContent = text;
      meta.appendChild(span);
    });

    const price = document.createElement("div");
    price.className = "property-price";
    price.textContent =
      p.listing_type === "rent" ? `${formatMoney(p.rent_monthly_lkr)} / month` : formatMoney(p.sale_total_price_lkr || p.price_lkr);

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

  const roomSummary = summarizeRooms(result.plan && result.plan.rooms ? result.plan.rooms : []);
  const budgetFields = [
    ["Plan ID", result.plan_id],
    ["Constraints", result.constraints_satisfied ? "Satisfied" : "Not satisfied"],
    ["Exact site fit", result.exact_site_fit_verified ? "Verified" : "Conceptual only"],
    ["Bedrooms", roomSummary.bedrooms],
    ["Bathrooms", roomSummary.bathrooms],
    ["Floors", result.plan && result.plan.floors ? result.plan.floors.length : null],
    ["Parking", result.plan && result.plan.parking ? result.plan.parking.spaces : null],
    ["Floor area", result.estimated_floor_area_sqft ? `${formatValue(result.estimated_floor_area_sqft)} sqft` : null],
    ["Space efficiency", result.plan && result.plan.space_metrics ? `${formatValue(result.plan.space_metrics.space_efficiency_score)}%` : null],
    ["Remaining construction budget", formatMoney(result.remaining_construction_budget_lkr)],
    ["Budget status", result.budget_status],
    ["Cost estimate available", result.budget_estimation_available ? "Yes" : "No"],
    ["Selected land price", result.selected_property ? formatMoney(result.selected_property.land_price_lkr) : null],
  ];

  budgetGrid.innerHTML = "";
  budgetFields.forEach(([label, value]) => {
    const item = document.createElement("div");
    item.className = "field-item";
    const title = document.createElement("span");
    title.textContent = label;
    const strong = document.createElement("strong");
    strong.textContent = formatValue(value);
    item.append(title, strong);
    budgetGrid.appendChild(item);
  });

  if (result.warnings && result.warnings.length) {
    warnings.textContent = result.warnings.join(" ");
    warnings.classList.remove("hidden");
  } else {
    warnings.classList.add("hidden");
  }

  preview.innerHTML = "";
  floorTabs.innerHTML = "";
  const svgFiles = result.files && result.files.svg ? result.files.svg : [];
  const svgUrls = svgFiles.map((path) => firstPlanUrl(path)).filter(Boolean);
  if (svgUrls.length) {
    const image = document.createElement("img");
    image.alt = "Generated conceptual floor plan";
    preview.appendChild(image);

    svgUrls.forEach((url, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = index === 0 ? "floor-tab active" : "floor-tab";
      button.textContent = index === 0 ? "Ground Floor" : `Floor ${index + 1}`;
      button.addEventListener("click", () => {
        document.querySelectorAll(".floor-tab").forEach((tab) => tab.classList.remove("active"));
        button.classList.add("active");
        image.src = url;
      });
      floorTabs.appendChild(button);
    });
    image.src = svgUrls[0];
  }

  const links = document.createElement("div");
  links.className = "file-links";
  [
    ["Plan JSON", result.files ? result.files.json : null],
    ["DXF", result.files ? result.files.dxf : null],
    ["PNG", result.files && result.files.png ? result.files.png[0] : null],
    ["SVG", result.files && result.files.svg ? result.files.svg[0] : null],
  ].forEach(([label, path]) => {
    const url = firstPlanUrl(path);
    if (!url) return;
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = label;
    links.appendChild(link);
  });
  preview.appendChild(links);
  jsonOutput.textContent = JSON.stringify(result, null, 2);
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

function firstPlanUrl(path) {
  if (!path) return "";
  const normalized = String(path).replaceAll("\\", "/");
  const marker = "storage/plans/";
  const index = normalized.indexOf(marker);
  if (index === -1) return "";
  return `${apiBaseUrl}/plans/${normalized.slice(index + marker.length)}`;
}

function formatMoney(value) {
  if (value === null || value === undefined) return "Not provided";
  return `LKR ${Number(value).toLocaleString("en-LK")}`;
}
