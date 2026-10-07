import csv
import html
from pathlib import Path
from typing import Any

from app.agents.agent3_planning.budget import COST_DISCLAIMER

ROOT = Path(__file__).resolve().parents[4]
MATERIAL_COSTS_PATH = ROOT / "data" / "knowledge" / "material_costs.csv"
MARKET_PRICES_PATH = ROOT / "data" / "knowledge" / "material_market_prices.csv"


def load_material_cost_allocations() -> list[dict[str, Any]]:
    with MATERIAL_COSTS_PATH.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [
        {
            "category": row["category"],
            "share_percent": float(row["share_percent"]),
            "includes": row["includes"],
            "notes": row["notes"],
        }
        for row in rows
    ]


def build_material_budget(construction_expected_lkr: float | None) -> list[dict[str, Any]]:
    allocations = load_material_cost_allocations()
    if construction_expected_lkr is None:
        return [
            {
                **item,
                "estimated_lkr": None,
            }
            for item in allocations
        ]
    return [
        {
            **item,
            "estimated_lkr": round(construction_expected_lkr * item["share_percent"] / 100, 2),
        }
        for item in allocations
    ]


def load_market_price_items() -> list[dict[str, Any]]:
    with MARKET_PRICES_PATH.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [
        {
            "work_item": row["work_item"],
            "unit": row["unit"],
            "low_rate_lkr": float(row["low_rate_lkr"]),
            "expected_rate_lkr": float(row["expected_rate_lkr"]),
            "high_rate_lkr": float(row["high_rate_lkr"]),
            "source_label": row["source_label"],
            "as_of": row["as_of"],
            "notes": row["notes"],
        }
        for row in rows
    ]


def build_market_item_budget(construction_expected_lkr: float | None, floor_area_sqft: float | None) -> list[dict[str, Any]]:
    items = load_market_price_items()
    work_items = [item for item in items if item["unit"] == "sqft"]
    raw_total = sum(item["expected_rate_lkr"] * (floor_area_sqft or 0) for item in work_items)
    scale = construction_expected_lkr / raw_total if construction_expected_lkr and raw_total else None
    rows = []
    for item in items:
        quantity = floor_area_sqft if item["unit"] == "sqft" else None
        market_expected_lkr = item["expected_rate_lkr"] * quantity if quantity else None
        adjusted_estimate_lkr = round(market_expected_lkr * scale, 2) if market_expected_lkr is not None and scale else market_expected_lkr
        rows.append({**item, "quantity": quantity, "market_expected_lkr": market_expected_lkr, "adjusted_estimate_lkr": adjusted_estimate_lkr})
    return rows


def write_budget_documents(output_dir: Path, option: dict, plan_response) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    property_data = option.get("property", {})
    house = option.get("house", {})
    budget = option.get("budget", {})
    planning = option.get("planning", {})
    material_budget = build_material_budget(budget.get("construction_expected_lkr"))
    market_item_budget = build_market_item_budget(budget.get("construction_expected_lkr"), house.get("estimated_floor_area_sqft"))

    csv_path = output_dir / "budget_breakdown.csv"
    excel_path = output_dir / "budget_summary.xls"
    html_path = output_dir / "budget_report.html"
    planning = {**planning, "budget_csv_url": str(csv_path), "budget_excel_url": str(excel_path)}
    _write_budget_csv(csv_path, option, material_budget, market_item_budget)
    _write_budget_excel(excel_path, property_data, house, budget, material_budget, market_item_budget)
    _write_budget_html(html_path, property_data, house, budget, planning, option, material_budget, market_item_budget, plan_response)
    return {"budget_csv_url": str(csv_path), "budget_excel_url": str(excel_path), "budget_doc_url": str(html_path)}


def _write_budget_csv(path: Path, option: dict, material_budget: list[dict[str, Any]], market_item_budget: list[dict[str, Any]]) -> None:
    budget = option.get("budget", {})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["section", "item", "value_lkr", "share_percent", "notes"])
        writer.writerow(["project", "land_price_lkr", budget.get("land_price_lkr"), "", "Selected land listing price."])
        writer.writerow(["project", "construction_expected_lkr", budget.get("construction_expected_lkr"), "", "Expected construction estimate from configured profile."])
        writer.writerow(["project", "total_expected_lkr", budget.get("total_expected_lkr"), "", "Land plus expected construction estimate."])
        writer.writerow(["project", "maximum_total_budget_lkr", budget.get("total_project_budget_lkr"), "", "User supplied total project budget."])
        writer.writerow(["project", "expected_margin_lkr", budget.get("expected_margin_lkr"), "", "Budget minus expected total."])
        for row in material_budget:
            writer.writerow(["construction", row["category"], row["estimated_lkr"], row["share_percent"], row["notes"]])
        writer.writerow([])
        writer.writerow(["market_item", "unit", "quantity", "expected_rate_lkr", "adjusted_estimate_lkr", "source", "as_of", "notes"])
        for row in market_item_budget:
            writer.writerow(
                [
                    row["work_item"],
                    row["unit"],
                    row["quantity"],
                    row["expected_rate_lkr"],
                    row["adjusted_estimate_lkr"],
                    row["source_label"],
                    row["as_of"],
                    row["notes"],
                ]
            )


