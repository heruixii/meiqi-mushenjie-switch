"""Safely merge PC-patch text that is not covered by voice matching.

The PC original and PC patch scripts have the same line structure.  A Switch
record is accepted only when its normalized Japanese text matches the PC
original at the same scene and occurrence, and the corresponding PC patch
line contains Chinese text. Manual override IDs and control-code mismatches
are always skipped.
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
from collections import defaultdict
from pathlib import Path

from apply_pc_voice_translations import CONTROL, manual_override_ids


JAPANESE = re.compile(r"[ぁ-んァ-ヶ一-龯]")
CHINESE = re.compile(r"[\u3400-\u9fff]")
VOICE = re.compile(r"@v[A-Za-z]+_\d+[A-Za-z0-9_]*")
QUOTED = re.compile(r"(?:「|『|“|\")(.*?)(?:」|』|”|\")(?:\[ps\])?$")
TAG = re.compile(r"\[[^\]]*\]")


def quoted_payload(line: str) -> str | None:
    match = QUOTED.search(line.strip())
    return match.group(1) if match else None


def payload(line: str) -> str | None:
    """Extract visible text while converting PC line breaks to Switch @n."""
    line = line.strip()
    if not line or line.startswith((";", "*", "[")) and quoted_payload(line) is None:
        return None
    quoted = quoted_payload(line)
    if quoted is not None:
        return quoted.replace("[r]", "@n")
    if not JAPANESE.search(line) and not CHINESE.search(line):
        return None
    line = line.replace("[r]", "@n")
    line = TAG.sub("", line)
    return line


def normalize(text: str) -> str:
    text = VOICE.sub("", text)
    text = text.replace("[r]", "@n")
    text = text.strip()
    if text[:1] in "「『“\"" and text[-1:] in "」』”\"":
        text = text[1:-1]
    text = re.sub(r"\s+", "", text)
    return text


def read_lines(path: Path, encoding: str) -> list[str]:
    if encoding == "cp932":
        return path.read_bytes().decode("cp932").splitlines()
    return path.read_text(encoding=encoding).splitlines()


def pc_map(original_root: Path, patch_root: Path) -> dict[str, dict[str, set[str]]]:
    result: dict[str, dict[str, set[str]]] = {}
    for original in sorted(original_root.glob("scenario*.ks")):
        patch = patch_root / original.name
        if not patch.is_file():
            continue
        original_lines = read_lines(original, "cp932")
        patch_lines = read_lines(patch, "utf-16")
        if len(original_lines) != len(patch_lines):
            continue
        occurrences: defaultdict[str, int] = defaultdict(int)
        scene_map: dict[str, set[str]] = defaultdict(set)
        for old, new in zip(original_lines, patch_lines):
            old_payload = payload(old)
            new_payload = payload(new)
            if old_payload is None or new_payload is None:
                continue
            key = normalize(old_payload)
            if not JAPANESE.search(key):
                continue
            occurrences[key] += 1
            if old_payload != new_payload and CHINESE.search(new_payload):
                scene_map[key].add(new_payload)
        result[original.stem.replace("-", "_", 1)] = scene_map
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sheet", type=Path)
    parser.add_argument("pc_original_root", type=Path)
    parser.add_argument("pc_patch_root", type=Path)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()

    shutil.copy2(args.sheet, args.backup)
    with args.sheet.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    project_root = args.sheet.parents[2]
    manual_ids = manual_override_ids(project_root / "06_scripts" / "apply_manual_polish.py")
    mappings = pc_map(args.pc_original_root, args.pc_patch_root)
    changed = 0
    skipped_controls = 0
    skipped_ambiguous = 0

    for row in rows:
        match = re.fullmatch(r"Script/(scenario\d+b?_\d+)\.binu8", row["file"])
        if not match or not JAPANESE.search(row["source"]):
            continue
        scene = match.group(1)
        source_key = normalize(row["source"])
        if row["status"] not in ("初译完成", "术语检查"):
            continue
        if row["id"] in manual_ids or "@v" in row["source"]:
            continue
        candidates = mappings.get(scene, {}).get(source_key, set())
        if len(candidates) != 1:
            continue
        translated = next(iter(candidates))

        if row["source"].lstrip().startswith(("「", "『", "“", '"')):
            candidate = f"「{translated}」"
        else:
            candidate = translated
        candidate_controls = CONTROL.findall(candidate)
        if row.get("control_codes", "").split() != candidate_controls:
            skipped_controls += 1
            continue
        row["translation"] = candidate
        row["status"] = "PC版替换待抽检"
        row["notes"] = "来自电脑端汉化补丁；按场景、PC原文及出现次序安全对齐，待抽样复核"
        changed += 1

    with args.sheet.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"pc_full_replaced={changed}")
    print(f"control_skipped={skipped_controls}")
    print(f"scene_maps={len(mappings)}")


if __name__ == "__main__":
    main()
