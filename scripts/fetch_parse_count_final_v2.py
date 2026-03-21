import csv
import json
import re
import subprocess
import hashlib
from pathlib import Path
from html import unescape

MANIFEST = Path("data/seed_manifest.tsv")
RAW_DIR = Path("data/sources/raw")
DOCS_OUT = Path("data/processed/clean/tenet_documents_final_v2.jsonl")
CHUNKS_OUT = Path("data/processed/chunks/tenet_chunks_final_v2.jsonl")
DOC_COUNTS_OUT = Path("data/processed/manifests/doc_counts_final_v2.json")
CHUNK_COUNTS_OUT = Path("data/processed/manifests/chunk_counts_final_v2.json")
SUCCESS_LOG = Path("data/logs/fetch_success_v2.tsv")
FAIL_LOG = Path("data/logs/fetch_fail_v2.tsv")

RAW_DIR.mkdir(parents=True, exist_ok=True)
DOCS_OUT.parent.mkdir(parents=True, exist_ok=True)
CHUNKS_OUT.parent.mkdir(parents=True, exist_ok=True)
SUCCESS_LOG.parent.mkdir(parents=True, exist_ok=True)

HARD_BAD_MARKERS = [
    "error 403",
    "error 404",
    "page not found",
    "access denied",
    "request unsuccessful",
    "captcha",
]

SOFT_BAD_MARKERS = [
    "just a moment",
    "enable javascript",
    "cloudflare",
    "temporarily unavailable",
    "maintenance",
]

CHUNK_SIZE = 2000

def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:120]

def fix_url(url: str) -> str:
    url = url.strip()
    url = re.sub(r"(bad_or_blocked|fetch_failed|duplicate)$", "", url)
    url = url.replace("/oj/en", "/oj/eng")
    return url

def fetch(url: str, out: Path):
    cmd = [
        "curl",
        "--http1.1",
        "-L",
        "--compressed",
        "--max-time", "10",
        "--retry", "2",
        "--retry-delay", "1",
        "--retry-all-errors",
        "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        url,
        "-o", str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0

def clean_html(text: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<noscript.*?>.*?</noscript>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<svg.*?>.*?</svg>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def classify_text(text: str):
    t = (text or "").strip().lower()
    if not t:
        return "empty"
    if len(t) < 80:
        return "too_short"
    if any(m in t for m in HARD_BAD_MARKERS):
        return "blocked"
    if len(t) < 180 and any(m in t for m in SOFT_BAD_MARKERS):
        return "blocked"
    if len(t) < 180:
        return "short_but_valid"
    return "ok"

def chunk_text(text: str):
    text = (text or "").strip()
    return [text[i:i+CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE) if text[i:i+CHUNK_SIZE].strip()]

rows = list(csv.DictReader(MANIFEST.open(), delimiter="\t"))
seen = set()
doc_counts = {}
chunk_counts = {}
success_rows = []
fail_rows = []
docs_written = 0
chunks_written = 0

with DOCS_OUT.open("w", encoding="utf-8") as docs_fp, CHUNKS_OUT.open("w", encoding="utf-8") as chunks_fp:
    for row in rows:
        fam = row["source_family"].strip()
        source_name = row["source_name"].strip()
        document_name = row["document_name"].strip()
        url = fix_url(row["url"])

        ext = ".pdf" if url.lower().endswith(".pdf") else ".html"
        out = RAW_DIR / f"{fam}__{slugify(source_name)}__{slugify(document_name)}{ext}"

        ok = fetch(url, out)
        if not ok or not out.exists():
            fail_rows.append([fam, source_name, document_name, url, "fetch_failed"])
            continue

        if ext == ".pdf":
            text = f"PDF_SOURCE {out.name} SIZE_BYTES {out.stat().st_size}"
            status = "ok"
        else:
            raw = out.read_text(encoding="utf-8", errors="ignore")
            text = clean_html(raw)
            status = classify_text(text)

        if status in {"empty", "too_short", "blocked"}:
            fail_rows.append([fam, source_name, document_name, url, status])
            continue

        dedupe_key = hashlib.sha256((fam + "|" + source_name + "|" + document_name + "|" + text[:8000]).encode("utf-8", errors="ignore")).hexdigest()
        if dedupe_key in seen:
            fail_rows.append([fam, source_name, document_name, url, "duplicate"])
            continue
        seen.add(dedupe_key)

        rec = {
            "source_family": fam,
            "source_name": source_name,
            "document_name": document_name,
            "url": url,
            "quality_status": status,
            "text": text[:50000],
        }
        docs_fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
        docs_written += 1
        doc_counts[fam] = doc_counts.get(fam, 0) + 1
        success_rows.append([fam, source_name, document_name, url, status])

        for idx, ch in enumerate(chunk_text(rec["text"]), start=1):
            crec = {
                "source_family": fam,
                "source_name": source_name,
                "document_name": document_name,
                "url": url,
                "quality_status": status,
                "chunk_id": idx,
                "text": ch,
            }
            chunks_fp.write(json.dumps(crec, ensure_ascii=False) + "\n")
            chunks_written += 1
            chunk_counts[fam] = chunk_counts.get(fam, 0) + 1

with SUCCESS_LOG.open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t")
    w.writerow(["source_family", "source_name", "document_name", "url", "status"])
    w.writerows(success_rows)

with FAIL_LOG.open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t")
    w.writerow(["source_family", "source_name", "document_name", "url", "status"])
    w.writerows(fail_rows)

DOC_COUNTS_OUT.write_text(json.dumps(dict(sorted(doc_counts.items())), indent=2), encoding="utf-8")
CHUNK_COUNTS_OUT.write_text(json.dumps(dict(sorted(chunk_counts.items())), indent=2), encoding="utf-8")

print("docs_written", docs_written)
print("chunks_written", chunks_written)
print("doc_counts", json.dumps(dict(sorted(doc_counts.items())), indent=2))
print("chunk_counts", json.dumps(dict(sorted(chunk_counts.items())), indent=2))
print("successes", len(success_rows))
print("failures", len(fail_rows))