def _write_budget_excel(
    path: Path,
    property_data: dict,
    house: dict,
    budget: dict,
    material_budget: list[dict[str, Any]],
    market_item_budget: list[dict[str, Any]],
) -> None:
    category_rows = "\n".join(
        f"<tr><td>{_esc(row['category'])}</td><td>{row['share_percent']:.1f}%</td><td>{_money(row['estimated_lkr'])}</td><td>{_esc(row['notes'])}</td></tr>"
        for row in material_budget
    )
    market_rows = "\n".join(
        f"<tr><td>{_esc(row['work_item'])}</td><td>{_esc(row['unit'])}</td><td>{_quantity(row['quantity'])}</td><td>{_money(row['expected_rate_lkr'])}</td><td>{_money(row['adjusted_estimate_lkr'])}</td><td>{_esc(row['source_label'])}</td></tr>"
        for row in market_item_budget
    )
    path.write_text(
        f"""<html>
<head>
  <meta charset="utf-8" />
  <style>
    body {{ font-family: Arial, sans-serif; }}
    h1, h2 {{ color: #06626d; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 18px; }}
    th {{ background: #087f8c; color: white; }}
    th, td {{ border: 1px solid #9db4ad; padding: 8px; text-align: left; }}
  </style>
</head>
<body>
  <h1>PropWise AI Budget Summary</h1>
  <table>
    <tr><th>Field</th><th>Value</th></tr>
    <tr><td>Property</td><td>{_esc(property_data.get('title') or property_data.get('listing_id') or 'Selected land')}</td></tr>
    <tr><td>Location</td><td>{_esc(property_data.get('location'))}, {_esc(property_data.get('district'))}</td></tr>
    <tr><td>House</td><td>{house.get('bedrooms')} bedrooms, {house.get('bathrooms')} bathrooms, {house.get('floors')} floor(s)</td></tr>
    <tr><td>Estimated floor area</td><td>{house.get('estimated_floor_area_sqft')} sqft</td></tr>
    <tr><td>Land price</td><td>{_money(budget.get('land_price_lkr'))}</td></tr>
    <tr><td>Construction expected</td><td>{_money(budget.get('construction_expected_lkr'))}</td></tr>
    <tr><td>Expected total</td><td>{_money(budget.get('total_expected_lkr'))}</td></tr>
    <tr><td>Expected margin</td><td>{_money(budget.get('expected_margin_lkr'))}</td></tr>
  </table>
  <h2>Category Budget</h2>
  <table>
    <tr><th>Category</th><th>Share</th><th>Estimated Amount</th><th>Notes</th></tr>
    {category_rows}
  </table>
  <h2>Market Price Item Sheet</h2>
  <table>
    <tr><th>Item</th><th>Unit</th><th>Qty Basis</th><th>Market Expected Rate</th><th>Approx. Item Cost</th><th>Source</th></tr>
    {market_rows}
  </table>
</body>
</html>""",
        encoding="utf-8",
    )


