# Data

PropWise AI uses a real Sri Lankan property dataset.

## Data Flow

```text
Original dataset
203,874 rows
        |
Cleaning
        |
Cleaned dataset
202,309 rows
        |
 +--------------+----------------+
 |              |                |
500 rows        10,000 rows      Full cleaned dataset
Git sample      Dev sample       Final retrieval source
 |              |
Tests/examples  Development
```

## Folder Purposes

- `data/raw/properties.csv`: original Sri Lankan property dataset, approximately 203,874 rows. Never modify directly.
- `data/processed/properties_cleaned.csv`: main cleaned dataset, approximately 202,309 rows. This is the future Agent 2 retrieval source.
- `data/sample/properties_sample.csv`: small sample of about 500 rows for tests, examples, demonstrations, and team onboarding. This may be committed, but it must come from the real cleaned dataset.
- `data/local/properties_dev.csv`: development sample of about 10,000 rows for early Supabase development, Agent 2 development, embedding experiments, and hybrid search testing.
- `data/knowledge/`: future knowledge-base files used mainly by Agent 3. Keep only `.gitkeep` at this stage.

The development samples do not replace the full dataset. The final architecture must support approximately 202,309 cleaned records.

Large dataset CSV files should be committed through Git LFS.
