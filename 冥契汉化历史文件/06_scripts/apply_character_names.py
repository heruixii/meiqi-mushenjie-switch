"""Apply confirmed Chinese names to exact standalone speaker-name records."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def load_mapping(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        return {
            row["游戏内姓名字段"]: row["电脑端/本项目中文名"]
            for row in rows
            if row.get("游戏内姓名字段") and row.get("电脑端/本项目中文名")
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sheet", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    mapping = load_mapping(args.mapping)
    with args.sheet.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    changed = 0
    matched_fields: set[str] = set()
    for row in rows:
        source = row.get("source", "")
        translation = mapping.get(source)
        if translation is None:
            continue
        matched_fields.add(source)
        if row.get("translation") != translation:
            row["translation"] = translation
            row["status"] = "术语检查"
            row["notes"] = "独立角色名；依据人物名表"
            changed += 1

    missing = sorted(set(mapping) - matched_fields)
    if missing:
        raise ValueError(f"mapping fields not found as standalone records: {', '.join(missing)}")

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

    print(f"mapped_fields={len(matched_fields)}")
    print(f"rows_changed={changed}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
