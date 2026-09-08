"""Create a stable translation sheet from the BINU8 string-table export."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


CONTROL_CODE = re.compile(r"@[A-Za-z][A-Za-z0-9_]*")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--file-prefix", default="", help="only include rows whose file starts with this prefix")
    args = parser.parse_args()

    with args.source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if args.file_prefix:
        rows = [row for row in rows if row["file"].startswith(args.file_prefix)]

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
        for row in rows:
            source = row["text"]
            writer.writerow(
                {
                    "id": f"{row['file']}@{row['text_offset']}",
                    "file": row["file"],
                    "length_offset": row["length_offset"],
                    "text_offset": row["text_offset"],
                    "source": source,
                    "translation": "",
                    "control_codes": " ".join(CONTROL_CODE.findall(source)),
                    "status": "未翻译",
                    "notes": "",
                }
            )

    print(f"rows={len(rows)}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
