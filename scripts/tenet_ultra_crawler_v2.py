import re
import json
import time
import hashlib
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path
from collections import defaultdict, deque

TARGET_DOCS = 500
TARGET_CHUNKS = 500
CHUNK_SIZE = 2000
TIMEOUT = 10
MAX_PAGES = 4000
MAX_PER_FAMILY = 120
SLEEP_BETWEEN = 0.15

ROOT = Path("data/processed/crawler")
ROOT.mkdir(parents=True, exist_ok=True)

DOCS_FILE = ROOT / "tenet_documents_ultra.jsonl"
CHUNKS_FILE = ROOT / "tenet_chunks_ultra.jsonl"
DOC_COUNTS_FILE = Path("data/processed/manifests/doc_counts_ultra.json")
CHUNK_COUNTS_FILE = Path("data/processed/manifests/chunk_counts_ultra.json")
VISITED_FILE = ROOT / "visited_urls.txt"
SEEN_HASHES_FILE = ROOT / "seen_hashes.txt"
FAILS_FILE = ROOT / "failed_urls.txt"

TRACKED_FAMILIES = [
    "aml",
    "corporate",
    "licensing",
    "enforcement",
    "frameworks",
    "regulations",
    "industry_adult",
    "industry_banking",
    "industry_crypto",
    "industry_defense",
    "industry_energy",
    "industry_fintech",
    "industry_gambling",
    "industry_gov_vendor",
    "industry_healthcare",
    "industry_insurance",
    "industry_payments",
    "industry_telecom",
]

