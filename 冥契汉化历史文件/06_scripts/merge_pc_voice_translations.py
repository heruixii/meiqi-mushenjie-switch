from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


VOICE = re.compile(r'voice=([A-Za-z]+_\d+)')
TEXT = re.compile(r'\][“"](.*?)[”"](?:\[ps\])?$')


def pc_dialogue(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding='utf-16').splitlines()
    result = {}
    pending = None
    for index, line in enumerate(lines):
        voice = VOICE.search(line)
        if voice:
            pending = voice.group(1)
            continue
        if pending:
            match = TEXT.search(line.strip())
            if match:
                result[pending] = match.group(1).replace('“', '「').replace('”', '」')
                pending = None
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('sheet', type=Path)
    parser.add_argument('pc_root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with args.sheet.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))
    result = []
    for scene in range(1, 15):
        pc_path = args.pc_root / f'scenario05-{scene}.ks'
        if not pc_path.exists():
            continue
        pc = pc_dialogue(pc_path)
        for row in rows:
            if row['file'] != f'Script/scenario05_{scene}.binu8':
                continue
            match = re.search(r'@v([A-Za-z]+_\d+)', row['source'])
            if not match or match.group(1) not in pc:
                continue
            if row['status'] not in ('初译完成', '术语检查'):
                continue
            translated = pc[match.group(1)]
            if translated:
                result.append({'id': row['id'], 'source': row['source'], 'current': row['translation'], 'pc_translation': translated})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['id', 'source', 'current', 'pc_translation'], delimiter='\t')
        writer.writeheader()
        writer.writerows(result)
    print(f'candidates={len(result)}')


if __name__ == '__main__':
    main()
