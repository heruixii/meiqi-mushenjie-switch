"""Apply PC text to the first Switch text record after matching voice markers.

Switch stores voice markers and visible text in separate records. The PC patch
stores the same marker followed by one or more htext records. A replacement is
made only when the marker, scene, and next visible text record are unique.
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
from pathlib import Path

VOICE = re.compile(r"voice=([A-Za-z]+_\d+)")
HTEXT = re.compile(r'^\[htext\s+text="(.*)"\]$')
QUOTED = re.compile(r'](?:[“"])(.*?)(?:[”"])(?:\[ps\])?$')
MARKER = re.compile(r"^[A-Za-z]+_\d+$")


def pc_blocks(root: Path) -> dict[tuple[str, str], str]:
    result = {}
    for path in root.glob("scenario*.ks"):
        scene = path.stem.replace("-", "_", 1)
        lines = path.read_text(encoding="utf-16").splitlines()
        for i, line in enumerate(lines):
            match = VOICE.search(line)
            if not match:
                continue
            parts = []
            for following in lines[i + 1 :]:
                if following.strip() == "":
                    break
                text = HTEXT.match(following.strip()) or QUOTED.search(following.strip())
                if not text:
                    break
                parts.append(text.group(1).replace('\\"', '"'))
            if parts:
                result[(scene, match.group(1).lower())] = "@n".join(parts)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sheet", type=Path)
    parser.add_argument("pc_root", type=Path)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    shutil.copy2(args.sheet, args.backup)
    with args.sheet.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    pc = pc_blocks(args.pc_root)
    replaced = skipped = 0
    for i, row in enumerate(rows):
        if not MARKER.fullmatch(row["source"].strip()):
            continue
        match = re.fullmatch(r"Script/(scenario\d+b?)_(\d+)\.binu8", row["file"])
        if not match:
            continue
        key = (f"{match.group(1)}_{match.group(2)}", row["source"].strip().lower())
        translated = pc.get(key)
        if not translated:
            continue
        target = None
        for following in rows[i + 1 :]:
            if following["file"] != row["file"] or MARKER.fullmatch(following["source"].strip()):
                break
            if following["source"].strip():
                target = following
                break
        if target is None or target["status"] not in ("初译完成", "术语检查") or not re.search(r"[ぁ-んァ-ヶ一-龯]", target["source"]):
            skipped += 1
            continue
        target["translation"] = translated
        target["status"] = "PC版替换待抽检"
        target["notes"] = "来自电脑端汉化补丁；按语音标记与场景区块对齐，待抽样复核"
        replaced += 1
    with args.sheet.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"pc_block_replaced={replaced}")
    print(f"pc_block_skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
