import json
from pathlib import Path

SRC = Path("data/processed/all_corpus/tenet_corpus_v6_clean.jsonl")
OUT = Path("data/processed/chunks/tenet_chunks_v1.jsonl")
CHUNK_SIZE = 2000

def chunk_text(text, size=CHUNK_SIZE):
    text = (text or "").strip()
    return [text[i:i+size] for i in range(0, len(text), size) if text[i:i+size].strip()]

written = 0
with SRC.open(encoding="utf-8", errors="ignore") as f, OUT.open("w", encoding="utf-8") as g:
    for line in f:
        if not line.strip():
            continue
        item = json.loads(line)
        base = {k: v for k, v in item.items() if k != "text"}
        for idx, chunk in enumerate(chunk_text(item.get("text", "")), start=1):
            rec = dict(base)
            rec["chunk_id"] = idx
            rec["text"] = chunk
            g.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1

print("chunks_written", written)
