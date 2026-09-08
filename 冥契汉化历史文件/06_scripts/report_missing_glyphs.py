"""Report character coverage across the game's bundled TTC fonts."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from analyze_fonts import ttc_cmap


def collect_characters(sheet: Path) -> set[str]:
    characters: set[str] = set()
    with sheet.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            for field in ("source", "translation"):
                characters.update(row.get(field, ""))
    return characters


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("romfs", type=Path)
    parser.add_argument("sheet", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    characters = sorted(collect_characters(args.sheet), key=ord)
    fonts = {
        path.name: ttc_cmap(path)
        for path in sorted((args.romfs / "System").glob("*.ttc"))
    }
    fields = ["character", "codepoint", *fonts, "covered_by_any"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for character in characters:
            covered = {name: ord(character) in cmap for name, cmap in fonts.items()}
            writer.writerow(
                {
                    "character": character,
                    "codepoint": f"U+{ord(character):04X}",
                    **{name: "yes" if value else "no" for name, value in covered.items()},
                    "covered_by_any": "yes" if any(covered.values()) else "no",
                }
            )

    missing_all = [
        character
        for character in characters
        if not any(ord(character) in cmap for cmap in fonts.values())
    ]
    print(f"characters={len(characters)}")
    print(f"missing_from_all_ttc={len(missing_all)}")
    print(f"missing_characters={''.join(missing_all)}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
