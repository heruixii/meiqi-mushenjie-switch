"""List files in a PFS0 container without decrypting or modifying it."""

from __future__ import annotations

import argparse
import csv
import struct
import sys
from pathlib import Path


HEADER = struct.Struct("<4sIII")
ENTRY = struct.Struct("<QQII")


def read_c_string(table: bytes, offset: int) -> str:
    if offset >= len(table):
        raise ValueError(f"string offset outside table: {offset}")
    end = table.find(b"\0", offset)
    if end == -1:
        raise ValueError(f"unterminated string at offset: {offset}")
    return table[offset:end].decode("utf-8", errors="replace")


def read_entries(path: Path) -> list[dict[str, int | str]]:
    with path.open("rb") as handle:
        header = handle.read(HEADER.size)
        if len(header) != HEADER.size:
            raise ValueError("file is shorter than a PFS0 header")

        magic, file_count, string_table_size, _reserved = HEADER.unpack(header)
        if magic != b"PFS0":
            raise ValueError(f"unsupported magic: {magic!r}; expected b'PFS0'")

        entries = []
        for index in range(file_count):
            data = handle.read(ENTRY.size)
            if len(data) != ENTRY.size:
                raise ValueError(f"truncated PFS0 entry at index {index}")
            offset, size, name_offset, _entry_reserved = ENTRY.unpack(data)
            entries.append(
                {
                    "index": index,
                    "offset": offset,
                    "size": size,
                    "name_offset": name_offset,
                }
            )

        string_table = handle.read(string_table_size)
        if len(string_table) != string_table_size:
            raise ValueError("truncated PFS0 string table")

    data_start = HEADER.size + file_count * ENTRY.size + string_table_size
    for entry in entries:
        entry["name"] = read_c_string(string_table, int(entry["name_offset"]))
        entry["absolute_offset"] = data_start + int(entry["offset"])
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("container", type=Path, help="path to an NSZ/NSP PFS0 container")
    parser.add_argument("--csv", type=Path, help="write the inventory to a CSV file")
    args = parser.parse_args()

    try:
        entries = read_entries(args.container)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    rows = [
        {
            "index": entry["index"],
            "name": entry["name"],
            "size": entry["size"],
            "relative_offset": entry["offset"],
            "absolute_offset": entry["absolute_offset"],
        }
        for entry in entries
    ]

    print(f"container: {args.container}")
    print(f"entries: {len(rows)}")
    for row in rows:
        print(
            f"{row['index']:>3}  {row['size']:>12} bytes  "
            f"offset {row['absolute_offset']:>12}  {row['name']}"
        )

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys() if rows else ["index", "name", "size", "relative_offset", "absolute_offset"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"csv: {args.csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
