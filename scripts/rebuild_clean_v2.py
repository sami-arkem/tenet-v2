import json
import hashlib
from pathlib import Path

ROOT = Path("data/processed")
PARSED = ROOT / "parsed" / "parsed_sources_v1.jsonl"
OUT_DOCS = ROOT / "clean_v2" / "tenet_documents_v2.jsonl"
OUT_COUNTS = ROOT / "manifests" / "source_family_counts_v2_clean.json"
OUT_CHUNKS = ROOT / "chunks" / "tenet_chunks_v2_clean.jsonl"
OUT_CHUNK_COUNTS = ROOT / "manifests" / "chunk_family_counts_v2_clean.json"

BAD_TEXT_MARKERS = [
    "403 forbidden",
    "access denied",
    "just a moment",
    "enable javascript",
    "request unsuccessful",
    "error 403",
    "error 404",
    "page not found",
]

CHUNK_SIZE = 2000

def is_bad_text(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return True
    if len(t) < 80:
        return True
    return any(marker in t for marker in BAD_TEXT_MARKERS)

def normalize_family(item):
    fam = item.get("source_family", "unknown")
    path = item.get("source_path", "").lower()
    name = item.get("document_name", "").lower()

    if fam == "unknown":
        if "sanction" in path or "sanction" in name:
            fam = "sanctions"
        elif "aml" in path or "aml" in name:
            fam = "aml"
        elif "corporate" in path:
            fam = "corporate"
        elif "licensing" in path:
            fam = "licensing"
        elif "enforcement" in path:
            fam = "enforcement"
        elif "framework" in path:
            fam = "frameworks"
        elif "regulation" in path or "privacy" in path or "gdpr" in path:
            fam = "regulations"
    item["source_family"] = fam
    return item

def chunk_text(text, size=CHUNK_SIZE):
    text = (text or "").strip()
    return [text[i:i+size] for i in range(0, len(text), size) if text[i:i+size].strip()]

seen = set()
docs_written = 0
doc_counts = {}
chunk_counts = {}
chunk_written = 0

with PARSED.open(encoding="utf-8", errors="ignore") as f, \
     OUT_DOCS.open("w", encoding="utf-8") as g_docs, \
     OUT_CHUNKS.open("w", encoding="utf-8") as g_chunks:

    for line in f:
        if not line.strip():
            continue
        item = json.loads(line)
        item = normalize_family(item)

        text = item.get("text", "")
        if is_bad_text(text):
            continue

        key = hashlib.sha256(
            (
                item.get("source_family", "") + "|" +
                item.get("source_name", "") + "|" +
                item.get("document_name", "") + "|" +
                text[:5000]
            ).encode("utf-8", errors="ignore")
        ).hexdigest()

        if key in seen:
            continue
        seen.add(key)

        g_docs.write(json.dumps(item, ensure_ascii=False) + "\n")
        docs_written += 1

        fam = item.get("source_family", "unknown")
        doc_counts[fam] = doc_counts.get(fam, 0) + 1

        base = {k: v for k, v in item.items() if k != "text"}
        for idx, chunk in enumerate(chunk_text(text), start=1):
            rec = dict(base)
            rec["chunk_id"] = idx
            rec["text"] = chunk
            g_chunks.write(json.dumps(rec, ensure_ascii=False) + "\n")
            chunk_written += 1
            chunk_counts[fam] = chunk_counts.get(fam, 0) + 1

OUT_COUNTS.write_text(json.dumps(doc_counts, indent=2), encoding="utf-8")
OUT_CHUNK_COUNTS.write_text(json.dumps(chunk_counts, indent=2), encoding="utf-8")

print("clean_docs_written", docs_written)
print("clean_chunks_written", chunk_written)
print("doc_counts", doc_counts)
print("chunk_counts", chunk_counts)
