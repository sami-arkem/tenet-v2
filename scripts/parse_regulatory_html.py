import json
import re
from pathlib import Path

SOURCES = [
    {
        "source_family": "frameworks",
        "source_name": "NIST",
        "document_name": "AI RMF 1.0",
        "input_path": "data/sources/frameworks/nist/nist_ai_rmf.html",
        "output_path": "data/processed/frameworks/nist_ai_rmf.jsonl",
        "url": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10",
    },
    {
        "source_family": "regulations",
        "source_name": "EU",
        "document_name": "EU AI Act",
        "input_path": "data/sources/regulations/eu/eu_ai_act.html",
        "output_path": "data/processed/regulations/eu_ai_act.jsonl",
        "url": "https://op.europa.eu/",
    },
    {
        "source_family": "regulations",
        "source_name": "US",
        "document_name": "FinCEN Bank Secrecy Act",
        "input_path": "data/sources/regulations/us/fincen_bsa.html",
        "output_path": "data/processed/regulations/fincen_bsa.jsonl",
        "url": "https://www.fincen.gov/resources/statutes-and-regulations/bank-secrecy-act",
    },
    {
        "source_family": "regulations",
        "source_name": "UK",
        "document_name": "Money Laundering Regulations 2017",
        "input_path": "data/sources/regulations/uk/uk_mlr_2017.html",
        "output_path": "data/processed/regulations/uk_mlr_2017.jsonl",
        "url": "https://www.legislation.gov.uk/uksi/2017/692/contents/made",
    },
    {
        "source_family": "regulations",
        "source_name": "AUSTRALIA",
        "document_name": "AML/CTF Act",
        "input_path": "data/sources/regulations/australia/australia_aml_ctf_act.html",
        "output_path": "data/processed/regulations/australia_aml_ctf_act.jsonl",
        "url": "https://www.legislation.gov.au/Latest/C2018C00295",
    },
    {
        "source_family": "regulations",
        "source_name": "UAE",
        "document_name": "UAE AML Law",
        "input_path": "data/sources/regulations/gcc/uae_aml_law.html",
        "output_path": "data/processed/regulations/uae_aml_law.jsonl",
        "url": "https://uaelegislation.gov.ae/en/legislations/3314",
    },
    {
        "source_family": "regulations",
        "source_name": "UAE",
        "document_name": "UAE AML Executive Regulations",
        "input_path": "data/sources/regulations/gcc/uae_aml_exec_regs.html",
        "output_path": "data/processed/regulations/uae_aml_exec_regs.jsonl",
        "url": "https://uaelegislation.gov.ae/en/legislations/3857",
    },
]

def clean_html(text: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_title(text: str) -> str:
    m = re.search(r"<title>(.*?)</title>", text, flags=re.S | re.I)
    return m.group(1).strip() if m else "unknown"

def main():
    for item in SOURCES:
        raw = Path(item["input_path"]).read_text(encoding="utf-8", errors="ignore")
        clean = clean_html(raw)
        title = extract_title(raw)

        record = {
            "source_family": item["source_family"],
            "source_name": item["source_name"],
            "document_name": item["document_name"],
            "title": title,
            "url": item["url"],
            "text": clean[:50000],
        }

        out = Path(item["output_path"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {out}")

if __name__ == "__main__":
    main()
