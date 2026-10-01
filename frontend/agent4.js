/* Agent 4 display only. All decisions and provider calls belong to the server. */
(() => {
  "use strict";
  const panel = () => document.querySelector("#recommendation-panel");
  const label = (value) => String(value ?? "Unknown").replaceAll("_", " ").toLowerCase();
  const el = (tag, text, className = "") => {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  };
  function list(parent, heading, values) {
    if (!Array.isArray(values) || !values.length) return;
    parent.appendChild(el("h4", heading));
    const ul = el("ul");
    values.forEach(value => ul.appendChild(el("li", value)));
    parent.appendChild(ul);
  }
  function details(parent, heading, values) {
    if (!Array.isArray(values) || !values.length) return;
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
    list(parent, "Planning assumptions", value.assumptions);
    list(parent, "Planning warnings", value.warnings);
    parent.appendChild(el("p", value.disclaimer || "Conceptual planning only. Construction estimates are preliminary, not quotations. Professional site and design review is required.", "plan-notice"));
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
    card.appendChild(el("p", `Listing ${item.listing_id} ? ${label(item.eligibility)}`, "muted"));
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
    details(card, "Warnings", item.warnings);
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
    root.appendChild(el("p", "Agent 4 ? Recommendation & Decision Support", "eyebrow"));
    root.appendChild(el("h2", label(response.status)));
    const sources = { LLM: "Grounded AI explanation", DETERMINISTIC_FALLBACK: "Deterministic fallback", DETERMINISTIC: "Deterministic only" };
    root.appendChild(el("p", `Explanation source: ${sources[response.explanation_status] || "Unknown"}`, "muted"));
    const evidence = response.presentation || {};
    const coverage = response.coverage || {};
    grid(root, [
      ["Retrieved / total matching", `${coverage.retrieved_count ?? 0} / ${coverage.total_matching_candidates ?? "Unknown"}`],
      ["Planning-assessed candidates", coverage.planning_assessed_count ?? 0],
      ["Eligible or conditional candidates ranked", coverage.ranked_count ?? 0],
      ["Coverage limits", [coverage.retrieval_truncated ? "Retrieval truncated" : null,
        coverage.planning_coverage_limited ? "Some retrieved candidates lack planning evidence" : null].filter(Boolean).join("; ") || "No truncation reported"],
    ]);
    root.appendChild(el("p", coverage.scope, "plan-notice"));
    if (evidence.retrieval?.relaxed_filters) root.appendChild(el("p", "Retrieval filters were relaxed. Agent 4 checked the original requirements.", "plan-notice"));
    list(root, "Warnings", response.warnings);
    list(root, "Retrieval warnings", evidence.retrieval?.warnings);
    list(root, "Details needed", response.clarification_questions);
    const explanation = response.explanation;
    if (explanation) {
      root.appendChild(el("h3", "Recommendation explanation"));
      root.appendChild(el("p", explanation.summary));
      if (explanation.top_recommendation_reason) root.appendChild(el("p", explanation.top_recommendation_reason));
      list(root, "Comparison explanation", explanation.comparison_summary);
      details(root, "Explanation warnings and limitations", explanation.warnings);
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
      alternatives.appendChild(el("summary", `Other evaluated candidates (${response.alternatives.length}) ? may violate requirements or lack evidence`));
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
      list(root, "Limitations", owned.limitations);
      list(root, "Suggested next steps", owned.next_steps);
      const files = evidence.owned_plan?.files;
      if (files) {
        const links = el("div", null, "file-links");
        [["All plans ZIP", files.zip], ["DXF", files.dxf], ["Plan JSON", files.json], ["Plan summary", files.summary]].forEach(([name, path]) => links.appendChild(fileDownloadButton(name, path)));
        root.appendChild(links);
      }
    }
    list(root, "Deterministic comparisons", (response.comparisons || []).map(c =>
      `${c.first_listing_id} versus ${c.second_listing_id}: score difference ${Number(c.score_difference).toFixed(2)}; expected cost difference ${formatMoney(c.expected_cost_difference_lkr)} (${label(c.budget_basis)}).`));
  }
  window.Agent4UI = { render, reset: () => { panel().replaceChildren(); panel().classList.add("hidden"); } };
})();
