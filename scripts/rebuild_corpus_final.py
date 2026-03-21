import json
from pathlib import Path

processed = Path("data/processed")
files = []

for p in sorted(processed.rglob("*.jsonl")):
    sp = str(p)
    if "/all_corpus/" in sp or "/chunks/" in sp or "/manifests/" in sp:
        continue
    files.append(p)

manifest = processed / "manifests" / "all_jsonl_files_final.txt"
manifest.write_text("\n".join(str(p) for p in files), encoding="utf-8")

out = processed / "all_corpus" / "tenet_corpus_final.jsonl"
counts = {}
written = 0

with out.open("w", encoding="utf-8") as g:
    for p in files:
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            fam = item.get("source_family", "unknown")
            counts[fam] = counts.get(fam, 0) + 1
            g.write(json.dumps(item, ensure_ascii=False) + "\n")
            written += 1

(processed / "manifests" / "source_family_counts_final.json").write_text(
    json.dumps(counts, indent=2), encoding="utf-8"
)

print("files", len(files))
print("written", written)
print(counts)
