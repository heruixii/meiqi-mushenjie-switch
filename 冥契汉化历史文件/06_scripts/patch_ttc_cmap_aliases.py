"""Add simplified-character aliases to the game's embedded TTC fonts."""

from __future__ import annotations

import argparse
import csv
import struct
from pathlib import Path

from opencc import OpenCC


U16 = struct.Struct(">H")
U16S = struct.Struct(">h")
U32 = struct.Struct(">I")


def collect_translation_characters(sheet: Path) -> set[str]:
    characters: set[str] = set()
    with sheet.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            characters.update(row.get("translation", ""))
    return characters


def table_records(data: bytes, font_offset: int) -> list[tuple[bytes, int, int]]:
    table_count = U16.unpack_from(data, font_offset + 4)[0]
    records = []
    for index in range(table_count):
        record_offset = font_offset + 12 + 16 * index
        tag = data[record_offset : record_offset + 4]
        offset = U32.unpack_from(data, record_offset + 8)[0]
        length = U32.unpack_from(data, record_offset + 12)[0]
        records.append((tag, offset, length))
    return records


def ttc_font_offsets(data: bytes) -> tuple[int, ...]:
    if data[:4] != b"ttcf":
        raise ValueError("not a TTC file")
    count = U32.unpack_from(data, 8)[0]
    return struct.unpack_from(">" + "I" * count, data, 12)


def format4_offset(data: bytes, font_offset: int) -> tuple[int, int]:
    cmap_offset = next(
        offset for tag, offset, _length in table_records(data, font_offset) if tag == b"cmap"
    )
    encoding_count = U16.unpack_from(data, cmap_offset + 2)[0]
    for index in range(encoding_count):
        record = cmap_offset + 4 + 8 * index
        platform, encoding, relative = struct.unpack_from(">HHI", data, record)
        subtable = cmap_offset + relative
        if platform == 3 and encoding == 1 and U16.unpack_from(data, subtable)[0] == 4:
            return subtable, U16.unpack_from(data, subtable + 2)[0]
    raise ValueError("no Windows format-4 cmap")


def format4_segments(data: bytes, subtable: int) -> list[tuple[int, int, int, int, int]]:
    segment_count = U16.unpack_from(data, subtable + 6)[0] // 2
    end_base = subtable + 14
    start_base = end_base + 2 * segment_count + 2
    delta_base = start_base + 2 * segment_count
    range_base = delta_base + 2 * segment_count
    segments = []
    for index in range(segment_count):
        end = U16.unpack_from(data, end_base + 2 * index)[0]
        start = U16.unpack_from(data, start_base + 2 * index)[0]
        delta = U16S.unpack_from(data, delta_base + 2 * index)[0]
        range_offset = U16.unpack_from(data, range_base + 2 * index)[0]
        segments.append((start, end, delta, range_offset, range_base + 2 * index))
    return segments


def cmap_mapping(data: bytes, subtable: int) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for start, end, delta, range_offset, range_address in format4_segments(data, subtable):
        if start > end or start == 0xFFFF:
            continue
        for codepoint in range(start, end + 1):
            if range_offset == 0:
                glyph = (codepoint + delta) & 0xFFFF
            else:
                glyph_address = range_address + range_offset + 2 * (codepoint - start)
                if glyph_address + 2 > len(data):
                    raise ValueError("cmap glyph array points outside the file")
                raw_glyph = U16.unpack_from(data, glyph_address)[0]
                glyph = (raw_glyph + delta) & 0xFFFF if raw_glyph else 0
            if glyph:
                mapping[codepoint] = glyph
    return mapping


