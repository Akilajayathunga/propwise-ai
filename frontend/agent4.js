(() => {
  "use strict";

  const panel = () => document.querySelector("#recommendation-panel");

  function node(tag, text, className) {
    const item = document.createElement(tag);
    if (text != null) item.textContent = String(text);
    if (className) item.className = className;
    return item;
  }

  let listingNames = new Map();
  function cleanText(value) {
    let text = String(value || "");
    for (const [id, title] of listingNames) text = text.replaceAll(id, title);
    // Technical numeric prose stays in the API; money below uses structured fields.
    if (/\b\d+(?:\.\d+)?e[+-]\d+\b/i.test(text)) return "";
    return text
      .replace(/\b[A-Z]+(?:_[A-Z]+)+\b/g, value => value.toLowerCase().replaceAll("_", " "))
      .replace(/\b(listing_type|property_type)\b/g, value => value.replaceAll("_", " "))
      .replace(/Agent 1/gi, "requirement parsing")
      .replace(/Agent 2/gi, "the search")
      .replace(/Agent 3/gi, "planning")
      .replace(/Agent 4/gi, "the assessment")
      .replace(/upstream/gi, "earlier")
      .replace(/retrieval/gi, "search")
      .replace(/\.{2,}(?=\s|$)/g, ".");
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

  const eligibilityLabel = value => ({
    ELIGIBLE: "Meets assessed criteria", CONDITIONAL: "Needs review",
    HARD_CONSTRAINT_VIOLATION: "Outside your criteria", INSUFFICIENT_EVIDENCE: "Not enough evidence",
  }[value] || "Not assessed");
  const displayEnum = value => String(value ?? "Unknown").toLowerCase().replaceAll("_", " ");
  const sentenceCase = value => value.charAt(0).toUpperCase() + value.slice(1);
  const budgetBasis = value => ({ SALE_TOTAL: "Purchase price", MONTHLY_RENT: "Monthly rent",
    TOTAL_PROJECT: "Total project", CONSTRUCTION: "Construction" }[value] || "Unknown");

  function constraintText(check) {
    const label = check.requirement || "Requirement";
    if (check.status === "SATISFIED") return `Satisfied: ${label}`;
    if (check.status === "VIOLATED") {
      if (/^Generated layout satisfies (?:Agent 3|planning) constraints$/i.test(label)) return "The conceptual layout does not satisfy the planning constraints.";
      const location = /^location matches (.+)$/i.exec(label);
      if (location) return `Does not match the requested location: ${location[1]}`;
      return `Not satisfied: ${label}`;
    }
    if (label === "Site dimensions and fit are evidenced") return "Exact site dimensions are not confirmed";
    return `Not confirmed: ${label}`;
  }

  function requirementText(item, value) {
    const check = (item.constraint_checks || []).find(check => check.requirement === value);
    return cleanText(check ? constraintText(check) : value);
  }

  function concise(value) {
    const text = cleanText(value);
    const sentences = text.split(/(?<=[.!?])\s+/);
    const short = sentences.slice(0, 2).join(" ").trim();
    return short.length <= 600 ? short : "";
  }

  // Conservative sentence-level display deduplication, never response mutation.
  const proseKey = value => cleanText(value).replace(/^(?:recorded evidence|limitation|warning|satisfied):\s*/i, "")
    .toLowerCase().replace(/[.!?]+$/, "").trim();

  function onlyVisibleMetadata(key) {
    // Match complete metadata clauses, not sentences that add a reason or caveat.
    return key.split(/\s*(?:;|,|\band\b)\s*/).every(part =>
      /^(?:(?:deterministic|final|recorded|recommendation) )?(?:rank(?:ed)?|(?:decision[- ]support )?(?:index|score))\s*(?::|is|of|=|#)?\s*\d+(?:\.\d+)?(?:\s*(?:\/|out of)\s*100)?$/.test(part)
      || /^(?:(?:recorded |assessed |assessment )?(?:eligibility|status|budget status|budget assessment)\s*(?::|is)\s*|(?:the )?(?:supplied |deterministic )?assessment is\s+|(?:this|the) (?:option|property|recommendation) is\s+)?(?:conditional|eligible|needs review|outside your criteria|hard[- ]constraint violation|insufficient evidence|no suitable option|recommendations ready|within budget|above budget|potentially feasible|complete|ready|ok)$/.test(part)
    );
  }

  function usefulProse(value, visible = []) {
    const known = new Set(visible.map(proseKey));
    const text = concise(value);
    return text.split(/(?<=[.!?])\s+/).map(sentence => sentence.trim()).filter(sentence => {
      const key = proseKey(sentence);
      if (known.has(key)) return false;
      if (onlyVisibleMetadata(key)) return false;
      if (/^(?:based on|recommendation scope: based on|best among) (?:the )?evaluated (?:retrieved )?candidates(?: only|; not the entire property market)?$/.test(key)) return false;
      return true;
    }).map(sentence => sentence.replace(/^(?:Recorded evidence|Limitation):\s*/i, "")).join(" ");
  }

  function usefulComparison(value, comparisons) {
    const text = usefulProse(value);
    return text.split(/(?<=[.!?])\s+/).filter(sentence => {
      if (/^Recorded comparison\s*:/i.test(sentence)) return false;
      if (comparisons?.length && /^(?:The )?(?:first|second) option(?:'s expected (?:total project )?cost is approximately LKR [\d,.-]+ (?:higher|lower)| scores [\d.]+ points (?:higher|lower))\.?$/i.test(sentence)) return false;
      return true;
    }).join(" ");
  }

  function actionSteps(values) {
    return (values || []).map(concise).filter(text =>
      /^(?:please\s+|you (?:should|can)\s+)?(?:confirm|verify|obtain|compare|review|consult|check|request|arrange|ask|visit|measure|clarify|seek|contact)\b/i.test(text)
    ).slice(0, 3);
  }

  function mainStrength(item, value) {
    const check = (item.constraint_checks || []).find(check => check.requirement === value);
    if (check && check.status !== "SATISFIED") return requirementText(item, value);
    const text = cleanText(value).replace(/^Satisfied:\s*/i, "").replace(/^(bedrooms|bathrooms|floors) at least (.+)$/i, "At least $2 $1");
    return sentenceCase(text);
  }

  // Select warning concepts, not the first few candidate-prefixed strings.
  function importantNotes(items, warnings = []) {
    const allWarnings = [...warnings, ...items.flatMap(item => [
      ...(item.warnings || []), ...(item.uncertainty || []), ...(item.trade_offs || []),
      ...(item.planning?.warnings || []),
    ])].join(" ");
    const notes = [];
    const aboveBudget = items.some(item => item.budget?.status === "ABOVE_BUDGET");
    if (items.some(item => {
      const budget = item.budget || {};
      const high = (budget.total_project || budget.construction)?.high_lkr;
      return budget.budget_lkr != null && high != null && high > budget.budget_lkr;
    }) || /high (?:construction\/project cost |cost |estimate|scenario).*exceeds? (?:the original |the )?budget/i.test(allWarnings))
      notes.push(`${aboveBudget ? "Some evaluated costs already exceed your budget. " : ""}The high-cost scenario may exceed your budget.`);
    else if (aboveBudget) notes.push("Some evaluated costs exceed the original budget.");
    if (items.some(item => item.planning && item.planning.exact_site_fit_verified !== true) || /exact (?:plot |site )?(?:dimensions.*unavailable|site fit cannot be confirmed)/i.test(allWarnings))
      notes.push("Exact site dimensions are not confirmed; exact site fit cannot be confirmed.");
    if (/availability.*not.*verified|historical listing/i.test(allWarnings))
      notes.push("Listing availability and claims have not been independently verified.");
    if (items.some(item => item.planning || item.budget?.construction) || /preliminary|not a contractor quotation/i.test(allWarnings))
      notes.push("Construction estimates are preliminary, not quotations; conceptual plans are not professional approval.");
    if (/relaxed|broadened|strict constraints yielded no results/i.test(allWarnings))
      notes.push("The search was broadened; options were still assessed against your original requirements.");
    return notes.slice(0, 5);
  }

  function considerationsFor(item) {
    const failed = (item.constraint_checks || []).filter(check => check.status === "VIOLATED").map(constraintText);
    const failure = item.planning?.constraints_satisfied === false ? ["The conceptual layout does not satisfy the planning constraints."] : [];
    const notes = importantNotes([item]);
    const unknown = (item.constraint_checks || []).filter(check => check.status === "UNKNOWN").map(constraintText);
    return [...new Set([...failed, ...failure, ...notes, ...unknown].map(cleanText).filter(Boolean))].slice(0, 4);
  }

  function keyStrengths(item) {
    const priorities = [/location matches/i, /bedrooms/i, /district matches/i, /expected cost fits/i, /bathrooms|floors/i];
    const values = [...new Set(item.strengths || [])];
    const priority = value => { const index = priorities.findIndex(pattern => pattern.test(value)); return index < 0 ? priorities.length : index; };
    return values.sort((a, b) => priority(a) - priority(b)).map(value => mainStrength(item, value)).filter(Boolean).slice(0, 3);
  }

  function displayList(parent, heading, values) {
    const unique = [...new Set((values || []).filter(Boolean).map(cleanText).filter(Boolean))];
    if (!unique.length) return;
    parent.appendChild(node("h4", heading));
    const list = node("ul");
    unique.forEach(value => list.appendChild(node("li", value)));
    parent.appendChild(list);
  }

  function displayFacts(parent, pairs) {
    const list = node("dl", null, "decision-facts");
    pairs.filter(([, value]) => value != null).forEach(([label, value]) => {
      list.append(node("dt", label), node("dd", value));
    });
    parent.appendChild(list);
  }

  function decisionDetails(parent, item, explanation, alternative = false) {
    const details = node("details", null, "pick-details decision-support-details");
    details.appendChild(node("summary", alternative ? "Why not shortlisted?" : "Why this option?"));
    displayFacts(details, [
      ["Final rank", alternative ? null : item.rank],
      ["Decision-support score", (alternative && item.eligibility === "HARD_CONSTRAINT_VIOLATION") || item.final_recommendation_score == null ? null : `${item.final_recommendation_score.toFixed(1)} / 100`],
      ["Eligibility", eligibilityLabel(item.eligibility)],
    ]);
    if (alternative) displayList(details, "Unmet requirements", (item.constraint_checks || [])
      .filter(check => check.status === "VIOLATED").map(constraintText).slice(0, 2));
    if (!alternative) {
      if (item.criteria?.length) {
        details.appendChild(node("h4", "Score breakdown"));
        displayFacts(details, item.criteria.map(value => [sentenceCase(displayEnum(value.criterion)), `${(value.normalized_score * 100).toFixed(1)} / 100`]));
      }
      const budget = item.budget || {};
      const money = value => value == null ? "Unknown" : formatMoney(value);
      const project = budget.basis === "TOTAL_PROJECT";
      const construction = budget.basis === "CONSTRUCTION";
      details.appendChild(node("h4", "Budget"));
      displayFacts(details, [
        [project ? "Total budget" : construction ? "Construction budget" : budget.basis === "MONTHLY_RENT" ? "Monthly budget" : "User budget", money(budget.budget_lkr)],
        [project ? "Land price" : "Property price", construction ? null : money(budget.price_lkr)],
        ["Expected construction cost", project || construction ? money(budget.construction?.expected_lkr) : null],
        ["Expected project total", project ? money(budget.total_project?.expected_lkr) : null],
        ["Budget status", budgetStatus(budget.status) || "Unknown"],
        ["Expected remaining budget", budget.expected_margin_lkr == null ? null : money(budget.expected_margin_lkr)],
        [project ? "High project estimate" : "High construction estimate", project ? money(budget.total_project?.high_lkr) : construction ? money(budget.construction?.high_lkr) : null],
      ]);
      // Detailed exclusions and cost ranges remain in View budget / the API.
      const planning = item.planning;
      if (planning) {
        details.appendChild(node("h4", "Conceptual plan"));
        displayFacts(details, [
          ["Layout score", planning.layout_score == null ? "Unknown" : `${planning.layout_score} / 100`],
          ["Exact site fit", planning.exact_site_fit_verified === true ? "Evidenced in the conceptual assessment, not professional approval" : "Not confirmed"],
          ["Land area", planning.land_size_perches == null ? "Unknown" : `${planning.land_size_perches} perches`],
          ["Width", planning.width_ft == null ? null : `${planning.width_ft} ft`],
          ["Length", planning.length_ft == null ? null : `${planning.length_ft} ft`],
        ]);
      }
    }
    if (explanation) {
      const visible = [...keyStrengths(item), ...(item.strengths || []), ...considerationsFor(item),
        ...(item.trade_offs || []), ...(item.unmet_requirements || []), ...(item.uncertainty || [])];
      const additional = values => [...new Set((values || []).map(value => usefulProse(value, visible)).filter(Boolean))];
      const reason = usefulProse(explanation.reason, visible);
      if (reason) details.appendChild(node("p", reason));
      if (!alternative) {
        displayList(details, "Further strengths", additional(explanation.strengths).slice(0, 2));
        displayList(details, "Further trade-offs", additional(explanation.trade_offs).slice(0, 2));
      }
    }
    parent.appendChild(details);
  }

  function assessmentCoverage(parent, coverage) {
    if (!coverage) return;
    const details = node("details", null, "results-notes assessment-coverage");
    details.appendChild(node("summary", "Assessment coverage"));
    displayFacts(details, [
      ["Retrieved", `${coverage.retrieved_count ?? "Unknown"} of ${coverage.total_matching_candidates ?? "unknown"} matching`],
      ["Planning-assessed", coverage.planning_assessed_count],
      ["Ranked", coverage.ranked_count],
    ]);
    if (coverage.retrieval_truncated) details.appendChild(node("p", "Retrieval covered only part of the matching candidates."));
    if (coverage.planning_coverage_limited) details.appendChild(node("p", "Some retrieved candidates were not assessed by planning."));
    details.appendChild(node("p", "Based on the evaluated candidates only."));
    parent.appendChild(details);
  }

  function optionDetails(item, raw, option, explanation, index, alternative, featured = false) {
    const property = raw || option?.property?.full_ad || option?.property || {};
    const card = node("article", null, "pick-card");
    const main = featured ? node("div", null, "pick-main") : card;
    const side = featured ? node("div", null, "pick-aside") : card;
    const top = node("div", null, "pick-topline");
    top.appendChild(node("span", alternative ? "Another option" : item.rank === 1 ? "Top pick" : item.rank != null ? `Pick ${item.rank}` : "Recommended option", "pick-label"));
    top.appendChild(node("span", eligibilityLabel(item.eligibility), "pick-condition"));
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
      property.is_verified ? "Marked verified in source data" : null,
    ].filter(Boolean);
    if (facts.length) {
      const factList = node("div", null, "pick-facts");
      facts.forEach(value => factList.appendChild(node("span", value)));
      main.appendChild(factList);
    }

    if (property.is_verified) main.appendChild(node("p", "Not independently verified by PropWise.", "pick-meta"));

    const expectedProject = item.budget?.total_project?.expected_lkr;
    const amount = item.budget?.basis === "TOTAL_PROJECT" && expectedProject != null
      ? expectedProject
      : item.budget?.price_lkr ?? property.rent_monthly_lkr ?? property.sale_total_price_lkr ?? property.land_price_lkr;
    if (amount != null) {
      const label = item.budget?.basis === "TOTAL_PROJECT" ? (expectedProject != null ? "Estimated project total" : "Land price; project estimate unavailable")
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

    const strengths = keyStrengths(item);
    if (strengths.length) {
      const list = node("ul", null, "pick-highlights");
      strengths.forEach(value => list.appendChild(node("li", value)));
      main.appendChild(list);
    }

    const considerations = considerationsFor(item);
    if (considerations.length) {
      const details = node("details", null, "pick-details");
      details.appendChild(node("summary", "What to consider"));
      const list = node("ul");
      considerations.forEach(value => list.appendChild(node("li", value)));
      details.appendChild(list);
      main.appendChild(details);
    }

    decisionDetails(main, item, explanation, alternative);

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
    const unique = [...new Set((values || []).filter(Boolean).map(cleanText).filter(Boolean))];
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
    noteList(section, "Things to confirm", considerationsFor(owned));
    decisionDetails(section, owned);
    noteList(section, "Next steps", owned.next_steps);
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
    const comparisons = response.comparisons || [];
    if (!comparisons.length) return;
    const names = new Map([...(response.recommendations || []), ...(response.alternatives || [])]
      .map(value => [value.listing_id, value.title]));
    const details = node("details", null, "results-notes comparison-list");
    details.appendChild(node("summary", "Compare top options"));
    const list = node("ul");
    comparisons.forEach(value => {
      const first = names.get(value.first_listing_id) || "First property";
      const second = names.get(value.second_listing_id) || "Second property";
      const messages = [`${first} compared with ${second}.`];
      if (value.score_difference != null) {
        const difference = value.score_difference;
        messages.push(difference === 0 ? "The options have the same decision-support score." :
          `The first option scores ${Math.abs(difference).toFixed(2)} points ${difference > 0 ? "higher" : "lower"}.`);
      }
      if (value.expected_cost_difference_lkr != null) {
        const difference = value.expected_cost_difference_lkr;
        messages.push(difference === 0 ? "The options have the same expected cost." :
          `The first option's expected cost is approximately ${formatMoney(Math.abs(difference))} ${difference > 0 ? "higher" : "lower"}.`);
      }
      messages.push(`Budget basis: ${budgetBasis(value.budget_basis)}.`);
      list.appendChild(node("li", messages.join(" ")));
    });
    details.appendChild(list);
    parent.appendChild(details);
  }

  function render(response) {
    const root = panel();
    const candidates = [...(response.recommendations || []), ...(response.alternatives || [])];
    listingNames = new Map(candidates.map(item => [item.listing_id, item.title && item.title !== item.listing_id ? item.title : "this option"]));
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
    if (usefulProse(explanation?.summary)) {
      root.appendChild(node("p", usefulProse(explanation.summary), "results-intro"));
    }
    const source = response.explanation_status || explanation?.source;
    root.appendChild(node("p", ({
      DETERMINISTIC: "Deterministic assessment", LLM: "Grounded AI explanation",
      DETERMINISTIC_FALLBACK: "Deterministic fallback explanation",
    }[source] || "Explanation source not provided"), "results-context"));
    if (explanation) {
      if (explanation.top_recommendation_reason) noteList(root, "Top recommendation reason", [usefulProse(explanation.top_recommendation_reason, candidates.flatMap(item => [...keyStrengths(item), ...(item.trade_offs || [])]))]);
      noteList(root, "Comparison explanation", (explanation.comparison_summary || []).map(value => usefulComparison(value, response.comparisons)).filter(Boolean).slice(0, 2));
      noteList(root, "Next steps", actionSteps(explanation.next_steps));
    }
    assessmentCoverage(root, response.coverage);
    noteList(root, "Important notes", importantNotes(response.owned_land_assessment ? [response.owned_land_assessment] : candidates,
      [...(response.warnings || []), ...(explanation?.warnings || [])]));
    noteList(root, "More information needed", response.clarification_questions);

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
