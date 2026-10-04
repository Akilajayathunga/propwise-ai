/* Offline, dependency-free smoke checks. Run: node frontend/tests/agent4-smoke.js
 * runAgent4Smoke(sources, fixtures) also supports the existing V8 tool runner.
 * No HTTP requests or provider calls are made; fetch and the DOM are mocked.
 */
async function runAgent4Smoke(sources, suppliedFixtures) {
  let assertions = 0;
  function assert(condition, message) {
    assertions += 1;
    if (!condition) throw new Error(message);
  }
  const clone = value => JSON.parse(JSON.stringify(value));
  class Element {
    constructor(tag) {
      this.tagName = tag; this.children = []; this._text = ""; this.className = "";
      this.style = {}; this.dataset = {}; this.events = {}; this.attributes = {};
      this.value = ""; this.checked = false;
      this.classList = {
        contains: name => this.className.split(/\s+/).includes(name),
        add: name => { if (!this.classList.contains(name)) this.className += ` ${name}`; },
        remove: name => { this.className = this.className.split(/\s+/).filter(x => x !== name).join(" "); },
        toggle: (name, state) => (state ?? !this.classList.contains(name)) ? this.classList.add(name) : this.classList.remove(name),
      };
    }
    set textContent(value) { this._text = String(value); this.children = []; }
    get textContent() { return [this._text, ...this.children.map(x => x.textContent)].filter(Boolean).join(" "); }
    set innerHTML(value) {
      if (value !== "") throw new Error("Dynamic HTML must not be rendered");
      this.replaceChildren();
    }
    appendChild(child) { this.children.push(child); return child; }
    append(...children) { children.forEach(child => this.appendChild(child)); }
    replaceChildren(...children) { this._text = ""; this.children = children; }
    setAttribute(key, value) { this.attributes[key] = value; }
    addEventListener(name, handler) { this.events[name] = handler; }
    focus() {}
    scrollIntoView() {}
  }
  function walk(element) { return [element, ...element.children.flatMap(walk)]; }
  const byClass = (element, name) => walk(element).filter(x => x.classList.contains(name));
  const nodes = new Map();
  const document = {
    createElement: tag => new Element(tag), body: new Element("body"),
    addEventListener() {}, activeElement: null,
    querySelector(selector) {
      if (selector.startsWith("meta[")) return null;
      if (!nodes.has(selector)) nodes.set(selector, new Element("div"));
      return nodes.get(selector);
    },
  };
  const window = { location: { hostname: "localhost", origin: "http://localhost" }, matchMedia: () => ({ matches: true }) };
  const calls = [];
  let response, retrieval;
  const fetch = async (url, options) => {
    calls.push({ url, body: JSON.parse(options.body) });
    if (url.endsWith("/api/v1/recommendation")) return { ok: true, json: async () => clone(response) };
    if (url.endsWith("/api/v1/property-search")) return { ok: true, json: async () => clone(retrieval) };
    throw new Error("Unexpected mock request");
  };
  new Function(sources["app.js"]);
  new Function(sources["agent4.js"]);
  const app = new Function("window", "document", "fetch", sources["app.js"] + "\n" + sources["agent4.js"] +
    "\nreturn {continueWithRequirements, showProperties, openAdDetailsModal};")(window, document, fetch);
  const panel = document.querySelector("#recommendation-panel");
  const item = (id, rank = null) => ({
    listing_id: id, title: id, rank, final_recommendation_score: 83.67,
    eligibility: "HARD_CONSTRAINT_VIOLATION", criteria: [], constraint_checks: [],
    strengths: [], trade_offs: [], unmet_requirements: [], uncertainty: [], warnings: [],
    budget: { basis: "SALE_TOTAL", price_lkr: 9000000, budget_lkr: 30000000, status: "WITHIN_BUDGET", authoritative: true, not_included: [] },
  });
  const kandyItem = item("house-for-sale-menikhinna-for-sale-kandy-2");
  Object.assign(kandyItem, { title: "House For Sale - Menikhinna", trade_offs: ["location matches Kandy"],
    unmet_requirements: ["location matches Kandy"], strengths: ["district matches Kandy"],
    constraint_checks: [
      { requirement: "location matches Kandy", status: "VIOLATED", evidence: "Listing location is Kundasale" },
      { requirement: "district matches Kandy", status: "SATISFIED", evidence: "Listing district is Kandy" },
    ], warnings: ["Listing availability and claims have not been independently verified."] });
  const siteWarning = "Land area is available, but exact plot dimensions are unavailable. The generated layout is conceptual and exact site fit cannot be confirmed.";
  const landItems = [1, 2].map(rank => ({ ...item(`land-${rank}`, rank), title: `Kottawa land ${rank}`, eligibility: "CONDITIONAL",
    final_recommendation_score: rank === 1 ? 85.1063 : 84.5691,
    constraint_checks: [{ requirement: "Site dimensions and fit are evidenced", status: "UNKNOWN", evidence: "Exact dimensions unavailable" }],
    uncertainty: ["Site dimensions and fit are evidenced"], warnings: [siteWarning],
    budget: { basis: "TOTAL_PROJECT", budget_lkr: 40000000, price_lkr: 9500000, status: "POTENTIALLY_FEASIBLE", authoritative: true,
      construction: { low_lkr: 24000000, expected_lkr: 28455730, high_lkr: 34000000 },
      total_project: { low_lkr: 33500000, expected_lkr: 37955730 + (rank - 1) * 1500000, high_lkr: 43500000 },
      expected_margin_lkr: 2044270, not_included: ["Professional fees are not included."] },
    planning: { exact_site_fit_verified: false, constraints_satisfied: true, layout_score: 85, assumptions: ["1 parking space assumed for conceptual planning."], warnings: [siteWarning], disclaimer: "Conceptual planning is not professional approval." },
  }));
  const fixtures = suppliedFixtures || {
    kandy: { status: "NO_SUITABLE_OPTION", recommendations: [], alternatives: [kandyItem], explanation_status: "DETERMINISTIC",
      coverage: { retrieved_count: 1, total_matching_candidates: 1, planning_assessed_count: 0, ranked_count: 0, scope: "Evaluated candidates only." },
      presentation: { properties: [{ listing_id: kandyItem.listing_id, location: "Kundasale", district: "Kandy", property_type: "house", is_verified: false }] } },
    kottawa: { status: "OK", recommendations: landItems, alternatives: Array.from({ length: 6 }, (_, n) => item(`alternative-${n}`)),
      explanation_status: "DETERMINISTIC", coverage: { retrieved_count: 8, total_matching_candidates: 106, planning_assessed_count: 8, ranked_count: 2, retrieval_truncated: true, planning_coverage_limited: false, scope: "Evaluated candidates only." },
      comparisons: [{ first_listing_id: "land-1", second_listing_id: "land-2", score_difference: 0.5372, expected_cost_difference_lkr: -1500000, budget_basis: "TOTAL_PROJECT" }],
      presentation: { properties: landItems.map(x => ({ listing_id: x.listing_id, is_verified: true, property_type: "land" })) } },
  };
  const original = JSON.stringify(fixtures);
  window.Agent4UI.render(fixtures.kandy);
  assert(panel.textContent.includes("No close matches yet"), "Kandy no-suitable-option heading");
  assert(panel.textContent.includes("Menikhinna"), "Kandy alternative identity");
  assert(panel.textContent.includes("Outside your criteria"), "Hard constraint label");
  assert(panel.textContent.includes("Does not match the requested location: Kandy"), "Violated location wording");
  assert(!panel.textContent.includes("location matches Kandy"), "No naked violated label");
  assert(panel.textContent.includes("District matches Kandy"), "Satisfied district remains positive");
  assert(!panel.textContent.includes("Final rank"), "No fabricated alternative rank");
  assert(panel.textContent.includes("Deterministic assessment"), "Deterministic source visible");
  window.Agent4UI.render(fixtures.kottawa);
  assert(byClass(panel, "pick-card").length === 8, "All two recommendations and six alternatives retained");
  assert(panel.textContent.includes("85.1 / 100") && panel.textContent.includes("84.6 / 100"), "Actual scores visible");
  assert(panel.textContent.includes("Final rank 1") && panel.textContent.includes("Final rank 2"), "Actual ranks visible");
  assert(panel.textContent.includes("8 of 106 matching") && panel.textContent.includes("Planning-assessed 8") && panel.textContent.includes("Ranked 2"), "Coverage counts");
  assert(panel.textContent.includes("Retrieval covered only part") && !panel.textContent.includes("Some retrieved candidates were not assessed"), "Retrieval limit distinguished from planning limit");
  assert(panel.textContent.includes("Exact site dimensions are not confirmed"), "Unknown site fit");
  assert(!panel.textContent.includes("Site dimensions and fit are evidenced"), "No affirmative unknown site-fit label");
  assert(panel.textContent.includes("exact site fit cannot be confirmed"), "Detailed planning warning retained");
  for (const label of ["Total budget", "Land price", "Expected construction cost", "Expected project total", "High project estimate", "Expected remaining budget", "Layout score", "Exact site fit"])
    assert(panel.textContent.includes(label), `Essential evidence available: ${label}`);
  assert(panel.textContent.includes("Why this option?") && !panel.textContent.includes("Decision support details"), "Compact section renamed");
  assert(!panel.textContent.includes("Planning assumptions") && !panel.textContent.includes("contribution"), "Verbose diagnostics omitted");
  const cards = byClass(panel, "pick-card");
  const altDetails = byClass(cards[2], "decision-support-details")[0];
  assert(!altDetails.textContent.includes("Score breakdown") && !altDetails.textContent.includes("High project estimate"), "Alternatives have lighter details");
  assert(byClass(panel, "pick-highlights").every(list => list.children.length <= 3), "At most three strengths");
  assert(byClass(panel, "pick-details").filter(detail => detail.children[0].textContent === "What to consider").every(detail => detail.children[1].children.length <= 4), "At most four considerations");
  assert(panel.textContent.includes("Marked verified in source data") && panel.textContent.includes("Not independently verified by PropWise"), "Source verification qualified");
  assert(!panel.textContent.includes("Verified listing"), "No misleading verification badge");
  assert(panel.textContent.includes("LKR 1,500,000 lower") && panel.textContent.includes("0.54 points higher") && panel.textContent.includes("Budget basis: Total project"), "Comparison direction, score, basis");
  const reverse = clone(fixtures.kottawa);
  reverse.recommendations.reverse();
  window.Agent4UI.render(reverse);
  assert(byClass(panel, "pick-label")[0].textContent === "Pick 2", "Card label follows rank, not array index");
  const planningLimited = clone(fixtures.kottawa);
  planningLimited.coverage.retrieval_truncated = false;
  planningLimited.coverage.planning_coverage_limited = true;
  window.Agent4UI.render(planningLimited);
  assert(panel.textContent.includes("Some retrieved candidates were not assessed") && !panel.textContent.includes("Retrieval covered only part"), "Planning limitation distinct");
  const ten = clone(fixtures.kottawa);
  ten.recommendations = Array.from({ length: 10 }, (_, n) => ({ ...clone(ten.recommendations[0]), listing_id: `pick-${n}`, rank: n + 1 }));
  ten.alternatives = [];
  window.Agent4UI.render(ten);
  assert(byClass(panel, "pick-card").length === 10 && panel.textContent.includes("Final rank 10"), "Deterministic cards not restricted to explanation subset");
  const budgetComparisons = clone(fixtures.kottawa);
  budgetComparisons.comparisons[0].expected_cost_difference_lkr = 1500000;
  budgetComparisons.comparisons[0].score_difference = -0.5;
  window.Agent4UI.render(budgetComparisons);
  assert(panel.textContent.includes("LKR 1,500,000 higher") && panel.textContent.includes("0.50 points lower"), "Opposite comparison directions");
  budgetComparisons.comparisons[0].expected_cost_difference_lkr = null;
  window.Agent4UI.render(budgetComparisons);
  assert(panel.textContent.includes("0.50 points lower"), "Score-only comparison retained");
  const owned = { status: "OK", recommendations: [], alternatives: [], explanation_status: "DETERMINISTIC",
    owned_land_assessment: { eligibility: "CONDITIONAL", budget: { basis: "CONSTRUCTION", budget_lkr: 40000000, status: "UNKNOWN", not_included: [] },
      planning: { constraints_satisfied: false, exact_site_fit_verified: false, warnings: ["Conceptual plan did not satisfy constraints."], assumptions: [] },
      constraint_checks: [], unmet_requirements: [], uncertainty: ["Exact site fit is not confirmed"], limitations: [], next_steps: ["Confirm site dimensions"] } };
  window.Agent4UI.render(owned);
  assert(!panel.textContent.includes("Final rank") && !panel.textContent.includes("Decision-support score"), "Owned land stays an unranked assessment");
  assert(panel.textContent.includes("The conceptual layout does not satisfy the planning constraints.") && panel.textContent.includes("Exact site fit Not confirmed"), "Planning failure and uncertainty preserved");
  const unknown = clone(fixtures.kandy);
  unknown.alternatives[0].eligibility = "INSUFFICIENT_EVIDENCE";
  window.Agent4UI.render(unknown);
  assert(panel.textContent.includes("Not enough evidence"), "Insufficient evidence distinct from violation");
  const injected = '<img src=x onerror="alert(1)"> score retrieval upstream agent';
  const explained = clone(fixtures.kandy);
  explained.explanation_status = "LLM";
  explained.explanation = { source: "LLM", summary: injected, top_recommendation_reason: "A grounded score reason",
    properties: [{ listing_id: explained.alternatives[0].listing_id, reason: injected, strengths: ["Explanation strength"], trade_offs: ["Explanation trade-off"] }],
    comparison_summary: ["Comparison evidence"], warnings: ["Explanation warning"], alternatives: ["Alternative explanation"], next_steps: ["Verify listing availability."], explanation_scope: "Bounded explanation scope" };
  window.Agent4UI.render(explained);
  for (const value of [injected.replace("retrieval", "search").replace("upstream", "earlier"), "Grounded AI explanation", "A grounded score reason", "Comparison evidence", "Verify listing availability."])
    assert(panel.textContent.includes(value), "Explanation content preserved as text");
  assert(!walk(panel).some(x => x.tagName === "img"), "Injection-like explanation did not create markup");
  const polished = clone(fixtures.kottawa);
  const first = polished.recommendations[0];
  first.criteria = ["budget", "location", "planning", "evidence_quality"].map(criterion => ({ criterion, normalized_score: 0.9 }));
  first.strengths = ["location matches Kottawa", "bedrooms at least 3", "district matches Colombo", "Expected cost fits original budget", "Land price alone fits total project budget"];
  first.trade_offs = ["Affordability depends on the cost scenario."];
  polished.explanation_status = "LLM";
  polished.explanation = { source: "LLM", summary: "The supplied assessment is recommendations ready.",
    top_recommendation_reason: "Recorded eligibility: conditional.",
    comparison_summary: ["Recorded comparison: LKR -1,500,000.", "The first option scores 0.54 points higher. The first option\'s expected cost is approximately LKR 1,500,000 lower."],
    next_steps: ["Limitation: High construction/project cost scenario exceeds the original budget..", "Warning: Missing dimensions.", "Costs may exceed budget.", "Confirm missing site dimensions.."],
    properties: [{ listing_id: first.listing_id, reason: "Recorded eligibility: conditional.",
      strengths: ["Recorded evidence: Expected cost fits original budget.", "Recorded evidence: Land price alone fits total project budget."],
      trade_offs: ["Limitation: Affordability depends on the cost scenario..."] }] };
  const originalPolished = JSON.stringify(polished);
  window.Agent4UI.render(polished);
  assert(!panel.textContent.includes("Top recommendation reason") && !panel.textContent.includes("Recorded eligibility"), "Generic top reason and property eligibility omitted");
  assert(!panel.textContent.includes("Comparison explanation") && !panel.textContent.includes("Recorded comparison"), "Raw and duplicate AI comparison omitted");
  assert(panel.textContent.includes("Compare top options"), "Deterministic comparison retained");
  assert(!panel.textContent.includes("The supplied assessment is"), "Generic status summary suppressed");
  assert(!panel.textContent.includes("Further strengths") && !panel.textContent.includes("Further trade-offs"), "Recorded duplicate property evidence omitted");
  const steps = byClass(panel, "results-notes").find(detail => detail.children[0].textContent === "Next steps");
  assert(steps.textContent === "Next steps Confirm missing site dimensions.", "Only genuine action next steps retained");
  assert(!panel.textContent.includes(".."), "Terminal double punctuation normalized");
  assert(byClass(panel, "pick-highlights").every(list => !list.textContent.includes("Satisfied:")), "Main strengths have no redundant satisfied prefix");
  assert(panel.textContent.includes("Location matches Kottawa") && panel.textContent.includes("At least 3 bedrooms") && panel.textContent.includes("District matches Colombo"), "Main strengths natural wording");
  const detail = byClass(panel, "decision-support-details")[0];
  for (const label of ["Budget", "Location", "Planning", "Evidence quality"])
    assert(walk(detail).some(element => element.tagName === "dt" && element.textContent === label), "Capitalized score label");
  polished.explanation.top_recommendation_reason = "Recorded eligibility: conditional. The additional site review should focus on the boundary measurements.";
  polished.explanation.summary = "The shortlist includes options with different site-review needs.";
  polished.explanation.properties[0].reason = "A boundary survey would help resolve the missing site dimensions.";
  polished.explanation.next_steps = ["Limitation: Missing dimensions."];
  window.Agent4UI.render(polished);
  assert(panel.textContent.includes("The additional site review should focus on the boundary measurements.") && panel.textContent.includes("different site-review needs") && panel.textContent.includes("A boundary survey would help"), "Useful nonduplicate prose survives, including mixed generic/useful sentences");
  assert(!byClass(panel, "results-notes").some(detail => detail.children[0].textContent === "Next steps"), "Empty action section omitted");
  for (const reason of ["This option is conditional.", "Eligibility is conditional.", "The deterministic assessment is complete."]) {
    polished.explanation.top_recommendation_reason = reason;
    window.Agent4UI.render(polished);
    assert(!panel.textContent.includes("Top recommendation reason"), "Equivalent state-only prose suppressed");
  }
  const fallback = clone(fixtures.kottawa);
  fallback.recommendations[0].final_recommendation_score = 88.91;
  fallback.explanation_status = "DETERMINISTIC_FALLBACK";
  fallback.explanation = { source: "DETERMINISTIC_FALLBACK", properties: [] };
  for (const reason of [
    "Deterministic rank 1; decision-support index 88.91.", "Rank 1; score 88.91.",
    "Final rank: 1.", "Decision-support score: 88.91 / 100.",
    "Rank 1 and score 88.91.", "Rank 1; eligibility: conditional; budget status: within budget.",
  ]) {
    fallback.explanation.top_recommendation_reason = reason;
    const before = JSON.stringify(fallback);
    window.Agent4UI.render(fallback);
    assert(!panel.textContent.includes(reason) && !panel.textContent.includes("Top recommendation reason"), "Metadata-only fallback reason omitted with its heading");
    assert(panel.textContent.includes("Final rank 1") && panel.textContent.includes("88.9 / 100"), "Actual recommendation rank and score retained");
    assert(panel.textContent.includes("Deterministic fallback explanation"), "Fallback source remains visible");
    assert(panel.textContent.includes("Compare top options") && panel.textContent.includes("Assessment coverage") && panel.textContent.includes("Needs review"), "Comparison, coverage and eligibility preserved");
    assert(JSON.stringify(fallback) === before, "Fallback API object unchanged");
  }
  const usefulReason = "The expected project cost is within budget, but the high-cost scenario exceeds the budget and exact site fit is not confirmed.";
  for (const reason of [usefulReason, `Rank 1; score 88.91; ${usefulReason}`, `Deterministic rank 1; decision-support index 88.91. ${usefulReason}`]) {
    fallback.explanation.top_recommendation_reason = reason;
    const before = JSON.stringify(fallback);
    window.Agent4UI.render(fallback);
    assert(panel.textContent.includes("Top recommendation reason") && panel.textContent.includes(usefulReason), "Useful additional grounded reason retained");
    assert(JSON.stringify(fallback) === before, "Useful fallback prose is not mutated");
  }
  const rejected = clone(fixtures.kandy);
  rejected.explanation_status = "LLM";
  rejected.explanation = { source: "LLM", summary: "The supplied assessment is no suitable option.", properties: [] };
  window.Agent4UI.render(rejected);
  const rejectionDetails = byClass(panel, "decision-support-details")[0];
  assert(rejectionDetails.textContent.includes("Why not shortlisted?") && rejectionDetails.textContent.includes("Does not match the requested location: Kandy"), "Alternative explains exclusion");
  assert(!rejectionDetails.textContent.includes("Decision-support score") && !rejectionDetails.textContent.includes("Final rank"), "Hard-constraint alternative hides score and has no rank");
  assert(!panel.textContent.includes("supplied assessment"), "No-suitable summary duplicates omitted");
  rejected.alternatives[0].constraint_checks = [{ requirement: "Generated layout satisfies Agent 3 constraints", status: "VIOLATED" }];
  rejected.alternatives[0].planning = { constraints_satisfied: false };
  window.Agent4UI.render(rejected);
  assert(!panel.textContent.includes("Not satisfied: Generated layout satisfies"), "No contradictory planning label");
  const consideration = byClass(panel, "pick-details").find(detail => detail.children[0].textContent === "What to consider");
  assert(consideration.textContent.split("The conceptual layout does not satisfy the planning constraints.").length === 2, "Natural planning failure deduplicated within considerations");
  // Rendering does not modify the original explanation, even when hidden.
  const untouched = JSON.parse(originalPolished);
  window.Agent4UI.render(untouched);
  assert(JSON.stringify(untouched) === originalPolished, "Polish leaves API explanation and scores intact");
  const technical = clone(fixtures.kottawa);
  technical.explanation_status = "LLM";
  const id = technical.recommendations[0].listing_id;
  technical.recommendations[0].constraint_checks.push({ requirement: "Expected cost fits original budget", status: "SATISFIED", evidence: "RAW_CHECK_MARKER Expected 3.79557e+07 LKR; ceiling 4e+07 LKR (TOTAL_PROJECT)" });
  technical.recommendations[0].criteria = [{ criterion: "budget", normalized_score: 0.715, weight: 0.35, contribution: 25.025, evidence_status: "KNOWN", explanation: "INTERNAL_CALCULATION_MARKER" }];
  technical.explanation = { source: "LLM", summary: `${id} has a TOTAL_PROJECT assessment.`,
    warnings: Array.from({ length: 20 }, () => [
      `${id}: Assumption: standard finish`, `${id}: Excluded cost: professional fees`,
      `${id}: Room geometry error in bedroom`, `${id}: Listing availability and claims have not been independently verified.`,
      `${id}: High construction/project cost scenario exceeds the original budget.`,
      `${id}: Strict constraints yielded no results.`,
    ]).flat(),
    properties: [{ listing_id: id, reason: "Recorded budget 3.79557e+07 (TOTAL_PROJECT)", strengths: technical.recommendations[0].strengths || [] }],
    comparison_summary: [], next_steps: [] };
  const unchanged = JSON.stringify(technical);
  window.Agent4UI.render(technical);
  assert(!/\d+(?:\.\d+)?e[+-]\d+/i.test(panel.textContent), "No scientific notation displayed");
  assert(!panel.textContent.includes("TOTAL_PROJECT") && !panel.textContent.includes("evidence known"), "No internal enum presentation");
  assert(!panel.textContent.includes("RAW_CHECK_MARKER") && !panel.textContent.includes("INTERNAL_CALCULATION_MARKER"), "Raw constraint evidence and calculations not exposed");
  assert(!panel.textContent.includes(id), "Known listing IDs replaced in explanatory prose");
  assert(panel.textContent.includes("71.5 / 100"), "Normalized criterion score retained");
  const important = byClass(panel, "results-notes").find(detail => detail.children[0].textContent === "Important notes");
  assert(important && important.children[1].children.length <= 5, "Page notes bounded despite repeated warnings");
  assert(important.textContent.includes("high-cost scenario") && important.textContent.includes("exact site fit cannot be confirmed") && important.textContent.includes("not been independently verified") && important.textContent.includes("preliminary") && important.textContent.includes("search was broadened"), "Notes selected by five material categories");
  assert(!important.textContent.includes("Assumption:") && !important.textContent.includes("Excluded cost:") && !important.textContent.includes("geometry"), "Candidate diagnostics not dumped at page level");
  assert(JSON.stringify(technical) === unchanged, "Original technical evidence remains unchanged");
  explained.explanation_status = "DETERMINISTIC_FALLBACK";
  explained.explanation.source = "DETERMINISTIC_FALLBACK";
  window.Agent4UI.render(explained);
  assert(panel.textContent.includes("Deterministic fallback explanation"), "Fallback transparency");
  const checkbox = sources["index.html"].match(/<input\b[^>]*id="explanation-enabled"[^>]*>/)?.[0];
  assert(checkbox && !/\bhidden\b|\bchecked\b/.test(checkbox), "AI control visible and unchecked");
  for (const enabled of [false, true]) {
    response = fixtures.kottawa;
    retrieval = { results: [...response.recommendations, ...response.alternatives].map(x => ({ listing_id: x.listing_id })) };
    document.querySelector("#explanation-enabled").checked = enabled;
    calls.length = 0;
    await app.continueWithRequirements({ intent: "LAND_AND_HOUSE", total_project_budget_lkr: 40000000, bedrooms: 3, bathrooms: 2, floors: 2 }, 0);
    assert(calls[0].url.endsWith("/api/v1/recommendation") && calls[0].body.top_k === 10, "Recommendation endpoint and top_k 10");
    assert(calls[0].body.explanation_enabled === enabled, "Checkbox sent to backend unchanged");
    assert(document.querySelector("#properties-panel").classList.contains("hidden"), "Recommendations AND alternatives excluded from supplementary search");
  }
  retrieval.results.push({ listing_id: "additional", title: injected, listing_type: "sale", property_type: "land", sale_total_price_lkr: 5000000 });
  await app.continueWithRequirements({ intent: "BUY_PROPERTY", maximum_budget_lkr: 30000000 }, 0);
  assert(document.querySelector("#options-title").textContent === "Additional retrieved listings", "Supplementary title");
  assert(document.querySelector("#market-analysis").textContent.includes("not final recommendations"), "Supplementary purpose clear");
  assert(document.querySelector("#property-list").children.length === 1, "Only genuinely additional listing shown");
  assert(document.querySelector("#property-list").textContent.includes(injected), "Listing title is literal text");
  app.showProperties({ results: [] });
  assert(document.querySelector("#properties-panel").classList.contains("hidden"), "Empty supplementary search hidden");
  app.openAdDetailsModal({ property: { listing_id: "source-flag", features: [], full_ad: { is_verified: true } } });
  assert(document.querySelector("#modal-content").textContent.includes("Marked verified in source data; not independently verified by PropWise"), "Modal verification qualified");
  assert(JSON.stringify(fixtures) === original, "API response objects not mutated");
  return { assertions, result: "PASS", network: "mock-only" };
}

if (typeof module !== "undefined") {
  module.exports = { runAgent4Smoke };
  if (require.main === module) {
    const fs = require("node:fs");
    const path = require("node:path");
    const sources = Object.fromEntries(["app.js", "agent4.js", "index.html"].map(name =>
      [name, fs.readFileSync(path.join(__dirname, "..", name), "utf8")]));
    runAgent4Smoke(sources).then(result => console.log(result)).catch(error => { console.error(error); process.exitCode = 1; });
  }
}
