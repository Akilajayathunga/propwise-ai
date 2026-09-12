from app.retrieval import analysis as analysis_module
from app.retrieval import filters, loader, scorer
from app.schemas.property import Agent2Result, PropertyResult
from app.schemas.requirements import ParsedRequirements


class PropertySearchAgent:
    """Orchestrator for Agent 2 - Property Search & Analysis.
    
    Responsible for executing the two-pass search strategy over the dataset:
      Pass 1: Apply strict user constraints (hard filters).
      Pass 2: If zero results, relax the strictest constraints (budget, bedrooms)
              and try again to avoid dead-ends.
              
    Finally, it scores, ranks, and analyses the resulting properties.
    """
    
    TOP_N_DEFAULT = 10

    def __init__(self, dataset_path: str | None = None) -> None:
        self.dataset_path = dataset_path

    def search(
        self,
        requirements: ParsedRequirements,
        top_n: int = TOP_N_DEFAULT,
    ) -> Agent2Result:
        # 1. Load data
        df = loader.load_dataset(self.dataset_path)

        # 2. Pass 1: Strict filters
        filtered_df = filters.apply_hard_filters(df, requirements, relax=False)
        relaxed = False

        # 3. Pass 2: Relax if empty
        if filtered_df.empty:
            filtered_df = filters.apply_hard_filters(df, requirements, relax=True)
            relaxed = True

        warnings = []
        if filtered_df.empty:
            warnings.append("No properties matched. Consider broadening location or budget constraints.")
            return Agent2Result(
                results=[],
                total_found=0,
                returned=0,
                relaxed_filters=relaxed,
                filters_applied=filters.describe_filters(requirements, relax=relaxed),
                analysis=analysis_module.compute_analysis(filtered_df, requirements),
                warnings=warnings,
                metadata={"dataset_size": len(df)},
            )

        # 4. Score and Rank
        scored_df = scorer.score_dataframe(filtered_df, requirements)
        
        # 5. Extract Top N
        top_n_df = scored_df.head(top_n)
        
        # 6. Build final models
        results = []
        for row in top_n_df.to_dict("records"):
            # Ensure NaN values are replaced with None for Pydantic models
            clean_row = {k: (v if not (isinstance(v, float) and v != v) else None) for k, v in row.items()}
            results.append(PropertyResult(**clean_row))

        # 7. Compute Market Analysis
        analysis = analysis_module.compute_analysis(filtered_df, requirements)

        if relaxed:
            warnings.append(
                "Strict constraints yielded no results. Dropped bedroom constraints "
                "and expanded budget ceiling by 20% to find fallback properties."
            )

        return Agent2Result(
            results=results,
            total_found=len(filtered_df),
            returned=len(results),
            relaxed_filters=relaxed,
            filters_applied=filters.describe_filters(requirements, relax=relaxed),
            analysis=analysis,
            warnings=warnings,
            metadata={"dataset_size": len(df), "top_n_requested": top_n},
        )

