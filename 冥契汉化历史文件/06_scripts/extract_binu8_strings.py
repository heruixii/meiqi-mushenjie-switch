"""Extract length-prefixed UTF-8 strings from BINU8/DATU8 resources."""

from __future__ import annotations

import argparse
import csv
import re
import struct
from pathlib import Path


LENGTH = struct.Struct("<I")
TEXT_CHARS = re.compile(r"[\u3000-\u30ff\u3400-\u9fff\uf900-\ufaff]")


def looks_like_text(value: str) -> bool:
    if not value or "\ufffd" in value:
        return False
    if any(ord(char) < 0x20 and char not in "\t\r\n" for char in value):
        return False
    return bool(TEXT_CHARS.search(value)) or any(
        char.isascii() and (char.isalnum() or char in " _-./:@[]()")
        for char in value
    )


def extract(path: Path, root: Path) -> list[dict[str, int | str]]:
    data = path.read_bytes()
    rows: list[dict[str, int | str]] = []
    for length_offset in range(0, len(data) - LENGTH.size):
        (stored_length,) = LENGTH.unpack_from(data, length_offset)
        if stored_length < 2 or stored_length > len(data) - length_offset - LENGTH.size:
            continue
        text_start = length_offset + LENGTH.size
        text_end = text_start + stored_length
        if data[text_end - 1] != 0:
            continue
        raw = data[text_start : text_end - 1]
        try:
            value = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if not looks_like_text(value):
            continue
        rows.append(
            {
                "file": path.relative_to(root).as_posix(),
                "length_offset": length_offset,
                "text_offset": text_start,
                "stored_length": stored_length,
                "byte_length": len(raw),
                "text": value,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("romfs", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--all", action="store_true", help="also scan all files")
    args = parser.parse_args()

    root = args.romfs.resolve()
    if args.all:
        paths = sorted(path for path in root.rglob("*") if path.is_file())
    else:
        paths = sorted(root.glob("Script/*.binu8"))
        paths += sorted(root.glob("Config/*.datu8"))

    rows = [row for path in paths for row in extract(path, root)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "file",
                "length_offset",
                "text_offset",
                "stored_length",
                "byte_length",
                "text",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"files_scanned={len(paths)}")
    print(f"length_prefixed_strings={len(rows)}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
