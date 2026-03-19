import json
import re
import hashlib
from pathlib import Path

SRC_ROOT = Path("data/sources")
OUT_ROOT = Path("data/processed/parsed")
OUT_ROOT.mkdir(parents=True, exist_ok=True)

URL_RE = re.compile(r"https?://[^\s\"'>]+", re.I)

def clean_text(text: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<noscript.*?>.*?</noscript>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&#160;", " ").replace("&amp;", "&")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def infer_family(parts):
    if "industry" in parts:
        i = parts.index("industry")
        if i + 1 < len(parts):
            return f"industry_{parts[i+1]}"
    for fam in ["aml", "corporate", "licensing", "enforcement", "frameworks", "regulations", "sanctions"]:
        if fam in parts:
            return fam
    return "unknown"

def infer_source_name(stem: str) -> str:
    s = stem.lower()
    mapping = {
        "fincen": "FINCEN",
        "eba": "EBA",
        "fca": "FCA",
        "rbi": "RBI",
        "fintrac": "FINTRAC",
        "mas": "MAS",
        "austrac": "AUSTRAC",
        "fatf": "FATF",
        "sec": "SEC",
        "companies_house": "UK_COMPANIES_HOUSE",
        "corporations_canada": "CANADA_CORPORATIONS",
        "asic": "ASIC",
        "mca": "MCA_INDIA",
        "eu": "EU",
        "acra": "ACRA",
        "nmls": "NMLS",
        "cfpb": "CFPB",
        "far": "FAR",
        "hhs": "HHS",
        "fda": "FDA",
        "who": "WHO",
        "ftc": "FTC",
        "mica": "EU",
        "finra": "FINRA",
        "bcbs": "BCBS",
        "ffiec": "FFIEC",
        "occ": "OCC",
        "apra": "APRA",
        "iais": "IAIS",
        "naic": "NAIC",
        "cisa": "CISA",
        "dcsa": "DCSA",
        "gambling": "UKGC",
        "doj": "DOJ",
        "nerc": "NERC",
        "ofsi": "UK_OFSI",
        "oecd": "OECD",
        "ico": "ICO",
        "gdpr": "EU",
        "edpb": "EDPB",
        "pcmltfa": "CANADA",
        "pipeda": "CANADA",
        "oaic": "AUSTRALIA_OAIC",
        "popia": "SOUTH_AFRICA",
        "lgpd": "BRAZIL",
        "privacy_act": "NEW_ZEALAND",
    }
    for k, v in mapping.items():
        if k in s:
            return v
    return stem.split("_")[0].upper()

def title_from_stem(stem: str) -> str:
    s = re.sub(r"_i\d+$", "", stem)
    s = re.sub(r"_v\d+$", "", s)
    s = s.replace("_", " ").strip()
    return s.title()

def maybe_url(text: str):
    m = URL_RE.search(text[:5000])
    return m.group(0) if m else ""

records = []
seen = set()

for p in sorted(SRC_ROOT.rglob("*")):
    if not p.is_file():
        continue
    rel = p.relative_to(SRC_ROOT)
    parts = rel.parts
    family = infer_family(parts)
    stem = p.stem
    ext = p.suffix.lower()

    if ext in [".html", ".htm", ".txt"]:
        raw = p.read_text(encoding="utf-8", errors="ignore")
        text = clean_text(raw)
    elif ext == ".pdf":
        text = f"PDF_SOURCE {p.name} SIZE_BYTES {p.stat().st_size}"
    elif ext in [".csv", ".xml", ".json", ".jsonl"]:
        raw = p.read_text(encoding="utf-8", errors="ignore")
        text = clean_text(raw)
    else:
        text = f"BINARY_SOURCE {p.name} SIZE_BYTES {p.stat().st_size}"

    if not text:
        continue

    rec = {
        "source_family": family,
        "source_name": infer_source_name(stem),
        "document_name": title_from_stem(stem),
        "source_path": str(rel),
        "url": maybe_url(text),
        "text": text[:50000],
    }

    key = hashlib.sha256(
        (rec["source_family"] + "|" + rec["source_name"] + "|" + rec["document_name"] + "|" + rec["text"][:4000]).encode("utf-8", errors="ignore")
    ).hexdigest()
    if key in seen:
        continue
    seen.add(key)
    records.append(rec)

out = OUT_ROOT / "parsed_sources_v1.jsonl"
with out.open("w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print("parsed_records", len(records))
print("wrote", out)
