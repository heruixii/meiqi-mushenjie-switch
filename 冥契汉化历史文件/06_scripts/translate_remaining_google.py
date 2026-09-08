"""Create translation batches for visible untranslated Japanese strings.

This is an initial-pass helper only. It protects BINU8 control codes and
resource identifiers, and emits a TSV batch that still needs human review.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError


CONTROL_RE = re.compile(r"@[A-Za-z][A-Za-z0-9_]*")
JAPANESE_RE = re.compile(r"[ぁ-んァ-ヶ一-龯々〆ヵ]")
INTERNAL_RE = re.compile(
    r"関数内ローカル変数|^v[A-Za-z0-9 ]+ @|^x @|^y @|^A$|^EventMode$|"
    r"^scenario|\.png$|\.spm$|^evt @|^sel :|^bank\(|^i :|^n[A-Za-z]+ :|"
    r"^System\.dat$|^EventGroup\.dat$|^Title\.bin$"
)
SKIP_FILES = {"Config/stand.datu8"}

NAME_MAP = {
    "瀬和 環": "濑和环",
    "瀬和環": "濑和环",
    "倉科 双葉": "仓科双叶",
    "倉科双葉": "仓科双叶",
    "椎名 朧": "椎名胧",
    "椎名朧": "椎名胧",
    "白坂 ハナ": "白坂花",
    "白坂ハナ": "白坂花",
    "架橋 琥珀": "架桥琥珀",
    "架橋琥珀": "架桥琥珀",
    "匂宮 めぐり": "匂宫巡",
    "匂宮めぐり": "匂宫巡",
    "箱鳥 理世": "箱鸟理世",
    "箱鳥理世": "箱鸟理世",
    "天使 奈々菜": "天使奈奈菜",
    "天使奈々菜": "天使奈奈菜",
    "龍木 悠苑": "龙木悠苑",
    "龍木悠苑": "龙木悠苑",
    "天樂 来々": "天乐来来",
    "天楽 来々": "天乐来来",
    "天樂来々": "天乐来来",
    "天楽来々": "天乐来来",
    "折原 氷狐": "折原冰狐",
    "折原氷狐": "折原冰狐",
    "瀬和 未来": "濑和未来",
    "瀬和未来": "濑和未来",
    "折原 京子": "折原京子",
    "折原京子": "折原京子",
    "匂宮 王海": "匂宫王海",
    "匂宮王海": "匂宫王海",
    "天使 美嘉": "天使美嘉",
    "天使美嘉": "天使美嘉",
}


def visible(row: dict[str, str]) -> bool:
    source = row.get("source", "")
    file_name = row.get("file", "")
    if row.get("translation", "").strip() or not source.strip():
        return False
    if file_name in SKIP_FILES or not JAPANESE_RE.search(source):
        return False
    if INTERNAL_RE.search(source):
        return False
    return file_name.startswith("Script/") or file_name.startswith("Config/")


def protect(source: str) -> tuple[str, dict[str, str]]:
    protected: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        token = f" ZXQCTRL{len(protected)}ZXQ "
        protected[token.strip()] = match.group(0)
        return token

    text = CONTROL_RE.sub(replace, source)
    for japanese, chinese in sorted(NAME_MAP.items(), key=lambda item: -len(item[0])):
        text = text.replace(japanese, chinese)
    return text, protected


def translate_google(text: str) -> str:
    query = quote(text, safe="")
    url = (
        "https://translate.googleapis.com/translate_a/single?client=gtx"
        f"&sl=ja&tl=zh-CN&dt=t&q={query}"
    )
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return "".join(part[0] for part in payload[0] if part and part[0])
        except HTTPError as error:
            if error.code == 429:
                time.sleep(15 * (attempt + 1))
            elif attempt == 3:
                raise
            else:
                time.sleep(1.5 * (attempt + 1))
        except Exception:
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


def translate_mymemory(text: str) -> str:
    query = quote(text, safe="")
    url = f"https://api.mymemory.translated.net/get?q={query}&langpair=ja|zh-CN"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("quotaFinished"):
                raise RuntimeError("MyMemory quota finished")
            result = payload.get("responseData", {}).get("translatedText", "")
            if not result:
                raise ValueError("empty MyMemory translation")
            return result
        except HTTPError as error:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def translate_argos(text: str) -> str:
    from argostranslate import translate as argos_translate

    # The installed offline packages provide ja<->en and en<->zh, not ja->zh.
    english = argos_translate.translate(text, "ja", "en")
    return argos_translate.translate(english, "en", "zh")


def translate_argos_preserving_controls(text: str) -> str:
    output: list[str] = []
    cursor = 0
    for match in CONTROL_RE.finditer(text):
        segment = text[cursor : match.start()]
        if segment.strip():
            output.append(translate_argos(segment))
        else:
            output.append(segment)
        output.append(match.group(0))
        cursor = match.end()
    tail = text[cursor:]
    if tail.strip():
        output.append(translate_argos(tail))
    else:
        output.append(tail)
    return "".join(output)


def translate(text: str, backend: str) -> str:
    if backend == "mymemory":
        return translate_mymemory(text)
    if backend == "argos":
        return translate_argos(text)
    return translate_google(text)


def restore(text: str, protected: dict[str, str]) -> str:
    for marker, token in protected.items():
        text = text.replace(marker, token)
    return text


ROW_MARKER_RE = re.compile(r"ZXQROW\s*(\d+)\s*ZXQ")


def translate_group(items: Sequence[tuple[str, dict[str, str]]], backend: str) -> list[str]:
    if backend == "argos":
        return [
            (
                translate_argos_preserving_controls(restore(text, protected))
                or restore(text, protected)
            )
            for text, protected in items
        ]
    marker_text = "\n".join(
        f"ZXQROW{number:03d}ZXQ\n{text}" for number, (text, _protected) in enumerate(items)
    )
    translated = translate(marker_text, backend)
    matches = list(ROW_MARKER_RE.finditer(translated))
    if len(matches) != len(items):
        raise ValueError(
            f"group marker mismatch: expected {len(items)}, got {len(matches)}"
        )
    result: list[str] = []
    for number, match in enumerate(matches):
        if int(match.group(1)) != number:
            raise ValueError("group marker order changed")
        end = matches[number + 1].start() if number + 1 < len(matches) else len(translated)
        result.append(translated[match.end() : end].strip())
    return [restore(text, protected) for text, (_source, protected) in zip(result, items)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("master", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--file-regex", default="")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--group-size", type=int, default=8)
    parser.add_argument("--group-chars", type=int, default=0)
    parser.add_argument("--backend", choices=("google", "mymemory", "argos"), default="google")
    args = parser.parse_args()

    # Load Argos resources once before worker threads start.  Concurrent first
    # loads can race on Stanza's resource cache on Windows.
    if args.backend == "argos":
        from argostranslate import translate as _argos_translate
        _argos_translate.translate("", "ja", "en")
        _argos_translate.translate("", "en", "zh")

    with args.master.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    candidates = [row for row in rows if visible(row)]
    if args.file_regex:
        matcher = re.compile(args.file_regex)
        candidates = [row for row in candidates if matcher.search(row.get("file", ""))]
    if args.max_rows:
        candidates = candidates[: args.max_rows]

    prepared = [(row, *protect(row["source"])) for row in candidates]
    groups: list[list[tuple[dict[str, str], str, dict[str, str]]]] = []
    current: list[tuple[dict[str, str], str, dict[str, str]]] = []
    current_chars = 0
    for item in prepared:
        item_chars = len(item[1])
        size_limit = max(1, args.group_size)
        char_limit = args.group_chars
        if current and (
            len(current) >= size_limit
            or (char_limit and current_chars + item_chars > char_limit)
        ):
            groups.append(current)
            current = []
            current_chars = 0
        current.append(item)
        current_chars += item_chars
    if current:
        groups.append(current)
    results: dict[str, str] = {}
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(
                translate_group,
                [(protected_text, protected) for row, protected_text, protected in group],
                args.backend,
            ): group
            for group in groups
        }
        for number, future in enumerate(as_completed(futures), 1):
            group = futures[future]
            try:
                group_results = future.result()
                if len(group_results) != len(group) or any(not result for result in group_results):
                    raise ValueError("empty translation in group")
                for (row, _protected_text, _protected), result in zip(group, group_results):
                    results[row["id"]] = result
            except Exception as error:
                failures.append(f"{group[0][0]['id']} (+{len(group)-1}): {error}")
            if number % 10 == 0:
                print(f"completed_groups={number}/{len(futures)}", flush=True)

    if failures:
        for failure in failures:
            print(failure)
        raise RuntimeError(f"translation failures={len(failures)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "translation"], delimiter="\t")
        writer.writeheader()
        for row in candidates:
            writer.writerow({"id": row["id"], "translation": results[row["id"]]})
    print(f"candidates={len(candidates)}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