SEEDS = {
    "aml": [
        "https://www.fincen.gov/guidance",
        "https://www.eba.europa.eu/regulation-and-policy/anti-money-laundering-and-countering-financing-terrorism",
        "https://www.fca.org.uk/firms/financial-crime/money-laundering-regulations",
        "https://fintrac-canafe.canada.ca/guidance-directives/transaction-operation/24hour/24hour-eng",
        "https://www.mas.gov.sg/regulation/anti-money-laundering/targeted-financial-sanctions",
        "https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Guidance-on-Digital-Identity.html",
    ],
    "corporate": [
        "https://www.sec.gov/edgar/searchedgar/companysearch",
        "https://find-and-update.company-information.service.gov.uk/",
        "https://ised-isde.canada.ca/site/corporations-canada/en",
        "https://asic.gov.au/for-business/registers/",
        "https://www.mca.gov.in/content/mca/global/en/company-llp-registration.html",
        "https://www.acra.gov.sg/how-to-guides/browse-topics/company-registration",
    ],
    "licensing": [
        "https://www.nmlsconsumeraccess.org/",
        "https://register.fca.org.uk/s/",
        "https://www.canada.ca/en/financial-consumer-agency/services/financial-toolkit/financial-institutions.html",
        "https://connectonline.asic.gov.au/",
        "https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=12194",
    ],
    "enforcement": [
        "https://www.sec.gov/enforcement-litigation/litigation-releases",
        "https://www.justice.gov/criminal/criminal-fraud/evaluation-corporate-compliance-programs",
        "https://www.gov.uk/government/publications/financial-sanctions-general-guidance",
        "https://finance.ec.europa.eu/financial-crime/eu-restrictive-measures_en",
        "https://www.fincen.gov/news/news-releases",
    ],
    "frameworks": [
        "https://oecd.ai/en/ai-principles",
        "https://oecd.ai/en/classification",
        "https://www.who.int/teams/digital-health-and-innovation/health-data-governance",
        "https://www.cisa.gov/cross-sector-cybersecurity-performance-goals",
        "https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/guide-to-accountability-and-governance/",
    ],
    "regulations": [
        "https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-314",
        "https://www.ftc.gov/business-guidance/privacy-security/gramm-leach-bliley-act",
        "https://www.legislation.gov.uk/uksi/2017/692/contents/made",
        "https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng",
        "https://laws-lois.justice.gc.ca/eng/acts/P-8.6/",
        "https://www.oaic.gov.au/privacy/the-privacy-act",
        "https://www.privacy.org.nz/privacy-act-2020/",
    ],
    "industry_fintech": [
        "https://www.consumerfinance.gov/compliance/supervision-examinations/",
        "https://www.consumerfinance.gov/compliance/compliance-resources/",
        "https://www.fca.org.uk/firms/innovation",
        "https://www.sec.gov/finhub",
    ],
    "industry_gov_vendor": [
        "https://www.acquisition.gov/far",
        "https://www.acquisition.gov/far-part-52",
        "https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng",
        "https://www.fedramp.gov/",
    ],
    "industry_healthcare": [
        "https://www.hhs.gov/hipaa/for-professionals/security/index.html",
        "https://www.hhs.gov/ocr/privacy/hipaa/administrative/securityrule/index.html",
        "https://www.cms.gov/medicare/provider-enrollment-and-certification/surveycertificationgeninfo/health-insurance-portability-and-accountability-act-hipaa",
        "https://www.fda.gov/medical-devices/digital-health-center-excellence/cybersecurity-medical-devices-frequently-asked-questions",
        "https://www.who.int/teams/digital-health-and-innovation/health-data-governance",
    ],
    "industry_payments": [
        "https://www.ecfr.gov/current/title-12/chapter-X/part-1005",
        "https://www.consumerfinance.gov/compliance/compliance-resources/",
        "https://www.ftc.gov/business-guidance/privacy-security/gramm-leach-bliley-act",
        "https://finance.ec.europa.eu/consumer-finance-and-payments/payment-services/payment-services-psd-2_en",
    ],
    "industry_crypto": [
        "https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng",
        "https://www.fincen.gov/guidance",
        "https://www.finra.org/rules-guidance/key-topics/aml",
        "https://www.sec.gov/finhub",
    ],
    "industry_banking": [
        "https://bsaaml.ffiec.gov/manual",
        "https://www.occ.treas.gov/publications-and-resources/publications/comptrollers-handbook/index-comptrollers-handbook.html",
        "https://www.bis.org/bcbs/publ/d550.htm",
        "https://www.fdic.gov/banker-resource-center/bank-secrecy-act-anti-money-laundering-bsaaml",
    ],
    "industry_insurance": [
        "https://www.apra.gov.au/cps-234-information-security",
        "https://www.apra.gov.au/information-security",
        "https://www.iaisweb.org/activities-topics/standards/",
        "https://content.naic.org/cipr-topics/cybersecurity",
        "https://www.dfs.ny.gov/industry_guidance/cybersecurity",
    ],
    "industry_telecom": [
        "https://www.cisa.gov/communications-resiliency",
        "https://www.cisa.gov/resources-tools/resources/enhanced-visibility-and-hardening-guidance-communications-infrastructure",
        "https://www.cisa.gov/resources-tools/resources/mobile-communications-best-practice-guidance",
    ],
    "industry_defense": [
        "https://dodcio.defense.gov/CMMC/",
        "https://csrc.nist.gov/pubs/sp/800/171/r3/final",
        "https://www.acquisition.gov/dfars",
    ],
    "industry_gambling": [
        "https://www.gamblingcommission.gov.uk/licensees-and-businesses/guide/page/anti-money-laundering",
        "https://www.gamblingcommission.gov.uk/licensees-and-businesses/guide/page/licence-conditions-and-codes-of-practice",
        "https://www.austrac.gov.au/business/industry-specific-guidance/gambling-industry",
    ],
    "industry_energy": [
        "https://www.nerc.com/pa/Stand/Pages/CIPStandards.aspx",
        "https://www.energy.gov/ceser/office-cybersecurity-energy-security-and-emergency-response",
        "https://www.cisa.gov/topics/industrial-control-systems",
    ],
    "industry_adult": [
        "https://www.justice.gov/criminal/criminal-ceos/obscenity",
        "https://www.justice.gov/humantrafficking",
        "https://www.ftc.gov/business-guidance/privacy-security",
    ],
}

