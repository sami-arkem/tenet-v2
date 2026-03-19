import json
from pathlib import Path

SRC = Path("data/processed/chunks/tenet_chunk_manifest_v1.jsonl")
OUT = Path("data/processed/chunks/tenet_retrieval_index_v1.jsonl")

rows = []
with SRC.open(encoding="utf-8", errors="ignore") as f:
    for line in f:
        if not line.strip():
            continue
        item = json.loads(line)
        item["search_text"] = " ".join([
            item.get("source_family", ""),
            item.get("source_name", ""),
            item.get("document_name", ""),
            item.get("jurisdiction", ""),
            item.get("industry", ""),
            item.get("audit_domain", ""),
            item.get("text", "")
        ]).strip()
        rows.append(item)

with OUT.open("w", encoding="utf-8") as g:
    for row in rows:
        g.write(json.dumps(row, ensure_ascii=False) + "\n")

print("indexed_rows", len(rows))
print("wrote", OUT)
