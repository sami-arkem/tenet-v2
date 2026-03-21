import json
import re
from pathlib import Path
from collections import Counter

INDEX = Path("data/processed/chunks/tenet_retrieval_index_v1.jsonl")

def tokenize(text: str):
    return re.findall(r"[a-zA-Z0-9_]+", (text or "").lower())

def score_row(row, query_tokens, industry=None, jurisdictions=None, source_families=None):
    text_tokens = tokenize(row.get("search_text", ""))
    counts = Counter(text_tokens)

    keyword_score = sum(counts.get(t, 0) for t in query_tokens)

    meta_score = 0
    if industry and row.get("industry") == industry:
        meta_score += 5
    if jurisdictions and row.get("jurisdiction") in jurisdictions:
        meta_score += 5
    if source_families and row.get("source_family") in source_families:
        meta_score += 4

    quality_bonus = 1 if row.get("quality_status") in ["ok", "short_but_valid", "unknown"] else 0

    return keyword_score + meta_score + quality_bonus

def retrieve(query, industry=None, jurisdictions=None, source_families=None, top_k=12):
    query_tokens = tokenize(query)
    rows = []

    with INDEX.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            score = score_row(row, query_tokens, industry, jurisdictions, source_families)
            if score > 0:
                row["score"] = score
                rows.append(row)

    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows[:top_k]

if __name__ == "__main__":
    query = "fintech aml kyc sanctions controls us uk eu"
    results = retrieve(
        query=query,
        industry="fintech",
        jurisdictions=["us", "uk", "eu"],
        source_families=["regulations", "aml", "enforcement", "industry_fintech"]
    )
    print(json.dumps(results[:5], indent=2))
