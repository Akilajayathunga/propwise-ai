# Dataset

PropWise AI uses a real Sri Lankan property dataset.

The raw dataset contains approximately 203,874 rows. The cleaned dataset contains approximately 202,309 rows. Full datasets should remain outside Git and be referenced through environment variables.

## Environment Variables

- `PROPERTY_DATASET_PATH`: optional path to the raw property dataset.
- `CLEANED_DATASET_PATH`: optional override for the full cleaned property dataset used for sample generation.
- `GIT_SAMPLE_SIZE`: default 500.
- `DEVELOPMENT_SAMPLE_SIZE`: default 10,000.
- `RANDOM_SEED`: default 42.

By default, the cleaned dataset is expected at `data/processed/properties_cleaned.csv` from the project root.

## Folder Layout

- `data/raw/properties.csv`: original dataset, approximately 203,874 rows, local-only.
- `data/processed/properties_cleaned.csv`: cleaned dataset, approximately 202,309 rows, local-only.
- `data/sample/properties_sample.csv`: Git sample, approximately 500 rows, allowed in Git.
- `data/local/properties_dev.csv`: development sample, approximately 10,000 rows, local-only.
- `data/knowledge/`: future Agent 3 knowledge-base files; keep only `.gitkeep` for now.

## Sampling

The script `backend/scripts/create_sample_dataset.py` creates reproducible subsets from the real cleaned dataset. It does not create artificial property records and does not modify the source dataset.

When available, sampling tries to preserve diversity across:

- `district`
- `property_type`
- `listing_type`

If group-aware sampling is not possible because columns are missing or rare groups make allocation impractical, the script falls back to reproducible random sampling.

## Sample Types

- Git sample: `data/sample/properties_sample.csv`, about 500 rows, allowed in Git.
- Development sample: `data/local/properties_dev.csv`, about 10,000 rows, ignored by Git.
- Final dataset: the full cleaned dataset of approximately 202,309 records.

The 500-row Git sample and 10,000-row development sample are temporary subsets. Future ingestion and retrieval code must support the full cleaned dataset.
