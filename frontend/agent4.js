/* Agent 4 display only. All decisions and provider calls belong to the server. */
(() => {
  "use strict";
  const panel = () => document.querySelector("#recommendation-panel");
  const label = (value) => String(value ?? "Unknown").replaceAll("_", " ").toLowerCase();
  const fallbackNotice = "The search was broadened because no options satisfied all initial retrieval filters. Final options were still evaluated against your original requirements.";
  const planningDisclaimer = "Conceptual planning only. Construction estimates are preliminary, not quotations. Professional site and design review is required.";
  function displayText(value) {
    return String(value)
      .replace(/Strict constraints yielded no results\. Dropped bedroom constraints and expanded budget ceiling by 20% to find fallback properties\.|Agent 2 relaxed its filters; Agent 4 checks the original requirements\./gi, fallbackNotice)
      .replace(/Agent 1/gi, "requirement parsing")
      .replace(/Agent 2/gi, "property search")
      .replace(/Agent 3/gi, "conceptual planning")
      .replace(/Agent 4/gi, "recommendation assessment");
  }
  const unique = values => [...new Set((values || []).filter(Boolean).map(displayText))];
  const excluding = (values, shown) => unique(values).filter(value => !new Set(unique(shown)).has(value));
  function planningNotes(value) {
    if (!value) return { assumptions: [], limitations: [], all: [] };
    const isLimitation = text => /unavailable|cannot|not verified|not confirmed|does not represent|excluded|not included|preliminary|not construction|professional.*review/i.test(text);
    const assumptions = unique(value.assumptions).filter(text => !isLimitation(text));
    const disclaimer = displayText(value.disclaimer || planningDisclaimer);
    const limitations = excluding([
      ...unique(value.assumptions).filter(isLimitation), ...(value.warnings || []),
    ], [...assumptions, disclaimer]);
    return { assumptions, limitations, all: [...assumptions, ...limitations, disclaimer] };
  }
  const el = (tag, text, className = "") => {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = displayText(text);
    if (className) node.className = className;
    return node;
  };
  function list(parent, heading, values) {
    values = unique(values);
    if (!values.length) return;
    parent.appendChild(el("h4", heading));
    const ul = el("ul");
    values.forEach(value => ul.appendChild(el("li", value)));
    parent.appendChild(ul);
  }
  function details(parent, heading, values) {
    values = unique(values);
    if (!values.length) return;
    const block = el("details", null, "a4-details");
    block.appendChild(el("summary", heading));
    list(block, "", values);
    parent.appendChild(block);
  }
  function grid(parent, entries) {
    const node = el("div", null, "field-grid");
    entries.forEach(([key, value]) => node.appendChild(summaryItem(key, value)));
    parent.appendChild(node);
  }
  function range(value) {
    if (!value) return "Unknown";
    return `${formatMoney(value.low_lkr)} / ${formatMoney(value.expected_lkr)} / ${formatMoney(value.high_lkr)}`;
  }
  function budget(parent, value) {
    if (!value) return;
    grid(parent, [
      ["Budget assessment", label(value.status)],
      ["Price basis", label(value.basis)],
      ["Original budget", formatMoney(value.budget_lkr)],
      [value.basis === "MONTHLY_RENT" ? "Monthly rent" : "Property / land price", formatMoney(value.price_lkr)],
      ["Construction: low / expected / high", range(value.construction)],
      ["Project: low / expected / high", range(value.total_project)],
      ["Expected budget margin", formatMoney(value.expected_margin_lkr)],
    ]);
    if (!value.authoritative) parent.appendChild(el("p", "Affordability evidence is unavailable or unverified.", "plan-notice"));
    list(parent, "Excluded costs", value.not_included);
  }
  function planning(parent, value) {
    if (!value) return;
    grid(parent, [
      ["Generated layout", value.constraints_satisfied === true ? "Passed conceptual checks" : value.constraints_satisfied === false ? "Failed conceptual checks" : "Unknown"],
      ["Layout quality", value.layout_score == null ? "Unknown" : `${Number(value.layout_score).toFixed(1)} / 100`],
      ["Site fit", value.exact_site_fit_verified === true ? "Upstream conceptual fit flag; review dimensions and limitations" : "Not verified"],
      ["Site width / length", `${formatValue(value.width_ft)} / ${formatValue(value.length_ft)} ft`],
    ]);
    const notes = planningNotes(value);
    list(parent, "Planning assumptions", notes.assumptions);
    list(parent, "Planning limitations", notes.limitations);
    parent.appendChild(el("p", value.disclaimer || planningDisclaimer, "plan-notice"));
  }
  function criteria(parent, values) {
    const block = el("details", null, "a4-details");
    block.appendChild(el("summary", "Why this decision-support score?"));
    const table = el("table", null, "budget-table");
    const header = el("tr");
    ["Criterion", "Weight", "Contribution", "Evidence"].forEach(text => header.appendChild(el("th", text)));
    table.appendChild(header);
    (values || []).forEach(value => {
      const row = el("tr");
      [label(value.criterion), `${(value.weight * 100).toFixed(1)}%`,
        Number(value.contribution).toFixed(2), label(value.evidence_status)].forEach(text => row.appendChild(el("td", text)));
      table.appendChild(row);
      block.appendChild(el("p", `${label(value.criterion)}: ${value.explanation}`, "muted"));
    });
    block.insertBefore(table, block.children[1] || null);
    parent.appendChild(block);
  }
  function adOption(raw) {
    const features = Array.isArray(raw.features) ? raw.features : String(raw.features || "").split(",").map(x => x.trim()).filter(Boolean);
    return { property: { ...raw, features, agent2_score: raw.score, full_ad: raw } };
  }
  function recommendationCard(item, raw, option, explanation, recommended) {
    const card = el("article", null, "a4-card");
    card.appendChild(el("p", recommended ? `Final rank ${item.rank}` : "Alternative / outside shortlist", "eyebrow"));
    card.appendChild(el("h3", item.title || item.listing_id));
    card.appendChild(el("p", `Listing ${item.listing_id} — ${label(item.eligibility)}`, "muted"));
    card.appendChild(el("p", `Decision-support score: ${Number(item.final_recommendation_score).toFixed(1)} / 100`, "a4-score"));
    if (explanation) {
      card.appendChild(el("p", explanation.reason));
      list(card, "Explanation strengths", explanation.strengths);
      list(card, "Explanation trade-offs", explanation.trade_offs);
    }
    budget(card, item.budget);
    list(card, "Strengths", item.strengths);
    list(card, "Trade-offs", item.trade_offs);
    list(card, "Unmet requirements", item.unmet_requirements);
    list(card, "Uncertainty", item.uncertainty);
    details(card, "Warnings", excluding(item.warnings, planningNotes(item.planning).all));
    planning(card, item.planning);
    criteria(card, item.criteria);
    const actions = el("div", null, "option-actions");
    if (raw) actions.appendChild(actionButton("View property details", () => openAdDetailsModal(adOption(raw))));
    if (option) {
      actions.appendChild(actionButton("View conceptual plan", () => openOptionModal(option)));
      actions.appendChild(actionButton("View budget report", () => openBudgetSummaryModal(option)));
      const preview = firstPlanUrl(option.planning?.png_url || option.planning?.svg_url);
      if (preview) {
        const image = el("img", null, "a4-preview");
        image.src = preview;
        image.alt = "Conceptual floor plan; not construction-ready";
        image.loading = "lazy";
        card.appendChild(image);
      }
    }
    card.appendChild(actions);
    details(card, "Upstream evidence (not the final ranking)", [
      `Retrieval relevance: ${item.upstream_retrieval_relevance_score} / 1`,
      `Upstream combination index: ${item.upstream_combination_score ?? "Not applicable"}`,
    ]);
    return card;
  }
  function render(response) {
    const root = panel();
    root.replaceChildren();
    root.classList.remove("hidden");
    root.appendChild(el("p", "RECOMMENDATION & DECISION SUPPORT", "eyebrow"));
    const statusHeadings = {
      OK: "Recommendations ready",
      NEEDS_CLARIFICATION: "More information needed",
      NO_SUITABLE_OPTION: "No suitable option",
      INSUFFICIENT_EVIDENCE: "Insufficient evidence",
    };
    root.appendChild(el("h2", statusHeadings[response.status] || "Recommendation result"));
    const sources = { LLM: "Grounded AI explanation", DETERMINISTIC_FALLBACK: "Deterministic fallback", DETERMINISTIC: "Deterministic only" };
    root.appendChild(el("p", `Explanation source: ${sources[response.explanation_status] || "Unknown"}`, "muted"));
    const evidence = response.presentation || {};
    const coverage = response.coverage || {};
    const coverageLimits = [
      coverage.retrieval_truncated === true ? "Retrieval covered only part of the matching candidates" : null,
      coverage.planning_coverage_limited === true ? "Some retrieved candidates were not assessed by planning" : null,
    ].filter(Boolean);
    grid(root, [
      ["Retrieved / total matching", `${coverage.retrieved_count ?? 0} / ${coverage.total_matching_candidates ?? "Unknown"}`],
      ["Planning-assessed candidates", coverage.planning_assessed_count ?? 0],
      ["Eligible or conditional candidates ranked", coverage.ranked_count ?? 0],
      ...(coverageLimits.length ? [["Coverage limits", coverageLimits.join("; ")]] : []),
    ]);
    const scopeNote = coverage.scope === "Best among the evaluated retrieved candidates; not the entire property market."
      ? "Recommendation scope: based on the evaluated retrieved candidates only."
      : coverage.scope;
    root.appendChild(el("p", scopeNote, "muted"));
    const displayedItems = [...(response.recommendations || []), ...(response.alternatives || [])];
    const displayedPlanning = [...displayedItems.map(item => item.planning), response.owned_land_assessment?.planning];
    const planningText = displayedPlanning.flatMap(value => planningNotes(value).all);
    const generalWarnings = excluding([
      ...(response.warnings || []),
      ...(evidence.retrieval?.relaxed_filters === true ? [fallbackNotice] : []),
    ], planningText);
    list(root, "Warnings", generalWarnings);
    list(root, "Details needed", response.clarification_questions);
    const explanation = response.explanation;
    if (explanation) {
      root.appendChild(el("h3", "Recommendation explanation"));
      root.appendChild(el("p", explanation.summary));
      if (explanation.top_recommendation_reason) root.appendChild(el("p", explanation.top_recommendation_reason));
      list(root, "Comparison explanation", explanation.comparison_summary);
      details(root, "Explanation warnings and limitations", excluding(explanation.warnings, [...planningText, ...generalWarnings]));
      list(root, "Alternative considerations", explanation.alternatives);
      list(root, "Next steps", explanation.next_steps);
      root.appendChild(el("p", explanation.explanation_scope, "muted"));
    }
    const raw = new Map((evidence.properties || []).map(p => [p.listing_id, p]));
    const options = new Map((evidence.land_house_options || []).map(o => [o.property.listing_id, o]));
    const explanations = new Map((explanation?.properties || []).map(p => [p.listing_id, p]));
    if (response.recommendations?.length) {
      const cards = el("div", null, "a4-cards");
      response.recommendations.forEach(item => cards.appendChild(recommendationCard(item, raw.get(item.listing_id), options.get(item.listing_id), explanations.get(item.listing_id), true)));
      root.appendChild(cards);
    } else if (!response.owned_land_assessment) {
      root.appendChild(el("p", "No final property shortlist is available. Review the status, warnings and alternatives.", "empty-text"));
    }
    if (response.alternatives?.length) {
      const alternatives = el("details", null, "a4-details");
      alternatives.appendChild(el("summary", `Other evaluated candidates (${response.alternatives.length}) — may violate requirements or lack evidence`));
      const cards = el("div", null, "a4-cards");
      response.alternatives.forEach(item => cards.appendChild(recommendationCard(item, raw.get(item.listing_id), options.get(item.listing_id), explanations.get(item.listing_id), false)));
      alternatives.appendChild(cards);
      root.appendChild(alternatives);
    }
    const owned = response.owned_land_assessment;
    if (owned) {
      root.appendChild(el("h3", "Owned-land assessment"));
      root.appendChild(el("p", `Assessment: ${label(owned.eligibility)}. No property ranking was performed.`));
      budget(root, owned.budget);
      planning(root, owned.planning);
      list(root, "Unmet requirements", owned.unmet_requirements);
      list(root, "Uncertainty", owned.uncertainty);
      list(root, "Limitations", excluding(owned.limitations, [...planningNotes(owned.planning).all, ...generalWarnings]));
      list(root, "Suggested next steps", owned.next_steps);
      const files = evidence.owned_plan?.files;
      if (files) {
        const links = el("div", null, "file-links");
        [["All plans ZIP", files.zip], ["DXF", files.dxf], ["Plan JSON", files.json], ["Plan summary", files.summary]].forEach(([name, path]) => links.appendChild(fileDownloadButton(name, path)));
        root.appendChild(links);
      }
    }
    const titles = new Map((evidence.properties || []).map(item => [item.listing_id, item.title || item.listing_id]));
    displayedItems.forEach(item => { if (item.title) titles.set(item.listing_id, item.title); });
    list(root, "Compare top options", (response.comparisons || []).map(c => {
      const score = Number(c.score_difference);
      const scoreText = score === 0 ? "Both options have the same decision-support score."
        : `The first option scores ${Number(Math.abs(score).toFixed(2))} points ${score > 0 ? "higher" : "lower"}.`;
      const cost = c.expected_cost_difference_lkr;
      const costLabel = c.budget_basis === "TOTAL_PROJECT" ? "expected total project cost"
        : c.budget_basis === "MONTHLY_RENT" ? "monthly rent" : "expected cost";
      const costText = cost == null ? "Comparable cost evidence is unavailable."
        : cost === 0 ? `Both options have the same ${costLabel}.`
        : `The first option's ${costLabel} is approximately ${formatMoney(Math.abs(cost))} ${cost > 0 ? "higher" : "lower"}.`;
      return `${titles.get(c.first_listing_id) || c.first_listing_id} versus ${titles.get(c.second_listing_id) || c.second_listing_id}: ${scoreText} ${costText}`;
    }));
  }
  window.Agent4UI = { render, reset: () => { panel().replaceChildren(); panel().classList.add("hidden"); } };
})();
