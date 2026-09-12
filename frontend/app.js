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
  submitButton.textContent = isLoading ? "Parsing..." : "Parse requirements";
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

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = button.dataset.example;
    queryInput.focus();
  });
});

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

  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/requirements/parse`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    showResult(await response.json());
  } catch (error) {
    showError(error instanceof Error ? error.message : "Unable to reach the backend.");
  } finally {
    setLoading(false);
  }
});
