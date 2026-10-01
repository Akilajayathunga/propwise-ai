"""Public projections of server-obtained evidence; absolute artifact paths stay private."""
import re
from pathlib import Path
from urllib.parse import quote

from app.schemas.recommendation_api import RecommendationPresentation, RetrievalDisplay

PLANS_ROOT = Path(__file__).resolve().parents[4] / "storage" / "plans"
ARTIFACT_NAME = re.compile(r"plan-[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+\.(?:png|svg|json|dxf|zip|csv|html|xls)$")
LINK_KEYS = {"svg_url", "png_url", "dxf_url", "zip_url", "json_url", "budget_doc_url",
             "budget_csv_url", "budget_excel_url"}
LINK_LIST_KEYS = {"svg_urls", "png_urls"}


def artifact_url(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        if value.startswith("/plans/"):
            relative = value[len("/plans/"):]
        else:
            relative = Path(value).resolve().relative_to(PLANS_ROOT.resolve()).as_posix()
        if not ARTIFACT_NAME.fullmatch(relative):
            return None
        return "/plans/" + quote(relative, safe="/.-_")
    except (ValueError, OSError):
        return None


def public_presentation(context, decision):
    result = RecommendationPresentation()
    allowed = {i.listing_id for i in decision.recommendations + decision.alternatives}
    if context.property_search:
        search = context.property_search
        result.properties = [p.model_copy(deep=True) for p in search.results if p.listing_id in allowed]
        result.retrieval = RetrievalDisplay(
            total_found=search.total_found, returned=search.returned, relaxed_filters=search.relaxed_filters,
            warnings=list(search.warnings), filters_applied=search.filters_applied,
            analysis=search.analysis,
            # Preserve complete metadata internally, project documented public fields.
            metadata={k: v for k, v in search.metadata.items() if k in {"dataset_size", "top_n_requested"}},
        )
    if context.land_house:
        for option in context.land_house.options:
            if option.property.get("listing_id") not in allowed:
                continue
            copy = option.model_copy(deep=True)
            copy.technical_data = {}
            copy.planning = {k: v for k, v in copy.planning.items() if k in {
                "plan_id", "constraints_satisfied", "exact_site_fit_verified", "layout_score", "space_efficiency"
            } | LINK_KEYS | LINK_LIST_KEYS}
            for key in LINK_KEYS:
                if key in copy.planning:
                    copy.planning[key] = artifact_url(copy.planning[key])
            for key in LINK_LIST_KEYS:
                if key in copy.planning:
                    values = copy.planning[key] if isinstance(copy.planning[key], list) else []
                    copy.planning[key] = [url for value in values if (url := artifact_url(value))]
            result.land_house_options.append(copy)
    if context.owned_land:
        result.owned_plan = context.owned_land.model_copy(deep=True)
        files = result.owned_plan.files
        for name in ("json", "dxf", "zip", "summary"):
            setattr(files, name, artifact_url(getattr(files, name)))
        for name in ("png", "svg"):
            setattr(files, name, [url for value in getattr(files, name) if (url := artifact_url(value))])
    return result
