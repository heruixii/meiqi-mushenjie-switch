"""Audit FNT glyph tables and TTC coverage for the extracted RomFS."""

from __future__ import annotations

import argparse
import csv
import struct
import zlib
from pathlib import Path


FNT_HEADER = struct.Struct("<4s4I")
FNT_RECORD = struct.Struct("<hhHHI")


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def i16(data: bytes, offset: int) -> int:
    return struct.unpack_from(">h", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def fnt_summary(path: Path) -> dict[str, int | str]:
    data = path.read_bytes()
    if len(data) < 8 or data[:4] != b"FNT\0":
        raise ValueError(f"unsupported FNT header: {path}")
    if data[4:8] == b"DATA":
        return {
            "file": path.name,
            "kind": "special-FNT-DATA",
            "file_size": len(data),
        }
    if len(data) < FNT_HEADER.size:
        raise ValueError(f"truncated FNT header: {path}")
    _magic, width, height, metadata_size, compressed_size = FNT_HEADER.unpack_from(data)
    compressed_start = FNT_HEADER.size
    compressed_end = compressed_start + compressed_size
    metadata = zlib.decompress(data[compressed_start:compressed_end])
    if len(metadata) != metadata_size or len(metadata) % FNT_RECORD.size:
        raise ValueError(f"unexpected metadata size: {path}")
    glyph_data = data[compressed_end:]
    records = [
        FNT_RECORD.unpack_from(metadata, offset)
        for offset in range(0, len(metadata), FNT_RECORD.size)
    ]
    invalid = 0
    size_mismatch = 0
    fallback = 0
    nonzero_offsets = sorted({record[4] for record in records if record[2] and record[3]})
    for index, (x, y, glyph_width, glyph_height, offset) in enumerate(records):
        if glyph_width == 0 or glyph_height == 0:
            continue
        if offset > len(glyph_data):
            invalid += 1
            continue
        next_offsets = [value for value in nonzero_offsets if value > offset]
        next_offset = next_offsets[0] if next_offsets else len(glyph_data)
        if next_offset < offset or next_offset > len(glyph_data):
            invalid += 1
            continue
        if next_offset - offset != glyph_width * glyph_height * 2:
            size_mismatch += 1
        if (x, y, glyph_width, glyph_height) in {
            (7, 8, 12, 9),
            (13, 13, 9, 8),
            (5, 5, 8, 7),
        }:
            fallback += 1
    return {
        "file": path.name,
        "width": width,
        "height": height,
        "metadata_size": metadata_size,
        "compressed_size": compressed_size,
        "glyph_data_size": len(glyph_data),
        "records": len(records),
        "invalid_offsets": invalid,
        "bitmap_size_mismatches": size_mismatch,
        "fallback_like_records": fallback,
    }


def sfnt_tables(data: bytes, font_offset: int = 24) -> dict[str, tuple[int, int]]:
    table_count = u16(data, font_offset + 4)
    result = {}
    for index in range(table_count):
        offset = font_offset + 12 + 16 * index
        tag = data[offset : offset + 4].decode("ascii")
        result[tag] = (u32(data, offset + 8), u32(data, offset + 12))
    return result


def cmap_format4(data: bytes, cmap_offset: int) -> dict[int, int]:
    segments = u16(data, cmap_offset + 6) // 2
    end_offset = cmap_offset + 14
    start_offset = end_offset + 2 * segments + 2
    delta_offset = start_offset + 2 * segments
    range_offset = delta_offset + 2 * segments
    result: dict[int, int] = {}
    for segment in range(segments):
        start = u16(data, start_offset + 2 * segment)
        end = u16(data, end_offset + 2 * segment)
        delta = i16(data, delta_offset + 2 * segment)
        range_value = u16(data, range_offset + 2 * segment)
        for codepoint in range(start, end + 1):
            if range_value == 0:
                glyph = (codepoint + delta) & 0xFFFF
            else:
                glyph_address = range_offset + 2 * segment + range_value + 2 * (codepoint - start)
                glyph = u16(data, glyph_address) if glyph_address + 2 <= len(data) else 0
                if glyph:
                    glyph = (glyph + delta) & 0xFFFF
            if glyph:
                result[codepoint] = glyph
    return result


def ttc_cmap(path: Path) -> dict[int, int]:
    data = path.read_bytes()
    if data[:4] != b"ttcf":
        raise ValueError(f"unsupported TTC header: {path}")
    font_offset = u32(data, 12)
    tables = sfnt_tables(data, font_offset)
    cmap_offset, _size = tables["cmap"]
    encoding_count = u16(data, cmap_offset + 2)
    for index in range(encoding_count):
        record = cmap_offset + 4 + 8 * index
        platform, encoding, subtable_offset = struct.unpack_from(">HHI", data, record)
        if platform == 3 and encoding == 1:
            subtable = cmap_offset + subtable_offset
            if u16(data, subtable) == 4:
                return cmap_format4(data, subtable)
    raise ValueError(f"no Windows format-4 cmap in {path}")


def game_characters(sheet: Path) -> set[str]:
    """Collect characters from both source and translated text columns."""
    characters: set[str] = set()
    with sheet.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            for field in ("text", "source", "translation"):
                characters.update(row.get(field, ""))
    return characters


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("romfs", type=Path)
    parser.add_argument("--sheet", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows: list[dict[str, int | str]] = []
    system = args.romfs / "System"
    for path in sorted(system.glob("*.fnt")):
        rows.append(fnt_summary(path))

    characters = game_characters(args.sheet) if args.sheet else set()
    for path in sorted(system.glob("*.ttc")):
        cmap = ttc_cmap(path)
        covered = sum(ord(char) in cmap for char in characters)
        rows.append(
            {
                "file": path.name,
                "kind": "ttc",
                "mapped_codepoints": len(cmap),
                "game_characters": len(characters),
                "game_characters_covered": covered,
                "game_characters_missing": len(characters) - covered,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"fonts_scanned={len(rows)}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
