import json
import re
from pathlib import Path

SRC = Path("data/processed/clean/tenet_documents_final_v2.jsonl")
OUT = Path("data/processed/chunks/tenet_chunk_manifest_v1.jsonl")
COUNTS = Path("data/processed/manifests/chunk_manifest_counts_v1.json")

CHUNK_SIZE = 1800
OVERLAP = 200

def infer_jurisdiction(item):
    text = ((item.get("document_name") or "") + " " + (item.get("source_name") or "") + " " + (item.get("url") or "")).lower()
    mapping = {
        "us": ["sec", "doj", "fincen", "fdic", "occ", "ftc", "cfpb", "hhs", "fda", "cms", "cisa", "nmls"],
        "uk": ["fca", "ofsi", "ico", "gamblingcommission", "companieshouse", "gov.uk"],
        "eu": ["eur-lex", "europa", "edpb", "eba", "esma"],
        "canada": ["canada", "fintrac", "laws-lois"],
        "australia": ["apra", "asic", "austrac", "oaic", "legislation.gov.au"],
        "india": ["rbi", "mca"],
        "singapore": ["mas", "acra"],
        "new_zealand": ["privacy.org.nz"],
        "south_africa": ["popia"],
        "brazil": ["gov.br", "lgpd"],
        "global": ["fatf", "oecd", "who", "bcbs", "iais", "nist"]
    }
    for jurisdiction, needles in mapping.items():
        if any(n in text for n in needles):
            return jurisdiction
    return "unknown"

def infer_industry(family):
    if family.startswith("industry_"):
        return family.replace("industry_", "")
    return "cross_industry"

def infer_audit_domain(family):
    if family.startswith("industry_"):
        return family
    return family

def clean_text(text):
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text

def chunk_text(text, size=CHUNK_SIZE, overlap=OVERLAP):
    text = clean_text(text)
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks

counts = {}
written = 0

with SRC.open(encoding="utf-8", errors="ignore") as f, OUT.open("w", encoding="utf-8") as g:
    for line in f:
        if not line.strip():
            continue
        item = json.loads(line)
        family = item.get("source_family", "unknown")
        chunks = chunk_text(item.get("text", ""))

        for idx, chunk in enumerate(chunks, start=1):
            rec = {
                "source_family": family,
                "source_name": item.get("source_name", ""),
                "document_name": item.get("document_name", ""),
                "url": item.get("url", ""),
                "jurisdiction": infer_jurisdiction(item),
                "industry": infer_industry(family),
                "audit_domain": infer_audit_domain(family),
                "quality_status": item.get("quality_status", "unknown"),
                "chunk_id": idx,
                "text": chunk
            }
            g.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1
            counts[family] = counts.get(family, 0) + 1

COUNTS.write_text(json.dumps(counts, indent=2), encoding="utf-8")
print("chunks_written", written)
print("counts", counts)
