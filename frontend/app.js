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
  submitButton.textContent = isLoading ? "Detecting..." : "Send";
}

function showError(errorMessage) {
  intentTitle.textContent = "Unable to parse";
  confidence.classList.add("hidden");
  fieldGrid.classList.add("hidden");
  jsonBlock.classList.add("hidden");
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
  document.getElementById("properties-panel").classList.add("hidden");

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

    // Call Agent 2
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

    const searchResult = await searchResponse.json();
    showProperties(searchResult);
    message.classList.add("hidden");

  } catch (error) {
    showError(error instanceof Error ? error.message : "Unable to reach the backend.");
  } finally {
    setLoading(false);
  }
});

function showProperties(result) {
  const panel = document.getElementById("properties-panel");
  const list = document.getElementById("property-list");
  const count = document.getElementById("property-count");
  const analysisDiv = document.getElementById("market-analysis");

  panel.classList.remove("hidden");
  count.textContent = `${result.returned} of ${result.total_found} results`;

  if (result.warnings && result.warnings.length > 0) {
    analysisDiv.innerHTML = `<strong>⚠️ Note:</strong> ${result.warnings.join(" ")}`;
    analysisDiv.classList.remove("hidden");
  } else {
    analysisDiv.classList.add("hidden");
  }

  list.innerHTML = "";

  if (result.results.length === 0) {
    list.innerHTML = `<p class="empty-text">No properties found matching these requirements.</p>`;
    return;
  }

  result.results.forEach((p) => {
    const card = document.createElement("div");
    card.className = "property-card";

    let priceText = "Price on request";
    if (p.listing_type === "sale" && p.sale_total_price_lkr) {
      priceText = `LKR ${p.sale_total_price_lkr.toLocaleString()}`;
    } else if (p.listing_type === "rent" && p.rent_monthly_lkr) {
      priceText = `LKR ${p.rent_monthly_lkr.toLocaleString()} / month`;
    }

    card.innerHTML = `
      <h3>${p.title}</h3>
      <div class="property-meta">
        <span>📍 ${p.location || "Unknown"} ${p.district ? `(${p.district})` : ""}</span>
        <span>🛏️ ${p.bedrooms || 0} Beds</span>
        <span class="property-score">⭐ Score: ${p.score.toFixed(2)}</span>
      </div>
      <div class="property-price">${priceText}</div>
    `;
    list.appendChild(card);
  });
}
