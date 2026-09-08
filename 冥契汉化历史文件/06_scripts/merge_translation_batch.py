"""Merge an offset-stable translation batch into the master TSV sheet."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sheet", type=Path)
    parser.add_argument("batch", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    with args.batch.open(encoding="utf-8-sig", newline="") as handle:
        batch_rows = list(csv.DictReader(handle, delimiter="\t"))
    updates: dict[str, str] = {}
    for row in batch_rows:
        key = row.get("id", "")
        translation = row.get("translation", "")
        if not key or not translation:
            raise ValueError("every batch row needs a non-empty id and translation")
        if key in updates:
            raise ValueError(f"duplicate batch id: {key}")
        updates[key] = translation

    with args.sheet.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    found: set[str] = set()
    for row in rows:
        key = row.get("id", "")
        if key not in updates:
            continue
        translation = updates[key]
        if row.get("translation") and row["translation"] != translation:
            raise ValueError(f"translation already differs at {key}")
        row["translation"] = translation
        row["status"] = "初译完成"
        row["notes"] = "第一幕开场段；结合上下文人工初译"
        found.add(key)

    missing = sorted(set(updates) - found)
    if missing:
        raise ValueError(f"batch ids not found in master sheet: {', '.join(missing)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "id",
        "file",
        "length_offset",
        "text_offset",
        "source",
        "translation",
        "control_codes",
        "status",
        "notes",
    ]
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"batch_rows={len(updates)}")
    print(f"rows_updated={len(found)}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
