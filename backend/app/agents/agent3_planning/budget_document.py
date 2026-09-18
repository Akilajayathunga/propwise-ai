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
    html_path = output_dir / "budget_report.html"
    planning = {**planning, "budget_csv_url": str(csv_path)}
    _write_budget_csv(csv_path, option, material_budget, market_item_budget)
    _write_budget_html(html_path, property_data, house, budget, planning, option, material_budget, market_item_budget, plan_response)
    return {"budget_csv_url": str(csv_path), "budget_doc_url": str(html_path)}


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
    market_rows = "\n".join(
        f"<tr><td>{_esc(row['work_item'])}</td><td>{_esc(row['unit'])}</td><td>{_quantity(row['quantity'])}</td><td>{_money(row['expected_rate_lkr'])}</td><td>{_money(row['adjusted_estimate_lkr'])}</td><td>{_esc(row['source_label'])}</td></tr>"
        for row in market_item_budget
    )
    plan_image = planning.get("png_url") or planning.get("svg_url")
    csv_link = f'<p><a href="{_relative_name(planning.get("budget_csv_url"))}" download>Download detailed CSV budget sheet</a></p>' if planning.get("budget_csv_url") else ""
    image_section = f'<img class="plan" src="{_relative_name(plan_image)}" alt="Conceptual floor plan" />' if plan_image else "<p>Plan image unavailable.</p>"
    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>PropWise Budget Report - {_esc(property_data.get('listing_id') or 'Option')}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1d2522; }}
    h1, h2 {{ margin-bottom: 8px; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 20px 0; }}
    .box {{ border: 1px solid #d8ded8; border-radius: 8px; padding: 12px; background: #fbfcfb; }}
    .box span {{ display: block; color: #61706a; font-size: 12px; margin-bottom: 6px; }}
    .box strong {{ font-size: 18px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
    th, td {{ border: 1px solid #d8ded8; padding: 9px; text-align: left; vertical-align: top; }}
    th {{ background: #e7f3f4; }}
    .plan {{ width: 100%; max-height: 760px; object-fit: contain; border: 1px solid #d8ded8; border-radius: 8px; }}
    .notice {{ color: #9f3a38; font-weight: 700; }}
  </style>
</head>
<body>
  <h1>PropWise AI Budget Report</h1>
  <p class="notice">Conceptual AI-assisted estimate - not a contractor quotation or quantity-surveyor estimate.</p>
  <h2>Property</h2>
  <p><strong>{_esc(property_data.get('title') or property_data.get('listing_id') or 'Selected land')}</strong></p>
  <p>{_esc(property_data.get('location') or '')} {_esc(property_data.get('district') or '')}</p>
  <p>{_esc(property_data.get('address') or '')}</p>
  <ul>{features}</ul>

  <div class="summary">
    <div class="box"><span>Land price</span><strong>{_money(budget.get('land_price_lkr'))}</strong></div>
    <div class="box"><span>Construction expected</span><strong>{_money(budget.get('construction_expected_lkr'))}</strong></div>
    <div class="box"><span>Expected total</span><strong>{_money(budget.get('total_expected_lkr'))}</strong></div>
    <div class="box"><span>Expected margin</span><strong>{_money(budget.get('expected_margin_lkr'))}</strong></div>
  </div>

  <h2>House Programme</h2>
  <p>{house.get('bedrooms')} bedrooms, {house.get('bathrooms')} bathrooms, {house.get('floors')} floor(s), {house.get('parking_spaces')} parking space(s).</p>
  <p>Estimated floor area: {house.get('estimated_floor_area_sqft')} sq.ft</p>

  <h2>Construction Budget By Material / Work Category</h2>
  {csv_link}
  <table>
    <thead><tr><th>Category</th><th>Share</th><th>Estimated amount</th><th>Includes</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Market Price Item Sheet</h2>
  <p>Work-item rows are scaled to the selected construction estimate. Material-unit rows are reference prices only until exact quantities are measured from a BOQ.</p>
  <table>
    <thead><tr><th>Item</th><th>Unit</th><th>Qty basis</th><th>Market expected rate</th><th>Approx. item cost</th><th>Source</th></tr></thead>
    <tbody>{market_rows}</tbody>
  </table>

  <h2>Conceptual Floor Plan</h2>
  {image_section}

  <h2>Warnings and Assumptions</h2>
  <ul>{warnings}</ul>
  <p>{_esc(COST_DISCLAIMER)}</p>
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
