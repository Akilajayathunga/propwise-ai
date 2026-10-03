(() => {
  "use strict";

  const panel = () => document.querySelector("#recommendation-panel");

  function node(tag, text, className) {
    const item = document.createElement(tag);
    if (text != null) item.textContent = String(text);
    if (className) item.className = className;
    return item;
  }

  function cleanText(value) {
    return String(value || "")
      .replace(/Agent [1-4]/gi, "the search")
      .replace(/upstream/gi, "earlier")
      .replace(/retrieval/gi, "search");
  }

  function friendlyType(value) {
    return String(value || "property").replaceAll("_", " ");
  }

  function budgetStatus(status) {
    return {
      WITHIN_BUDGET: "Within budget",
      POTENTIALLY_FEASIBLE: "Potentially within budget",
      TIGHT_BUDGET: "Budget is tight",
      ABOVE_BUDGET: "Over budget",
    }[status] || "";
  }

  function optionDetails(item, raw, option, explanation, index, alternative, featured = false) {
    const property = raw || option?.property?.full_ad || option?.property || {};
    const card = node("article", null, "pick-card");
    const main = featured ? node("div", null, "pick-main") : card;
    const side = featured ? node("div", null, "pick-aside") : card;
    const top = node("div", null, "pick-topline");
    top.appendChild(node("span", alternative ? "Another option" : index === 0 ? "Top pick" : `Pick ${index + 1}`, "pick-label"));
    if (item.eligibility !== "ELIGIBLE") {
      const status = item.eligibility === "CONDITIONAL" ? "Needs review" : "Outside your criteria";
      top.appendChild(node("span", status, "pick-condition"));
    }
    main.appendChild(top);

    const planImage = firstPlanUrl(option?.planning?.png_url || option?.planning?.svg_url);
    if (planImage) {
      const media = node("button", null, "pick-plan-preview");
      media.type = "button";
      media.setAttribute("aria-label", `View plan for ${item.title || "this property"}`);
      const image = node("img");
      image.src = planImage;
      image.alt = "Conceptual floor plan";
      image.loading = "lazy";
      media.appendChild(image);
      media.addEventListener("click", () => openOptionModal(option));
      main.appendChild(media);
    }

    main.appendChild(node("h3", item.title || property.title || "Property"));
    const location = [property.location, property.district].filter(Boolean).join(", ");
    const meta = [location, friendlyType(property.property_type), property.listing_type === "rent" ? "For rent" : "For sale"].filter(Boolean).join("  /  ");
    main.appendChild(node("p", meta, "pick-meta"));

    const facts = [
      property.bedrooms != null ? `${property.bedrooms} beds` : null,
      property.bathrooms != null ? `${property.bathrooms} baths` : null,
      property.land_size_perches != null ? `${property.land_size_perches} perches` : null,
      property.house_size_sqft != null ? `${property.house_size_sqft} sqft` : null,
      property.is_verified ? "Verified listing" : null,
    ].filter(Boolean);
    if (facts.length) {
      const factList = node("div", null, "pick-facts");
      facts.forEach(value => factList.appendChild(node("span", value)));
      main.appendChild(factList);
    }

    const expectedProject = item.budget?.total_project?.expected_lkr;
    const amount = item.budget?.basis === "TOTAL_PROJECT" && expectedProject != null
      ? expectedProject
      : item.budget?.price_lkr ?? property.rent_monthly_lkr ?? property.sale_total_price_lkr ?? property.land_price_lkr;
    if (amount != null) {
      const label = item.budget?.basis === "TOTAL_PROJECT" ? "Estimated project total"
        : property.listing_type === "rent" ? "Monthly rent" : "Asking price";
      const price = node("div", null, "pick-price");
      const money = formatMoney(amount);
      const value = node("strong");
      if (money.startsWith("LKR ")) {
        value.append(node("small", "LKR"), node("span", money.slice(4), "amount"));
      } else {
        value.textContent = money;
      }
      price.append(node("span", label), value);
      side.appendChild(price);
    }

    const fit = budgetStatus(item.budget?.status);
    if (fit) side.appendChild(node("span", fit, `budget-pill ${String(item.budget.status).toLowerCase().replaceAll("_", "-")}`));

    const reason = explanation?.reason || "";
    if (reason && !/score|retriev|upstream|agent/i.test(reason)) main.appendChild(node("p", cleanText(reason), "pick-reason"));

    const strengths = (explanation?.strengths?.length ? explanation.strengths : item.strengths || [])
      .filter(value => !/score|retriev|upstream|agent|expected cost fits|listing type is|property type is|location matches/i.test(value))
      .slice(0, 3);
    if (strengths.length) {
      const list = node("ul", null, "pick-highlights");
      strengths.forEach(value => list.appendChild(node("li", cleanText(value))));
      main.appendChild(list);
    }

    const considerations = [...new Set([
      ...(item.trade_offs || []),
      ...(item.unmet_requirements || []),
      ...(item.uncertainty || []),
      ...(item.warnings || []),
    ].filter(Boolean).map(cleanText))];
    if (considerations.length) {
      const details = node("details", null, "pick-details");
      details.appendChild(node("summary", "What to consider"));
      const list = node("ul");
      considerations.forEach(value => list.appendChild(node("li", value)));
      details.appendChild(list);
      main.appendChild(details);
    }

    const actions = node("div", null, "pick-actions");
    if (raw || option) {
      const source = option || {
        property: {
          ...raw,
          features: Array.isArray(raw.features) ? raw.features : String(raw.features || "").split(",").map(value => value.trim()).filter(Boolean),
          full_ad: raw,
        },
      };
      actions.appendChild(actionButton("View listing", () => openAdDetailsModal(source)));
    }
    if (option) {
      actions.appendChild(actionButton("View plan", () => openOptionModal(option)));
      actions.appendChild(actionButton("View budget", () => openBudgetSummaryModal(option)));
    }
    side.appendChild(actions);
    if (featured) card.append(main, side);
    return card;
  }

  function noteList(parent, heading, values) {
    const unique = [...new Set((values || []).filter(Boolean).map(cleanText))];
    if (!unique.length) return;
    const details = node("details", null, "results-notes");
    details.appendChild(node("summary", heading));
    const list = node("ul");
    unique.forEach(value => list.appendChild(node("li", value)));
    details.appendChild(list);
    parent.appendChild(details);
  }

  function ownedLandOverview(parent, response) {
    const owned = response.owned_land_assessment;
    if (!owned) return;
    const section = node("div", null, "owned-overview");
    const status = budgetStatus(owned.budget?.status);
    if (status) section.appendChild(node("span", status, `build-status ${String(owned.budget.status).toLowerCase().replaceAll("_", "-")}`));
    const details = node("div", null, "owned-facts");
    const facts = [
      ["Estimated construction", owned.budget?.construction?.expected_lkr != null ? formatMoney(owned.budget.construction.expected_lkr) : null],
      ["Construction budget", owned.budget?.budget_lkr != null ? formatMoney(owned.budget.budget_lkr) : null],
      ["Expected margin", owned.budget?.expected_margin_lkr != null ? formatMoney(owned.budget.expected_margin_lkr) : null],
    ];
    facts.filter(([, value]) => value != null).forEach(([label, value]) => {
      const fact = node("div", null, "owned-fact");
      fact.append(node("span", label), node("strong", value));
      details.appendChild(fact);
    });
    section.appendChild(details);
    const budget = owned.budget?.budget_lkr;
    const expected = owned.budget?.construction?.expected_lkr;
    if (budget > 0 && expected != null) {
      const ratio = expected / budget;
      const comparison = node("div", null, "build-budget-meter");
      comparison.appendChild(node("div", "Estimated cost against your budget", "build-budget-label"));
      const track = node("div", null, "build-budget-track");
      const fill = node("span", null, ratio > 1 ? "over-budget" : "");
      fill.style.width = `${Math.min(ratio * 100, 100)}%`;
      track.appendChild(fill);
      comparison.append(track, node("p", `${Math.round(ratio * 100)}% of your budget`, "build-budget-caption"));
      section.appendChild(comparison);
    }
    noteList(section, "Things to confirm", [
      ...(owned.unmet_requirements || []),
      ...(owned.uncertainty || []),
      ...(owned.limitations || []),
    ]);
    const files = response.presentation?.owned_plan?.files;
    if (files) {
      const actions = node("div", null, "pick-actions");
      actions.appendChild(fileDownloadButton("Download all floors", files.zip));
      actions.appendChild(fileDownloadButton("Download DXF", files.dxf));
      section.appendChild(actions);
    }
    parent.appendChild(section);
  }

  function comparisonSummary(parent, response) {
    const comparisons = (response.comparisons || []).filter(value => value.expected_cost_difference_lkr != null);
    if (!comparisons.length) return;
    const names = new Map([...(response.recommendations || []), ...(response.alternatives || [])]
      .map(value => [value.listing_id, value.title]));
    const details = node("details", null, "results-notes comparison-list");
    details.appendChild(node("summary", "Compare costs"));
    const list = node("ul");
    comparisons.slice(0, 6).forEach(value => {
      const first = names.get(value.first_listing_id) || "First property";
      const second = names.get(value.second_listing_id) || "Second property";
      const gap = formatMoney(Math.abs(value.expected_cost_difference_lkr));
      list.appendChild(node("li", `${first} and ${second}: ${gap} estimated cost difference.`));
    });
    details.appendChild(list);
    parent.appendChild(details);
  }

  function render(response) {
    const root = panel();
    root.replaceChildren();
    root.classList.remove("hidden");

    const header = node("div", null, "result-header");
    const headings = {
      OK: "Places worth a closer look",
      NEEDS_CLARIFICATION: "A little more detail will help",
      NO_SUITABLE_OPTION: "No close matches yet",
      INSUFFICIENT_EVIDENCE: "We need a little more detail",
    };
    const heading = node("div");
    const ownedLand = Boolean(response.owned_land_assessment);
    heading.append(node("p", ownedLand ? "YOUR BUILD" : "CURATED FOR YOU", "eyebrow"),
      node("h2", ownedLand ? "Your build at a glance" : headings[response.status] || "Your options"));
    header.appendChild(heading);
    if (response.recommendations?.length) header.appendChild(node("span", `${response.recommendations.length} picks`, "result-count"));
    root.appendChild(header);

    const explanation = response.explanation;
    if (explanation?.summary && !/score|retriev|upstream|agent/i.test(explanation.summary)) {
      root.appendChild(node("p", cleanText(explanation.summary), "results-intro"));
    }
    if (response.coverage?.retrieval_truncated || response.coverage?.planning_coverage_limited) {
      root.appendChild(node("p", "These picks are based on the listings reviewed so far. More options may be available.", "results-context"));
    }
    noteList(root, "Good to know", [...(response.warnings || []), ...(response.clarification_questions || [])]);

    const properties = new Map((response.presentation?.properties || []).map(value => [value.listing_id, value]));
    const options = new Map((response.presentation?.land_house_options || []).map(value => [value.property?.listing_id, value]));
    const explanations = new Map((explanation?.properties || []).map(value => [value.listing_id, value]));

    if (response.recommendations?.length) {
      const cards = node("div", null, "pick-grid");
      const featureLayout = response.recommendations.length === 3 && !response.presentation?.land_house_options?.length;
      if (featureLayout) cards.dataset.layout = "feature";
      response.recommendations.forEach((item, index) => {
        cards.appendChild(optionDetails(item, properties.get(item.listing_id), options.get(item.listing_id), explanations.get(item.listing_id), index, false, featureLayout && index === 0));
      });
      root.appendChild(cards);
    }

    ownedLandOverview(root, response);
    comparisonSummary(root, response);

    if (response.alternatives?.length) {
      const details = node("details", null, "alternative-list");
      details.appendChild(node("summary", `Other options to consider (${response.alternatives.length})`));
      const cards = node("div", null, "pick-grid");
      response.alternatives.forEach((item, index) => {
        cards.appendChild(optionDetails(item, properties.get(item.listing_id), options.get(item.listing_id), explanations.get(item.listing_id), index, true));
      });
      details.appendChild(cards);
      root.appendChild(details);
    }

    if (!response.recommendations?.length && !response.owned_land_assessment) {
      root.appendChild(node("p", "Try a broader area or budget to see more options.", "empty-text"));
    }
  }

  window.Agent4UI = {
    render,
    reset() {
      panel().replaceChildren();
      panel().classList.add("hidden");
    },
  };
})();
