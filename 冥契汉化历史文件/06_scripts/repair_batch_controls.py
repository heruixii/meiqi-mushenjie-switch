"""Restore source BINU8 control codes in an auto-translated TSV batch."""
import csv
import re
import sys
from pathlib import Path

CONTROL_RE = re.compile(r"@[A-Za-z][A-Za-z0-9_]*")

path = Path(sys.argv[1])
master = Path(sys.argv[2])
with master.open(encoding="utf-8-sig", newline="") as handle:
    source_by_id = {row["id"]: row.get("source", "") for row in csv.DictReader(handle, delimiter="\t")}
with path.open(encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
fixed = 0
for row in rows:
    source_codes = CONTROL_RE.findall(source_by_id.get(row.get("id", ""), ""))
    translation_codes = CONTROL_RE.findall(row.get("translation", ""))
    if source_codes != translation_codes:
        text = row.get("translation", "")
        for code in translation_codes:
            text = text.replace(code, "", 1)
        prefix = "".join(source_codes)
        row["translation"] = prefix + text
        fixed += 1
fields = ["id", "translation"]
with path.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: row.get(key, "") for key in fields} for row in rows)
print(f"rows_fixed={fixed}")