def build_format4(mapping: dict[int, int]) -> bytes:
    """Build a compact format-4 table from a BMP codepoint-to-glyph map."""
    codepoints = sorted(codepoint for codepoint in mapping if codepoint <= 0xFFFF)
    spans: list[tuple[int, int, int, list[int] | None]] = []
    cursor = 0
    while cursor < len(codepoints):
        start = codepoints[cursor]
        end = start
        while cursor + 1 < len(codepoints) and codepoints[cursor + 1] == end + 1:
            cursor += 1
            end = codepoints[cursor]
        run = list(range(start, end + 1))
        deltas = [(mapping[codepoint] - codepoint) & 0xFFFF for codepoint in run]
        # Long arithmetic runs are cheaper as delta segments. Short runs are
        # kept in an array segment so that fonts with many irregular CJK
        # mappings do not exceed the original table's reserved size.
        position = 0
        while position < len(run):
            delta = deltas[position]
            finish = position + 1
            while finish < len(run) and deltas[finish] == delta:
                finish += 1
            if finish - position >= 4:
                signed_delta = delta if delta < 0x8000 else delta - 0x10000
                spans.append((run[position], run[finish - 1], signed_delta, None))
                position = finish
                continue
            variable_start = position
            position = finish
            while position < len(run):
                next_delta = deltas[position]
                next_finish = position + 1
                while next_finish < len(run) and deltas[next_finish] == next_delta:
                    next_finish += 1
                if next_finish - position >= 4:
                    break
                position = next_finish
            spans.append(
                (
                    run[variable_start],
                    run[position - 1],
                    0,
                    [mapping[codepoint] for codepoint in run[variable_start:position]],
                )
            )
        cursor += 1

    spans.append((0xFFFF, 0xFFFF, 1, None))
    segment_count = len(spans)
    end_codes = [span[1] for span in spans]
    start_codes = [span[0] for span in spans]
    deltas = [span[2] for span in spans]
    range_offsets: list[int] = []
    glyph_array: list[int] = []
    header_size = 16 + 8 * segment_count
    for index, (_start, _end, _delta, glyphs) in enumerate(spans):
        if glyphs is None:
            range_offsets.append(0)
            continue
        range_address = 16 + 6 * segment_count + 2 * index
        array_address = header_size + 2 * len(glyph_array)
        range_offsets.append(array_address - range_address)
        glyph_array.extend(glyphs)

    body = bytearray()
    body += struct.pack(">HHHHHHH", 4, 0, 0, segment_count * 2, 0, 0, 0)
    body += struct.pack(">" + "H" * segment_count, *end_codes)
    body += struct.pack(">H", 0)
    body += struct.pack(">" + "H" * segment_count, *start_codes)
    body += struct.pack(">" + "h" * segment_count, *deltas)
    body += struct.pack(">" + "H" * segment_count, *range_offsets)
    if glyph_array:
        body += struct.pack(">" + "H" * len(glyph_array), *glyph_array)
    if len(body) > 0xFFFF:
        raise ValueError(f"format-4 cmap is too large: {len(body)} bytes")
    struct.pack_into(">H", body, 2, len(body))
    struct.pack_into(">H", body, 4, 0)
    return bytes(body)


