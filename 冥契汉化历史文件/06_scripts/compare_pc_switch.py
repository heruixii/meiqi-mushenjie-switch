from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


VISIBLE = re.compile(r'[ぁ-んァ-ン一-龯]')
CHINESE = re.compile(r'[\u3400-\u9fff]')


def pc_lines(path: Path) -> list[str]:
    text = path.read_text(encoding='utf-16')
    result = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(('*', '[', ';')):
            continue
        if CHINESE.search(line) and not line.startswith(('[', '*', ';')):
            result.append(line)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('switch_sheet', type=Path)
    parser.add_argument('pc_root', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    with args.switch_sheet.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))
    output = []
    for number in range(1, 13):
        switch_rows = [
            row for row in rows
            if row['file'] == f'Script/scenario05_{number}.binu8'
            and VISIBLE.search(row['source'])
            and '@関数内ローカル変数' not in row['source']
        ]
        pc_path = args.pc_root / f'scenario05-{number}.ks'
        pc = pc_lines(pc_path) if pc_path.exists() else []
        output.append({'scene': f'05_{number}', 'switch_visible': len(switch_rows), 'pc_visible': len(pc), 'difference': len(pc) - len(switch_rows)})
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['scene', 'switch_visible', 'pc_visible', 'difference'], delimiter='\t')
        writer.writeheader()
        writer.writerows(output)
    print(f'reported={len(output)}')


if __name__ == '__main__':
    main()
