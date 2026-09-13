# Agent Contracts

This document records conceptual interfaces only. Concrete schemas and implementations will be added later.

## Agent 1: Requirement & Intent Understanding

Input: natural language from the user.

Output: structured requirements describing intent, budget, location preferences, property constraints, and route selection.

## Agent 2: Property Search & Analysis

Input: structured property requirements.

Output: ranked retrieved properties with relevant analysis signals.

## Agent 3: Home Planning & Budget Estimation

Input: house or land-and-house requirements.

Input may include selected land context from Agent 2. Agent 3 adapts Agent 2 property fields into `SelectedPropertyContext`:

| Agent 2 Field | Agent 3 Field |
| --- | --- |
| `listing_id` | `listing_id` |
| `location` | `location` |
| `district` | `district` |
| `property_type` | `property_type` |
| `land_size_perches` | `land_size_perches` |
| `sale_total_price_lkr` | `land_price_lkr` |
| `score` | `source_score` |

Optional fields such as `land_width_ft`, `land_length_ft`, and `road_side` remain `null` when Agent 2 does not provide them. Agent 3 must not invent these values.

Output: conceptual canonical plan JSON, SVG floor-plan visuals, PNG previews, conceptual DXF, budget status, warnings, and responsible AI disclaimer.

Budget estimation uses `data/knowledge/construction_costs.json`. If verified construction rates are unavailable, Agent 3 returns `budget_estimation_available=false` and `budget_status=COST_DATA_UNAVAILABLE`.

## Agent 4: Recommendation & Decision Support

Input: validated outputs from previous agents.

Output: final recommendation and decision-support summary.

No agent schemas or business logic are implemented yet.