def checksum(data: bytes) -> int:
    padded = data + b"\0" * ((-len(data)) % 4)
    return sum(struct.unpack(">" + "I" * (len(padded) // 4), padded)) & 0xFFFFFFFF


def build_cmap(original: bytes, format4: bytes) -> bytes:
    """Keep the original Mac format-6 subtable and replace Windows format-4."""
    mac = original[20 : 20 + U16.unpack_from(original, 22)[0]]
    header = struct.pack(">HHHHIHHI", 0, 2, 1, 0, 20, 3, 1, 20 + len(mac))
    return header + mac + format4


def build_face(data: bytes, font_offset: int, cmap: bytes) -> bytes:
    records = table_records(data, font_offset)
    table_data = {
        tag: data[offset : offset + length]
        for tag, offset, length in records
    }
    table_data[b"cmap"] = cmap
    header = data[font_offset : font_offset + 12]
    directory_size = 12 + 16 * len(records)
    offsets: dict[bytes, int] = {}
    cursor = directory_size
    for tag, _offset, _length in records:
        cursor = (cursor + 3) & ~3
        offsets[tag] = cursor
        cursor += len(table_data[tag])

    face = bytearray(cursor)
    face[:12] = header
    head_data = bytearray(table_data[b"head"])
    struct.pack_into(">I", head_data, 8, 0)
    table_data[b"head"] = bytes(head_data)
    for index, (tag, _offset, _length) in enumerate(records):
        record_offset = 12 + 16 * index
        face[record_offset : record_offset + 4] = tag
        struct.pack_into(">I", face, record_offset + 4, checksum(table_data[tag]))
        struct.pack_into(">I", face, record_offset + 8, offsets[tag])
        struct.pack_into(">I", face, record_offset + 12, len(table_data[tag]))
        face[offsets[tag] : offsets[tag] + len(table_data[tag])] = table_data[tag]

    head_offset = offsets[b"head"]
    adjustment = (0xB1B0AFBA - checksum(bytes(face))) & 0xFFFFFFFF
    struct.pack_into(">I", face, head_offset + 8, adjustment)
    return bytes(face)


def aliases_for_missing(
    characters: set[str], mapping: dict[int, int]
) -> dict[str, tuple[str, int]]:
    converter = OpenCC("s2t")
    fallbacks = {"—": "―"}
    aliases: dict[str, tuple[str, int]] = {}
    for character in sorted(characters, key=ord):
        codepoint = ord(character)
        if codepoint in mapping:
            continue
        target = fallbacks.get(character, converter.convert(character))
        if len(target) != 1 or ord(target) not in mapping:
            continue
        aliases[character] = (target, mapping[ord(target)])
    return aliases


def patch_font(path: Path, characters: set[str]) -> tuple[int, list[str]]:
    data = path.read_bytes()
    mappings: list[dict[int, int]] = []
    original_cmaps: list[bytes] = []
    for font_offset in ttc_font_offsets(data):
        records = table_records(data, font_offset)
        cmap_offset, cmap_length = next(
            (offset, length)
            for tag, offset, length in records
            if tag == b"cmap"
        )
        subtable, _length = format4_offset(data, font_offset)
        mapping = cmap_mapping(data, subtable)
        mappings.append(mapping)
        original_cmaps.append(data[cmap_offset : cmap_offset + cmap_length])

    aliases = aliases_for_missing(characters, mappings[0])
    unresolved = sorted(
        set(characters)
        - set(chr(codepoint) for codepoint in mappings[0])
        - set(aliases),
        key=ord,
    )
    for mapping in mappings:
        for character, (target, _target_glyph) in aliases.items():
            mapping[ord(character)] = mapping[ord(target)]

    faces = []
    for font_offset, mapping, original_cmap in zip(
        ttc_font_offsets(data), mappings, original_cmaps
    ):
        replacement = build_format4(mapping)
        faces.append(build_face(data, font_offset, build_cmap(original_cmap, replacement)))

    header_size = 12 + 4 * len(faces)
    offsets = []
    cursor = header_size
    for face in faces:
        cursor = (cursor + 3) & ~3
        offsets.append(cursor)
        cursor += len(face)
    output = bytearray(cursor)
    output[:4] = b"ttcf"
    struct.pack_into(">III", output, 4, 0x00010000, len(faces), *offsets[:1])
    for index, offset in enumerate(offsets):
        struct.pack_into(">I", output, 12 + 4 * index, offset)
    for offset, face in zip(offsets, faces):
        adjusted = bytearray(face)
        table_count = U16.unpack_from(adjusted, 4)[0]
        head_relative = None
        for index in range(table_count):
            record_offset = 12 + 16 * index
            tag = adjusted[record_offset : record_offset + 4]
            relative = U32.unpack_from(adjusted, record_offset + 8)[0]
            struct.pack_into(">I", adjusted, record_offset + 8, offset + relative)
            if tag == b"head":
                head_relative = relative
        if head_relative is not None:
            struct.pack_into(">I", adjusted, head_relative + 8, 0)
            adjustment = (0xB1B0AFBA - checksum(bytes(adjusted))) & 0xFFFFFFFF
            struct.pack_into(">I", adjusted, head_relative + 8, adjustment)
        output[offset : offset + len(adjusted)] = adjusted

    path.write_bytes(output)
    return len(aliases), unresolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("system", type=Path)
    parser.add_argument("sheet", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    characters = collect_translation_characters(args.sheet)
    args.output.mkdir(parents=True, exist_ok=True)
    total = 0
    for source in sorted(args.system.glob("*.ttc")):
        target = args.output / source.name
        target.write_bytes(source.read_bytes())
        patched, unresolved = patch_font(target, characters)
        total += patched
        print(f"{source.name}: aliases={patched} unresolved={''.join(unresolved)}")
    print(f"translation_characters={len(characters)}")
    print(f"aliases_written={total}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
