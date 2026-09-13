from app.agents.agent2_property.agent import PropertySearchAgent
from app.schemas.requirements import Intent, ParsedRequirements


def test_agent2_buy_property_pipeline() -> None:
    req = ParsedRequirements(
        original_query="test",
        intent=Intent.BUY_PROPERTY,
        location="Colombo",
        listing_type="sale",
        property_type="house",
        maximum_budget_lkr=30_000_000,
        bedrooms=3,
    )
    
    agent = PropertySearchAgent()
    result = agent.search(req, top_n=5)
    
    assert result.returned <= 5
    assert result.total_found >= result.returned
    assert not result.relaxed_filters
    
    if result.results:
        # Check all results respect hard constraints
        for p in result.results:
            assert p.sale_total_price_lkr <= 30_000_000
            assert p.bedrooms >= 3
            assert p.listing_type.lower() == "sale"
            
        # Check scores are descending
        scores = [p.score for p in result.results]
        assert scores == sorted(scores, reverse=True)


def test_agent2_rent_property_pipeline() -> None:
    req = ParsedRequirements(
        original_query="test",
        intent=Intent.RENT_PROPERTY,
        listing_type="rent",
        property_type="apartment",
        maximum_budget_lkr=150_000,
    )
    
    agent = PropertySearchAgent()
    result = agent.search(req)
    
    if result.results:
        for p in result.results:
            assert p.rent_monthly_lkr <= 150_000
            assert p.listing_type.lower() == "rent"


def test_agent2_fallback_relaxation() -> None:
    # 100 LKR budget is impossible for a 3-bedroom house in Colombo
    req = ParsedRequirements(
        original_query="test",
        intent=Intent.BUY_PROPERTY,
        location="Colombo",
        listing_type="sale",
        property_type="house",
        maximum_budget_lkr=100,
        bedrooms=3,
    )
    
    agent = PropertySearchAgent()
    result = agent.search(req)
    
    assert result.returned == 0
    # Because there's no matches even if budget expanded by 20%
    assert result.relaxed_filters is True
    assert "No properties matched" in result.warnings[0]


def test_agent2_land_and_house_intent() -> None:
    req = ParsedRequirements(
        original_query="test",
        intent=Intent.LAND_AND_HOUSE,
        location="Colombo",
        listing_type="sale",
        total_project_budget_lkr=40_000_000,
    )
    
    agent = PropertySearchAgent()
    result = agent.search(req)
    
    if result.results:
        # Should only return land
        for p in result.results:
            assert p.property_type.lower() == "land"
            
    # Check analysis passes budget forward
    assert "land_and_house" in result.analysis
    assert result.analysis["land_and_house"]["total_project_budget_lkr"] == 40_000_000

