"""Add contact_number to property CSV files without inventing missing numbers."""

from __future__ import annotations

import csv
from pathlib import Path

from app.retrieval.contact import extract_contact_number


ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    ROOT / "data" / "sample" / "properties_sample.csv",
    ROOT / "data" / "local" / "properties_dev.csv",
    ROOT / "data" / "local" / "properties_dev_10000.csv",
    ROOT / "data" / "processed" / "properties_cleaned.csv",
]


def add_contact_numbers(path: Path) -> None:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if "contact_number" not in fieldnames:
        fieldnames.append("contact_number")

    for row in rows:
        row["contact_number"] = row.get("contact_number") or extract_contact_number(
            row.get("description"),
            row.get("title"),
            row.get("address"),
            row.get("features"),
        )

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    for path in TARGETS:
        add_contact_numbers(path)
        print(f"updated {path}")


if __name__ == "__main__":
    main()
