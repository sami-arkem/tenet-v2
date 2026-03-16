import csv
import json
from pathlib import Path

BASE = Path("data/sources/sanctions")
OUT = Path("data/processed/sanctions/parsed")
OUT.mkdir(parents=True, exist_ok=True)

def parse_ofac():
    src = BASE / "ofac" / "ofac_sdn.csv"
    out = OUT / "ofac_sdn.jsonl"
    rows = 0
    with src.open("r", encoding="utf-8", errors="ignore") as f, out.open("w", encoding="utf-8") as g:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            record = {
                "source": "OFAC",
                "record_type": "sanctions",
                "entity_id": row[0].strip() if len(row) > 0 else "",
                "name": row[1].strip() if len(row) > 1 else "",
                "program": row[3].strip() if len(row) > 3 else "",
            }
            g.write(json.dumps(record, ensure_ascii=False) + "\n")
            rows += 1
    print(f"ofac rows: {rows}")

if __name__ == "__main__":
    parse_ofac()
