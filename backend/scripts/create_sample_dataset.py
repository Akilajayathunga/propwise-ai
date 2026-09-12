"""
Create reproducible representative samples from PropWise AI's cleaned property dataset.

Usage from repository backend folder:
    python -m scripts.create_sample_dataset --mode git
    python -m scripts.create_sample_dataset --mode development --size 10000

The script samples from the CLEANED dataset. It never creates artificial listings
and never modifies the source file.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import random
from collections import Counter, defaultdict
from pathlib import Path

GROUP_FIELDS = ("district", "property_type", "listing_type")

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def resolve_source(cli_source: str | None) -> Path:
    if cli_source:
        return Path(cli_source).expanduser().resolve()

    env_path = os.getenv("CLEANED_DATASET_PATH")
    if env_path:
        p = Path(env_path).expanduser()
        if not p.is_absolute():
            p = project_root() / p
        return p.resolve()

    return (project_root() / "data" / "processed" / "properties_cleaned.csv").resolve()

def allocate_quotas(counts: Counter, target: int) -> dict:
    total = sum(counts.values())
    if target >= total:
        return dict(counts)

    exact = {g: c * target / total for g, c in counts.items()}
    quotas = {g: int(math.floor(v)) for g, v in exact.items()}

    if len(counts) <= target:
        for g, c in counts.items():
            if c > 0 and quotas[g] == 0:
                quotas[g] = 1

    while sum(quotas.values()) > target:
        candidates = [g for g, q in quotas.items() if q > 1] or [g for g, q in quotas.items() if q > 0]
        g = max(candidates, key=lambda x: (quotas[x] - exact[x], quotas[x], counts[x]))
        quotas[g] -= 1

    remainders = sorted(
        counts,
        key=lambda g: (exact[g] - math.floor(exact[g]), counts[g], g),
        reverse=True,
    )
    idx = 0
    while sum(quotas.values()) < target:
        g = remainders[idx % len(remainders)]
        if quotas[g] < counts[g]:
            quotas[g] += 1
        idx += 1

    return quotas

def create_sample(source: Path, output: Path, target: int, seed: int) -> None:
    if not source.exists():
        raise SystemExit(
            f"Cleaned dataset not found: {source}\n"
            "Set CLEANED_DATASET_PATH in backend/.env or pass --source."
        )

    with source.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise SystemExit("CSV header is missing.")

        missing = [c for c in GROUP_FIELDS if c not in fieldnames]
        counts = Counter()
        total = 0
        for row in reader:
            if missing:
                key = ("ALL",)
            else:
                key = tuple((row.get(c) or "").strip() for c in GROUP_FIELDS)
            counts[key] += 1
            total += 1

    target = min(target, total)
    quotas = allocate_quotas(counts, target)
    rng = random.Random(seed)
    seen = Counter()
    reservoirs = defaultdict(list)

    with source.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = ("ALL",) if missing else tuple((row.get(c) or "").strip() for c in GROUP_FIELDS)
            k = quotas.get(key, 0)
            if not k:
                continue
            seen[key] += 1
            i = seen[key]
            bucket = reservoirs[key]
            if len(bucket) < k:
                bucket.append(row.copy())
            else:
                j = rng.randrange(i)
                if j < k:
                    bucket[j] = row.copy()

    rows = [r for g in sorted(reservoirs) for r in reservoirs[g]]
    rng.shuffle(rows)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Source: {source}")
    print(f"Source rows: {total:,}")
    print(f"Output: {output}")
    print(f"Sample rows: {len(rows):,}")
    print(f"Seed: {seed}")
    if missing:
        print(f"Warning: missing stratification fields {missing}; used reproducible random sampling.")
    else:
        print(f"Stratified by: {', '.join(GROUP_FIELDS)}")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["git", "development"], required=True)
    parser.add_argument("--size", type=int)
    parser.add_argument("--seed", type=int, default=int(os.getenv("RANDOM_SEED", "42")))
    parser.add_argument("--source")
    args = parser.parse_args()

    root = project_root()
    source = resolve_source(args.source)

    if args.mode == "git":
        size = args.size or int(os.getenv("GIT_SAMPLE_SIZE", "500"))
        output = root / "data" / "sample" / "properties_sample.csv"
    else:
        size = args.size or int(os.getenv("DEVELOPMENT_SAMPLE_SIZE", "10000"))
        output = root / "data" / "local" / "properties_dev.csv"

    if size <= 0:
        raise SystemExit("--size must be greater than zero.")

    create_sample(source, output, size, args.seed)

if __name__ == "__main__":
    main()