def _write_budget_html(
    path: Path,
    property_data: dict,
    house: dict,
    budget: dict,
    planning: dict,
    option: dict,
    material_budget: list[dict[str, Any]],
    market_item_budget: list[dict[str, Any]],
    plan_response,
) -> None:
    rows = "\n".join(
        f"<tr><td>{_esc(row['category'])}</td><td>{row['share_percent']:.1f}%</td><td>{_money(row['estimated_lkr'])}</td><td>{_esc(row['includes'])}</td></tr>"
        for row in material_budget
    )
    warnings = "".join(f"<li>{_esc(item)}</li>" for item in option.get("warnings", []))
    features = "".join(f"<li>{_esc(item)}</li>" for item in property_data.get("features", []))
    feature_list = f"<ul>{features}</ul>" if features else ""
    market_rows = "\n".join(
        f"<tr><td>{_esc(row['work_item'])}</td><td>{_esc(row['unit'])}</td><td>{_quantity(row['quantity'])}</td><td>{_money(row['expected_rate_lkr'])}</td><td>{_money(row['adjusted_estimate_lkr'])}</td><td>{_esc(row['source_label'])}</td></tr>"
        for row in market_item_budget
    )
    plan_image = planning.get("png_url") or planning.get("svg_url")
    csv_link = f'<a class="action" href="{_relative_name(planning.get("budget_csv_url"))}" download>Download CSV</a>' if planning.get("budget_csv_url") else ""
    excel_link = f'<a class="action primary" href="{_relative_name(planning.get("budget_excel_url"))}" download>Download Excel</a>' if planning.get("budget_excel_url") else ""
    image_section = f'<img class="plan" src="{_relative_name(plan_image)}" alt="Conceptual floor plan" />' if plan_image else "<p>Plan image unavailable.</p>"
    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>PropWise Budget Report - {_esc(property_data.get('listing_id') or 'Option')}</title>
  <style>
    :root {{ color-scheme: light; --ink: #19312b; --muted: #4e675c; --green: #194b40; --line: #afc8b8; --peach: #eda374; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #dce9df; color: var(--ink); font: 15px/1.55 Arial, sans-serif; }}
    .shell {{ max-width: 1280px; margin: 0 auto; padding: 34px clamp(18px, 3vw, 44px) 72px; }}
    .hero {{ display: flex; align-items: end; justify-content: space-between; gap: 30px; padding: clamp(28px, 4vw, 52px); border-radius: 8px; background: var(--green); color: #f5faf5; }}
    .hero-label {{ margin: 0 0 15px; color: #bfe0c8; font-size: 11px; font-weight: 800; text-transform: uppercase; }}
    .hero h1 {{ max-width: 650px; margin: 0 0 12px; font-size: clamp(30px, 3.5vw, 46px); line-height: 1.1; }}
    .hero p {{ max-width: 570px; margin: 0; color: #d8e9dd; }}
    .hero-total {{ min-width: 230px; padding-left: 22px; border-left: 3px solid var(--peach); }}
    .hero-total span {{ display: block; color: #c9e0d2; font-size: 12px; }}
    .hero-total strong {{ display: block; margin-top: 4px; color: #ffd2af; font-size: clamp(24px, 2.8vw, 36px); line-height: 1.12; white-space: nowrap; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 22px 0 30px; }}
    .action {{ display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 10px 17px; border: 1px solid #789e88; border-radius: 5px; color: var(--green); background: #edf5ed; font-weight: 700; text-decoration: none; }}
    .action.primary {{ border-color: var(--peach); background: var(--peach); color: #25312b; }}
    .action:hover {{ background: #ffffff; }}
    .action:focus-visible {{ outline: 3px solid #b3552b; outline-offset: 3px; }}
    .section {{ padding: 28px 0 31px; border-bottom: 1px solid var(--line); }}
    .section h2 {{ margin: 0 0 15px; color: var(--green); font-size: 23px; line-height: 1.2; }}
    .section p {{ margin: 7px 0; }}
    .section-heading {{ display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; }}
    .section-heading p {{ max-width: 720px; color: var(--muted); font-size: 13px; }}
    .property-name {{ margin: 0 0 7px; font-size: 21px; font-weight: 750; }}
    .property-location {{ color: var(--muted); }}
    .notice {{ margin: 0 0 2px; padding: 13px 16px; border-left: 4px solid #c46c43; border-radius: 3px; background: #f4dfcf; color: #723e29; font-weight: 700; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 20px 0 0; }}
    .box {{ min-width: 0; min-height: 112px; padding: 19px; border: 1px solid #126f76; border-top: 5px solid #93d9cb; border-radius: 6px; background: #167780; color: #fff; box-shadow: 0 10px 24px rgba(25, 75, 64, 0.12); }}
    .box:nth-child(2) {{ border-color: #db825b; border-top-color: #a74d37; background: #f5ad83; color: #38271f; }}
    .box.emphasis {{ border-color: #123f36; border-top-color: var(--peach); background: #123f36; color: #fff; }}
    .box:nth-child(4) {{ border-color: #a7c36b; border-top-color: #668441; background: #c7e388; color: #263721; }}
    .box span {{ display: block; margin-bottom: 8px; color: #e0f4ed; font-size: 12px; }}
    .box:nth-child(2) span, .box:nth-child(4) span {{ color: #4e4b32; }}
    .box.emphasis span {{ color: #d5ead9; }}
    .box strong {{ display: block; font-size: 21px; line-height: 1.25; overflow-wrap: anywhere; }}
    .house-facts {{ display: flex; gap: 14px 32px; flex-wrap: wrap; font-weight: 700; }}
    .house-facts span {{ color: var(--green); }}
    .table-scroll {{ width: 100%; overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; background: #e9f2e9; }}
    table {{ width: 100%; min-width: 680px; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 12px 13px; border-bottom: 1px solid #c7d9ca; text-align: left; vertical-align: top; }}
    th {{ background: var(--green); color: white; font-weight: 700; white-space: nowrap; }}
    tbody tr:nth-child(even) {{ background: #e2eee4; }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    .plan-wrap {{ padding: 18px; border: 1px solid var(--line); border-radius: 6px; background: #eaf2eb; }}
    .plan {{ display: block; width: 100%; max-height: 760px; object-fit: contain; }}
    .assumptions {{ padding-left: 20px; }}
    .assumptions li {{ margin: 7px 0; }}
    .disclaimer {{ margin-top: 23px !important; color: var(--muted); font-size: 12px; }}
    @media (max-width: 760px) {{
      .shell {{ padding-top: 16px; }}
      .hero {{ align-items: start; flex-direction: column; gap: 23px; }}
      .hero-total {{ width: 100%; min-width: 0; }}
      .summary {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 440px) {{
      .summary {{ grid-template-columns: 1fr; }}
      .actions .action {{ flex: 1 1 100%; }}
      .hero-total strong {{ white-space: normal; }}
      .section h2 {{ font-size: 21px; }}
    }}
    @media print {{
      body {{ background: white; print-color-adjust: exact; }}
      .shell {{ max-width: none; padding: 0; }}
      .actions {{ display: none; }}
      .hero, .section, .box, .table-scroll {{ break-inside: avoid; }}
      .table-scroll {{ overflow: visible; }}
      table {{ min-width: 0; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
  <section class="hero">
    <div>
      <div class="hero-label">PropWise AI / Project estimate</div>
      <h1>Your project budget</h1>
      <p>Approximate planning budget for the selected land and house option.</p>
    </div>
    <div class="hero-total"><span>Expected total</span><strong>{_money(budget.get('total_expected_lkr'))}</strong></div>
  </section>
  <div class="actions">{excel_link}{csv_link}</div>
  <p class="notice">Conceptual AI-assisted estimate - not a contractor quotation or quantity-surveyor estimate.</p>
  <section class="section">
    <h2>Selected property</h2>
    <p class="property-name">{_esc(property_data.get('title') or property_data.get('listing_id') or 'Selected land')}</p>
    <p class="property-location">{_esc(property_data.get('location') or '')} {_esc(property_data.get('district') or '')}</p>
    <p>{_esc(property_data.get('address') or '')}</p>
    {feature_list}
  </section>

  <section class="section">
  <h2>Budget at a glance</h2>
  <div class="summary">
    <div class="box"><span>Land price</span><strong>{_money(budget.get('land_price_lkr'))}</strong></div>
    <div class="box"><span>Construction expected</span><strong>{_money(budget.get('construction_expected_lkr'))}</strong></div>
    <div class="box emphasis"><span>Expected total</span><strong>{_money(budget.get('total_expected_lkr'))}</strong></div>
    <div class="box"><span>Expected margin</span><strong>{_money(budget.get('expected_margin_lkr'))}</strong></div>
  </div>
  </section>

  <section class="section">
  <h2>House programme</h2>
  <div class="house-facts"><span>{house.get('bedrooms')} bedrooms</span><span>{house.get('bathrooms')} bathrooms</span><span>{house.get('floors')} floor(s)</span><span>{house.get('parking_spaces')} parking space(s)</span><span>{house.get('estimated_floor_area_sqft')} sq.ft estimated</span></div>
  </section>

  <section class="section">
  <h2>Construction budget by category</h2>
  <div class="table-scroll"><table>
    <thead><tr><th>Category</th><th>Share</th><th>Estimated amount</th><th>Includes</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
  </section>

  <section class="section">
  <h2>Market Price Item Sheet</h2>
  <p>Work-item rows are scaled to the selected construction estimate. Material-unit rows are reference prices only until exact quantities are measured from a BOQ.</p>
  <div class="table-scroll"><table>
    <thead><tr><th>Item</th><th>Unit</th><th>Qty basis</th><th>Market expected rate</th><th>Approx. item cost</th><th>Source</th></tr></thead>
    <tbody>{market_rows}</tbody>
  </table></div>
  </section>

  <section class="section">
  <h2>Conceptual floor plan</h2>
  <div class="plan-wrap">{image_section}</div>
  </section>

  <section class="section">
  <h2>Warnings and assumptions</h2>
  <ul class="assumptions">{warnings}</ul>
  <p class="disclaimer">{_esc(COST_DISCLAIMER)}</p>
  </section>
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )


def _relative_name(path_value: str | None) -> str:
    if not path_value:
        return ""
    return Path(path_value).name


def _money(value: Any) -> str:
    if value is None:
        return "Not available"
    return f"Rs. {float(value):,.0f}"


def _quantity(value: Any) -> str:
    if value is None:
        return "Reference only"
    return f"{float(value):,.0f}"


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))
