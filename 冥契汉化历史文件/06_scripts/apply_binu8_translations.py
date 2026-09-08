"""Apply selected BINU8 translations into a LayeredFS-style output tree."""

from __future__ import annotations

import argparse
import csv
import re
import struct
from pathlib import Path


CONTROL_CODE = re.compile(r"@[A-Za-z][A-Za-z0-9_]*")


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_record(data: bytes | bytearray, row: dict[str, str]) -> tuple[int, int, str]:
    """Read and validate one length-prefixed string using the sheet coordinates."""
    length_offset = int(row["length_offset"])
    if length_offset < 0 or length_offset + 4 > len(data):
        raise ValueError(f"length offset out of range at {row['file']}:{length_offset}")
    stored_length = struct.unpack_from("<I", data, length_offset)[0]
    text_start = length_offset + 4
    text_end = text_start + stored_length
    if text_end > len(data) or stored_length < 2 or data[text_end - 1] != 0:
        raise ValueError(f"invalid string record at {row['file']}:{length_offset}")
    try:
        original = bytes(data[text_start : text_end - 1]).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"invalid UTF-8 record at {row['file']}:{length_offset}"
        ) from exc
    if original != row["source"]:
        raise ValueError(
            f"source mismatch at {row['file']}:{length_offset}: "
            f"expected {row['source']!r}, found {original!r}"
        )
    expected_length = row.get("stored_length")
    if expected_length and int(expected_length) != stored_length:
        raise ValueError(
            f"stored length mismatch at {row['file']}:{length_offset}: "
            f"sheet={expected_length}, file={stored_length}"
        )
    expected_byte_length = row.get("byte_length")
    if expected_byte_length and int(expected_byte_length) != stored_length - 1:
        raise ValueError(
            f"byte length mismatch at {row['file']}:{length_offset}: "
            f"sheet={expected_byte_length}, file={stored_length - 1}"
        )
    return text_start, text_end, original


def validate_replacement(original: str, translation: str, row: dict[str, str]) -> bytes:
    if "\x00" in translation:
        raise ValueError(f"NUL in translation at {row['file']}:{row['length_offset']}")
    if CONTROL_CODE.findall(original) != CONTROL_CODE.findall(translation):
        raise ValueError(
            f"control-code mismatch at {row['file']}:{row['length_offset']}: "
            f"{CONTROL_CODE.findall(original)!r} != {CONTROL_CODE.findall(translation)!r}"
        )
    encoded = translation.encode("utf-8")
    return struct.pack("<I", len(encoded) + 1) + encoded + b"\0"


def apply_file(source: Path, target: Path, rows: list[dict[str, str]], root: Path) -> int:
    source_data = source.read_bytes()
    data = bytearray(source_data)
    edits: list[tuple[int, int, bytes, str]] = []
    seen_offsets: set[int] = set()
    for row in rows:
        translation = row.get("translation", "")
        if not translation:
            continue
        length_offset = int(row["length_offset"])
        if length_offset in seen_offsets:
            raise ValueError(f"duplicate length offset at {row['file']}:{length_offset}")
        seen_offsets.add(length_offset)
        text_start, text_end, original = read_record(source_data, row)
        replacement = validate_replacement(original, translation, row)
        edits.append((length_offset, text_end, replacement, translation))

    previous_end = len(data) + 1
    for start, end, replacement, _translation in sorted(edits, reverse=True):
        if end > previous_end:
            raise ValueError(f"overlapping string records in {source}")
        data[start:end] = replacement
        previous_end = start

    if len(data) == 0:
        raise ValueError(f"empty output after applying translations to {source}")
    # Earlier replacements shift later records, so verify using each record's
    # post-write offset rather than its original sheet offset.
    for length_offset, text_end, _replacement, translation in edits:
        shift = sum(
            len(other_replacement) - (other_end - other_start)
            for other_start, other_end, other_replacement, _other_translation in edits
            if other_start < length_offset
        )
        new_length_offset = length_offset + shift
        if new_length_offset < 0 or new_length_offset + 4 > len(data):
            raise ValueError(f"post-write offset out of range at {length_offset}")
        stored_length = struct.unpack_from("<I", data, new_length_offset)[0]
        new_text_start = new_length_offset + 4
        new_text_end = new_text_start + stored_length
        if new_text_end > len(data) or stored_length < 2 or data[new_text_end - 1] != 0:
            raise ValueError(f"post-write record invalid at {length_offset}")
        actual = bytes(data[new_text_start : new_text_end - 1]).decode("utf-8")
        if actual != translation:
            raise ValueError(f"post-write verification failed at {length_offset}")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return len(edits)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("romfs", type=Path)
    parser.add_argument("translations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.romfs.resolve()
    rows = [row for row in load_rows(args.translations) if row.get("translation", "")]
    by_file: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_file.setdefault(row["file"], []).append(row)

    total = 0
    for relative, file_rows in by_file.items():
        source = root / Path(relative)
        target = args.output / Path(relative)
        if not source.is_file():
            raise FileNotFoundError(source)
        total += apply_file(source, target, file_rows, root)

    print(f"files_written={len(by_file)}")
    print(f"strings_written={total}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
