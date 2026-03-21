import json
from pathlib import Path

processed = Path("data/processed")
out = processed / "all_corpus" / "tenet_corpus_v6_clean.jsonl"
manifest = processed / "manifests" / "all_jsonl_files_v6.txt"
counts_out = processed / "manifests" / "source_family_counts_v6.json"

exclude_parts = [
    "data/processed/all_corpus/",
    "data/processed/fixed/",
    "tenet_corpus_v3.jsonl",
    "tenet_corpus_v4_dedup.jsonl",
    "tenet_corpus_v5.jsonl",
    "all_sanctions_v1.jsonl",
]

files = []
for p in processed.rglob("*.jsonl"):
    sp = str(p)
    if any(part in sp for part in exclude_parts):
        continue
    files.append(p)

files = sorted(files)
manifest.write_text("\n".join(str(p) for p in files), encoding="utf-8")

counts = {}
written = 0

with out.open("w", encoding="utf-8") as g:
    for p in files:
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)

            if "source_family" not in item:
                if "sanctions" in str(p):
                    item["source_family"] = "sanctions"
                elif "train" in str(p):
                    item["source_family"] = "training"

            fam = item.get("source_family", "unknown")
            counts[fam] = counts.get(fam, 0) + 1
            g.write(json.dumps(item, ensure_ascii=False) + "\n")
            written += 1

counts_out.write_text(json.dumps(counts, indent=2), encoding="utf-8")
print("files", len(files))
print("written", written)
print(counts)