BAD_MARKERS = [
    "403 forbidden",
    "access denied",
    "just a moment",
    "enable javascript",
    "request unsuccessful",
    "page not found",
    "error 404",
    "error 403",
    "cloudflare",
    "captcha",
    "temporarily unavailable",
    "maintenance",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def clean_html(text: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<noscript.*?>.*?</noscript>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<svg.*?>.*?</svg>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_links(base_url: str, html: str):
    hrefs = re.findall(r'href=["\\\']([^"\\\']+)["\\\']', html, flags=re.I)
    out = []
    base = urllib.parse.urlparse(base_url)
    for h in hrefs:
        if h.startswith("#") or h.startswith("mailto:") or h.startswith("javascript:"):
            continue
        full = urllib.parse.urljoin(base_url, h)
        p = urllib.parse.urlparse(full)
        if p.scheme not in ("http", "https"):
            continue
        if p.netloc != base.netloc:
            continue
        full = full.split("#")[0]
        out.append(full)
    return out

def fetch_url(url: str):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            data = r.read()
            return ctype, data
    except Exception:
        return None, None

def is_good_text(text: str):
    t = (text or "").strip().lower()
    if len(t) < 200:
        return False
    return not any(m in t for m in BAD_MARKERS)

def chunk_text(text: str, size: int = CHUNK_SIZE):
    text = (text or "").strip()
    return [text[i:i+size] for i in range(0, len(text), size) if text[i:i+size].strip()]

visited = set()
seen_hashes = set()
doc_counts = defaultdict(int)
chunk_counts = defaultdict(int)

q = deque()
for fam, urls in SEEDS.items():
    for u in urls:
        q.append((fam, u))

pages = 0
per_family = defaultdict(int)

with DOCS_FILE.open("a", encoding="utf-8") as docs_fp, \
     CHUNKS_FILE.open("a", encoding="utf-8") as chunks_fp, \
     VISITED_FILE.open("a", encoding="utf-8") as vis_fp, \
     SEEN_HASHES_FILE.open("a", encoding="utf-8") as hash_fp, \
     FAILS_FILE.open("a", encoding="utf-8") as fail_fp:

    while q and pages < MAX_PAGES:
        fam, url = q.popleft()

        if fam not in TRACKED_FAMILIES:
            continue
        if per_family[fam] >= MAX_PER_FAMILY:
            continue
        if doc_counts[fam] >= TARGET_DOCS and chunk_counts[fam] >= TARGET_CHUNKS:
            continue
        if url in visited:
            continue

        visited.add(url)
        vis_fp.write(url + "\n")
        vis_fp.flush()

        ctype, data = fetch_url(url)
        time.sleep(SLEEP_BETWEEN)

        if not data:
            fail_fp.write(url + "\n")
            fail_fp.flush()
            continue

        ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
        raw_html = ""
        text = ""

        if "pdf" in (ctype or "") or ext == ".pdf":
            text = f"PDF_SOURCE {url} SIZE_BYTES {len(data)}"
        else:
            try:
                raw_html = data.decode("utf-8", errors="ignore")
            except Exception:
                raw_html = data.decode("latin1", errors="ignore")
            text = clean_html(raw_html)

        if not is_good_text(text):
            continue

        h = hashlib.sha256((fam + "|" + text[:8000]).encode("utf-8", errors="ignore")).hexdigest()
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        hash_fp.write(h + "\n")
        hash_fp.flush()

        rec = {
            "source_family": fam,
            "source_name": urllib.parse.urlparse(url).netloc.upper().replace(".", "_"),
            "document_name": url,
            "url": url,
            "text": text[:50000],
        }
        docs_fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
        docs_fp.flush()

        doc_counts[fam] += 1
        per_family[fam] += 1
        pages += 1

        for idx, ch in enumerate(chunk_text(rec["text"]), start=1):
            crec = {
                "source_family": fam,
                "source_name": rec["source_name"],
                "document_name": rec["document_name"],
                "url": url,
                "chunk_id": idx,
                "text": ch,
            }
            chunks_fp.write(json.dumps(crec, ensure_ascii=False) + "\n")
            chunk_counts[fam] += 1
        chunks_fp.flush()

        if raw_html:
            for nxt in extract_links(url, raw_html):
                if nxt not in visited:
                    q.append((fam, nxt))

DOC_COUNTS_FILE.write_text(json.dumps(dict(sorted(doc_counts.items())), indent=2), encoding="utf-8")
CHUNK_COUNTS_FILE.write_text(json.dumps(dict(sorted(chunk_counts.items())), indent=2), encoding="utf-8")

print("pages_crawled", pages)
print("queue_left", len(q))
print("doc_counts", json.dumps(dict(sorted(doc_counts.items())), indent=2))
print("chunk_counts", json.dumps(dict(sorted(chunk_counts.items())), indent=2))
