from __future__ import annotations

import argparse
import ast
import csv
import re
import shutil
from pathlib import Path


VOICE = re.compile(r'@v([A-Za-z]+_\d+[A-Za-z]*(?:_[A-Za-z0-9]+)?)')
TEXT = re.compile(r'\][「“"](.*?)[」”"](?:\[ps\])?$')
HTEXT = re.compile(r'^\[htext\s+text="(.*)"\]$')
PLAIN = re.compile(r'\](.*?)(?:\[ps\])$')
CONTROL = re.compile(r'@[A-Za-z]+(?:_[A-Za-z0-9]+)*')


def manual_override_ids(path: Path) -> set[str]:
    """Read override keys without importing the script or changing the sheet."""
    if not path.is_file():
        return set()
    tree = ast.parse(path.read_text(encoding='utf-8'))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name)
            and target.value.id == 'OVERRIDES'
            for target in node.targets
        ):
            try:
                result.add(ast.literal_eval(node.targets[0].slice))
            except (ValueError, TypeError):
                pass
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == 'update'
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.value.id == 'OVERRIDES'
        ):
            try:
                result.update(ast.literal_eval(node.value.args[0]).keys())
            except (ValueError, TypeError):
                pass
    return result


def read_pc(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding='utf-16').splitlines()
    result = {}
    pending = None
    for line in lines:
        found = re.search(r'voice=([A-Za-z]+_\d+)', line)
        if found:
            pending = found.group(1)
            continue
        if pending:
            stripped = line.strip()
            match = TEXT.search(stripped) or HTEXT.match(stripped) or PLAIN.search(stripped)
            if match:
                result[pending.lower()] = match.group(1)
                pending = None
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('sheet', type=Path)
    parser.add_argument('pc_root', type=Path)
    parser.add_argument('backup', type=Path)
    args = parser.parse_args()
    shutil.copy2(args.sheet, args.backup)
    with args.sheet.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))
    project_root = args.sheet.parents[2]
    manual_ids = manual_override_ids(project_root / '06_scripts' / 'apply_manual_polish.py')
    pc_by_scene = {}
    # PC patch contains all numbered routes, not only scenario 05.
    for path in args.pc_root.glob('scenario*.ks'):
        match = re.fullmatch(r'(scenario\d+b?)\-(\d+)', path.stem)
        if match:
            pc_by_scene[f'{match.group(1)}_{match.group(2)}'] = read_pc(path)
    changed = 0
    skipped_complex = 0
    for row in rows:
        if row['status'] not in ('初译完成', '术语检查'):
            continue
        if row['id'] in manual_ids:
            continue
        match = re.match(r'Script/(scenario\d+b?)_(\d+)\.binu8$', row['file'])
        voice = VOICE.search(row['source'])
        if not match or not voice:
            continue
        scene = f'{match.group(1)}_{match.group(2)}'
        voice_map = pc_by_scene.get(scene, {})
        voice_key = voice.group(1).lower()
        translated = voice_map.get(voice_key)
        if not translated:
            # Switch adds route/variant suffixes such as _a, _b, and _cs;
            # PC uses the shared base voice number for these lines.
            base_key = re.sub(r'(?:_[a-z0-9]+|[a-z]+)$', '', voice_key)
            translated = voice_map.get(base_key)
        if not translated:
            continue
        controls = row.get('control_codes', '').split()
        candidate = f'{voice.group(0)}「{translated}」'
        candidate_controls = CONTROL.findall(candidate)
        if controls != candidate_controls:
            skipped_complex += 1
            continue
        row['translation'] = candidate
        row['status'] = 'PC版替换待抽检'
        row['notes'] = '来自电脑端汉化补丁；按语音编号对齐，待抽样复核'
        changed += 1
    with args.sheet.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    print(f'pc_voice_replaced={changed}')
    print(f'complex_skipped={skipped_complex}')


if __name__ == '__main__':
    main()
