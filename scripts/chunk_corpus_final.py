import json
from pathlib import Path

SRC = Path("data/processed/all_corpus/tenet_corpus_final.jsonl")
OUT = Path("data/processed/chunks/tenet_chunks_final.jsonl")
COUNTS = Path("data/processed/manifests/chunk_family_counts_final.json")
CHUNK = 2000

def chunk_text(text, size=CHUNK):
    text = (text or "").strip()
    return [text[i:i+size] for i in range(0, len(text), size) if text[i:i+size].strip()]

counts = {}
written = 0

with SRC.open(encoding="utf-8", errors="ignore") as f, OUT.open("w", encoding="utf-8") as g:
    for line in f:
        if not line.strip():
            continue
        item = json.loads(line)
        base = {k: v for k, v in item.items() if k != "text"}
        fam = item.get("source_family", "unknown")
        for idx, chunk in enumerate(chunk_text(item.get("text", "")), start=1):
            rec = dict(base)
            rec["chunk_id"] = idx
            rec["text"] = chunk
            g.write(json.dumps(rec, ensure_ascii=False) + "\n")
            counts[fam] = counts.get(fam, 0) + 1
            written += 1

COUNTS.write_text(json.dumps(counts, indent=2), encoding="utf-8")
print("chunks_written", written)
print(counts)
