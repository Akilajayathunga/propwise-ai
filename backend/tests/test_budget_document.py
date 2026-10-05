from app.agents.agent3_planning.budget_document import _write_budget_html


def test_budget_report_keeps_data_and_downloads_in_styled_document(tmp_path):
    report = tmp_path / "budget_report.html"
    _write_budget_html(
        report,
        {"listing_id": "land-1", "title": "Land <Kottawa>", "location": "Kottawa", "district": "Colombo", "features": []},
        {"bedrooms": 2, "bathrooms": 2, "floors": 1, "parking_spaces": 1, "estimated_floor_area_sqft": 1177.3},
        {"land_price_lkr": 11_000_000, "construction_expected_lkr": 22_368_700, "total_expected_lkr": 33_368_700, "expected_margin_lkr": 6_631_300},
        {"png_url": str(tmp_path / "ground_floor.png"), "budget_csv_url": str(tmp_path / "budget_breakdown.csv"), "budget_excel_url": str(tmp_path / "budget_summary.xls")},
        {"warnings": ["Verify <site> dimensions."]},
        [{"category": "Foundation", "share_percent": 18.0, "estimated_lkr": 4_026_366, "includes": "Footings"}],
        [{"work_item": "Cement", "unit": "bag", "quantity": None, "expected_rate_lkr": 2_034, "adjusted_estimate_lkr": None, "source_label": "Market guide"}],
        None,
    )

    html = report.read_text(encoding="utf-8")
    assert '<meta name="viewport" content="width=device-width, initial-scale=1"' in html
    assert "background: #dce9df" in html
    assert "background: #167780" in html
    assert "background: #f5ad83" in html
    assert "background: #c7e388" in html
    assert "Your project budget" in html
    assert "Rs. 33,368,700" in html
    assert "Land &lt;Kottawa&gt;" in html
    assert "Verify &lt;site&gt; dimensions." in html
    assert '<a class="action primary" href="budget_summary.xls" download>' in html
    assert '<a class="action" href="budget_breakdown.csv" download>' in html
    assert 'src="ground_floor.png"' in html
    assert "<div class=\"table-scroll\"><table>" in html
