"""Normalize localized Chinese fields to Simplified Chinese."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from opencc import OpenCC


def normalize(path: Path, field: str, delimiter: str) -> int:
    converter = OpenCC("t2s")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=delimiter))
    changed = 0
    for row in rows:
        original = row.get(field, "")
        updated = converter.convert(original)
        if updated != original:
            row[field] = updated
            changed += 1
    if not rows:
        return 0
    fields = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--batches", type=Path, nargs="*", default=[])
    parser.add_argument("--names", type=Path, required=True)
    parser.add_argument("--glossary", type=Path, required=True)
    args = parser.parse_args()

    total = 0
    total += normalize(args.master, "translation", "\t")
    for batch in args.batches:
        total += normalize(batch, "translation", "\t")
    total += normalize(args.names, "电脑端/本项目中文名", ",")
    total += normalize(args.glossary, "中文", ",")
    print(f"fields_changed={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
