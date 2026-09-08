"""Extract UTF-8, NUL-terminated text candidates from BINU8 resources."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


JAPANESE_OR_CJK = re.compile(r"[\u3000-\u30ff\u3400-\u9fff\uf900-\ufaff]")


def looks_like_text(value: str) -> bool:
    if len(value) < 2 or "\ufffd" in value:
        return False
    if any(ord(char) < 0x20 and char not in "\t\r\n" for char in value):
        return False
    return bool(JAPANESE_OR_CJK.search(value)) or any(
        char.isalpha() for char in value
    )


def scan_file(path: Path, root: Path) -> list[dict[str, str | int]]:
    data = path.read_bytes()
    rows: list[dict[str, str | int]] = []
    for start, raw in ((match.start(), match.group()) for match in re.finditer(rb"[^\x00]+", data)):
        try:
            value = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if not looks_like_text(value):
            continue
        rows.append(
            {
                "file": path.relative_to(root).as_posix(),
                "offset": start,
                "byte_length": len(raw),
                "text": value,
                "before4": data[max(0, start - 4) : start].hex(),
                "after4": data[start + len(raw) : start + len(raw) + 4].hex(),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("romfs", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.romfs.resolve()
    paths = sorted(root.glob("Script/*.binu8"))
    paths += sorted(root.glob("Config/*.datu8"))
    rows = [row for path in paths for row in scan_file(path, root)]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["file", "offset", "byte_length", "text", "before4", "after4"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"files_scanned={len(paths)}")
    print(f"text_candidates={len(rows)}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
