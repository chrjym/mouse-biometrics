#!/usr/bin/env python3
"""
example-rrl-fetch.py — Fetch, deduplicate, and cross-check mouse biometrics candidate literature.

Sources supported:
- arXiv (Search API / Atom XML, free, no key)
- OpenAlex (REST API, free, no key, polite pool via mailto; supports --ph for OpenAlex-PH)
- Semantic Scholar (Graph API, free, no key; supports optional SEMANTIC_SCHOLAR_API_KEY)
- Google Scholar via SerpApi (optional, requires SERPAPI_KEY env var or --serpapi-key)
- Crossref (Search API, free, no key)
- CORE (REST API, free, requires CORE_API_KEY env var or --core-key)
- Europe PMC (REST API, free, no key)
- PubMed NCBI E-utilities (REST API / XML, free, optional NCBI_API_KEY or --ncbi-key)
- ERIC (REST API, free, no key)
- DOAJ (REST API, free, no key; supports --ph for DOAJ-PH)
- DBLP (REST API, free, no key)
- OpenAIRE (REST API, free, no key)
- Zenodo (REST API, free, no key)
- OSF Preprints (REST API, free, no key, title filter only)
- Springer Nature (REST API, requires SPRINGER_API_KEY or --springer-key)
- IEEE Xplore (REST API, requires IEEE_API_KEY or --ieee-key)

Enrichment:
- Unpaywall: Given DOI, resolves legal open access PDF link (requires RRL_EMAIL env var or --email)

Manual Import (ResearchGate / ejournals.ph / HERDIN):
- Text file input (--import-file) with DOIs, URLs, or titles (supports rg: and pej: tags).
- Verifies against Crossref without scraping. Unverified items retained as stubs.
- Outputs manual Google site: search links for ResearchGate, ejournals.ph, and HERDIN.

LaTeX / BibTeX Export:
- --latex flag: Writes <out>.bib with escaped special chars, double-braced titles, unique keys,
  and <out>_rrl.tex compilable skeleton with \\nocite{*} and apalike style.
"""

import argparse
import concurrent.futures
import datetime
import difflib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure stdout/stderr handles UTF-8 on Windows consoles without charmap crash
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# Default search queries tailored to thesis scope
DEFAULT_QUERIES = [
    '"mouse dynamics" "authentication"',
    '"curvature" "mouse trajectory"',
]

DEFAULT_EMAIL = os.environ.get("RRL_EMAIL", "thesis-research@example.edu")
USER_AGENT = f"ThesisLiteratureChecker/2.0 (mailto:{DEFAULT_EMAIL}; academic-thesis-project)"
TIMEOUT_SECONDS = 20

# Enforced literature search year scope (2021-2026 only)
DEFAULT_MIN_YEAR = 2021
DEFAULT_MAX_YEAR = 2026


# ==========================================
# HTTP & RETRY UTILITIES
# ==========================================

def safe_urlopen(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = TIMEOUT_SECONDS,
    max_retries: int = 2,
    retry_delay: float = 1.5,
) -> bytes:
    """
    Safely opens a URL with headers, handling Windows/Linux SSL certificate fallbacks,
    and retrying on HTTP 429 (rate limits) and 5xx (transient server errors).
    """
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)

    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            last_error = e
            # Retry on rate limiting (429) or transient server errors (5xx)
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                wait_time = retry_delay * (attempt + 1)
                time.sleep(wait_time)
                continue
            raise
        except urllib.error.URLError as e:
            last_error = e
            err_msg = str(e)
            if "CERTIFICATE_VERIFY_FAILED" in err_msg or "certificate verify failed" in err_msg:
                import ssl
                ctx = ssl._create_unverified_context()
                try:
                    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                        return response.read()
                except Exception as inner_e:
                    last_error = inner_e
            if attempt < max_retries:
                time.sleep(retry_delay * (attempt + 1))
                continue
            raise
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(retry_delay * (attempt + 1))
                continue
            raise

    if last_error:
        raise last_error
    return b""


# ==========================================
# STRING & DOI NORMALIZATION
# ==========================================

def normalize_string(text: str) -> str:
    """Normalize string for fuzzy/exact matching by lowercasing and stripping non-alphanumerics."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    """
    Normalizes DOIs by lowercasing, stripping leading URLs/prefixes
    ('https://doi.org/', 'http://dx.doi.org/', 'doi:'), and trailing punctuation.
    """
    if not doi:
        return None
    d = str(doi).strip().lower()
    prefixes = [
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi.org/",
        "dx.doi.org/",
        "doi:",
    ]
    changed = True
    while changed:
        changed = False
        d = d.strip()
        for p in prefixes:
            if d.startswith(p):
                d = d[len(p):].strip()
                changed = True

    d = d.rstrip(")., \t\r\n")
    return d if d else None


def title_similarity(title1: str, title2: str) -> float:
    """Computes similarity ratio between two normalized titles."""
    norm1 = normalize_string(title1)
    norm2 = normalize_string(title2)
    if not norm1 or not norm2:
        return 0.0
    if norm1 == norm2:
        return 1.0

    seq_ratio = difflib.SequenceMatcher(None, norm1, norm2).ratio()

    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())
    if tokens1 and tokens2:
        jaccard = len(tokens1.intersection(tokens2)) / len(tokens1.union(tokens2))
    else:
        jaccard = 0.0

    return max(seq_ratio, jaccard)


def clean_html(text: str) -> str:
    """Strips HTML/XML tags and normalizes whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


# ==========================================
# RECORD SHAPE BUILDER
# ==========================================

def make_record(
    title: str = "",
    authors: Optional[List[str]] = None,
    year: str = "",
    doi: Optional[str] = None,
    abstract: str = "",
    url: str = "",
    pdf_url: str = "",
    venue: str = "",
    citations: int = 0,
    sources: Optional[List[str]] = None,
    date: str = "",
) -> dict:
    """
    Constructs a uniform record shape across all literature connectors:
    title, authors[], year, doi, abstract, url, pdf_url, venue, citations, sources[].
    """
    clean_title = re.sub(r"\s+", " ", (title or "").strip())
    clean_authors = [re.sub(r"\s+", " ", (a or "").strip()) for a in (authors or []) if a and a.strip()]
    norm_doi = normalize_doi(doi)
    clean_abstract = clean_html(abstract)
    clean_year = str(year or "").strip()
    if not clean_year and date:
        m = re.search(r"\b(19\d\d|20\d\d)\b", date)
        if m:
            clean_year = m.group(1)

    return {
        "title": clean_title,
        "authors": clean_authors,
        "year": clean_year,
        "doi": norm_doi,
        "abstract": clean_abstract,
        "url": (url or "").strip(),
        "pdf_url": (pdf_url or "").strip(),
        "venue": re.sub(r"\s+", " ", (venue or "").strip()),
        "citations": max(0, int(citations or 0)),
        "sources": list(sources or []),
        "date": (date or "").strip(),
        "cited_by_count": max(0, int(citations or 0)),  # backwards compatibility
    }


# ==========================================
# BIBLIOGRAPHY CROSS-CHECK
# ==========================================

def extract_logged_papers(bib_path: Path) -> Dict[str, Set[str]]:
    """
    Parses references/annotated-bibliography.md to extract known paper titles, DOIs, and arXiv IDs.
    Filters out markdown section headers and metadata keywords.
    """
    logged_titles: Set[str] = set()
    logged_dois: Set[str] = set()
    logged_arxiv_ids: Set[str] = set()

    if not bib_path.exists():
        print(f"[*] Note: Annotated bibliography not found at {bib_path}", file=sys.stderr)
        return {"titles": logged_titles, "dois": logged_dois, "arxiv_ids": logged_arxiv_ids}

    content = bib_path.read_text(encoding="utf-8")

    excluded_prefixes = {
        "context", "feedback", "decisions", "open questions", "phase 1", "phase 2", "phase 3", "phase 4",
        "authors", "year", "venue", "abstract", "strengths", "weaknesses", "limitations", "gaps",
        "connection to our thesis gap", "four phase evolution", "identified gap", "resulting thesis framing",
        "table of contents", "source", "core focus", "key methodological themes", "paper 1", "paper 2",
        "paper 3", "paper 4", "paper 5", "paper 6", "paper 7", "paper 8", "thesis review rule", "note",
        "important", "warning", "tip", "caution"
    }

    # Extract bold items: **Title**
    bold_items = re.findall(r"\*\*([^*]+)\*\*", content)
    for item in bold_items:
        cleaned = item.strip()
        norm_item = normalize_string(cleaned)
        if not norm_item:
            continue
        if any(norm_item.startswith(prefix) for prefix in excluded_prefixes):
            continue
        if len(norm_item.split()) >= 2:
            logged_titles.add(norm_item)

    # Extract DOIs: 10.xxxx/yyyy
    dois = re.findall(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", content)
    for d in dois:
        nd = normalize_doi(d)
        if nd:
            logged_dois.add(nd)

    # Extract arXiv IDs: arXiv:YYMM.NNNNN or arxiv.org/abs/YYMM.NNNNN
    arxiv_ids = re.findall(r"arxiv(?:\.org/(?:abs|pdf)/|:)(\d{4}\.\d{4,5})", content, flags=re.IGNORECASE)
    for aid in arxiv_ids:
        logged_arxiv_ids.add(aid.lower())

    return {"titles": logged_titles, "dois": logged_dois, "arxiv_ids": logged_arxiv_ids}


def is_already_logged(paper: dict, logged_data: Dict[str, Set[str]]) -> Tuple[bool, str]:
    """
    Check if a paper is already logged in the annotated bibliography.
    Returns (is_logged, reason).
    """
    # 1. Check DOI match
    doi = normalize_doi(paper.get("doi"))
    if doi:
        if doi in logged_data["dois"]:
            return True, f"DOI match: {doi}"
        for logged_doi in logged_data["dois"]:
            if doi in logged_doi or logged_doi in doi:
                return True, f"DOI substring match: {doi}"

    # 2. Check arXiv ID match
    url = paper.get("url") or ""
    arxiv_match = re.search(r"(\d{4}\.\d{4,5})", url)
    if arxiv_match:
        aid = arxiv_match.group(1).lower()
        if aid in logged_data["arxiv_ids"]:
            return True, f"arXiv ID match: {aid}"

    # 3. Check Title match
    title = paper.get("title", "")
    norm_title = normalize_string(title)
    if not norm_title:
        return False, ""

    if norm_title in logged_data["titles"]:
        return True, "Exact title match"

    for logged_title in logged_data["titles"]:
        sim = title_similarity(norm_title, logged_title)
        if sim >= 0.80:
            return True, f"Fuzzy title match ({sim:.2f}) with '{logged_title[:40]}...'"

    return False, ""


# ==========================================
# SOURCE FETCHERS
# ==========================================

def build_arxiv_query(query_str: str) -> str:
    """Builds an accurate phrase-level boolean query for arXiv API."""
    phrases = re.findall(r'"([^"]+)"', query_str)
    remaining = re.sub(r'"[^"]+"', " ", query_str).strip()
    words = [w for w in remaining.split() if w.upper() not in ("AND", "OR", "NOT")]

    clauses = []
    for p in phrases:
        if p.strip():
            clauses.append(f'all:"{p.strip()}"')
    for w in words:
        if w.strip():
            clauses.append(f'all:"{w.strip()}"')

    if not clauses:
        clauses = [f'all:"{query_str.strip()}"']

    return " AND ".join(clauses)


def fetch_arxiv(query: str, limit: int = 15) -> List[dict]:
    """Fetch preprints from arXiv Search API (Atom/XML feed)."""
    base_url = "https://export.arxiv.org/api/query"
    search_expr = build_arxiv_query(query)
    params = {
        "search_query": search_expr,
        "start": 0,
        "max_results": limit,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    results = []
    try:
        raw_xml = safe_urlopen(url, timeout=TIMEOUT_SECONDS)
        root = ET.fromstring(raw_xml.decode("utf-8"))
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

        for entry in root.findall("atom:entry", ns):
            title_elem = entry.find("atom:title", ns)
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            if not title:
                continue

            summary_elem = entry.find("atom:summary", ns)
            summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""

            published_elem = entry.find("atom:published", ns)
            pub_date = published_elem.text.strip()[:10] if published_elem is not None and published_elem.text else ""

            id_elem = entry.find("atom:id", ns)
            paper_url = id_elem.text.strip() if id_elem is not None and id_elem.text else ""

            pdf_url = ""
            for link_elem in entry.findall("atom:link", ns):
                if link_elem.get("title") == "pdf" or link_elem.get("type") == "application/pdf":
                    pdf_url = link_elem.get("href", "")

            authors = [
                a.find("atom:name", ns).text.strip()
                for a in entry.findall("atom:author", ns)
                if a.find("atom:name", ns) is not None and a.find("atom:name", ns).text
            ]

            doi_elem = entry.find("arxiv:doi", ns)
            doi = doi_elem.text.strip() if doi_elem is not None and doi_elem.text else None

            results.append(make_record(
                title=title,
                authors=authors,
                year=pub_date[:4] if pub_date else "",
                doi=doi,
                abstract=summary,
                url=paper_url or (f"https://doi.org/{doi}" if doi else ""),
                pdf_url=pdf_url,
                venue="arXiv Preprint",
                citations=0,
                sources=["arXiv"],
                date=pub_date,
            ))
    except Exception as e:
        print(f"[!] arXiv fetch error: {e}", file=sys.stderr)

    return results


def fetch_openalex(query: str, limit: int = 15, ph_scope: bool = False, email: Optional[str] = None) -> List[dict]:
    """Fetch works from OpenAlex REST API with polite pool mailto parameter."""
    base_url = "https://api.openalex.org/works"
    contact_email = email or os.environ.get("RRL_EMAIL") or DEFAULT_EMAIL
    params: Dict[str, Any] = {
        "search": query,
        "sort": "publication_date:desc",
        "per_page": min(limit, 50),
        "mailto": contact_email,
    }
    source_label = "OpenAlex-PH" if ph_scope else "OpenAlex"
    if ph_scope:
        params["filter"] = "institutions.country_code:PH"

    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    results = []
    try:
        raw_json = safe_urlopen(url, timeout=TIMEOUT_SECONDS)
        data = json.loads(raw_json.decode("utf-8"))

        for item in data.get("results", []):
            title = item.get("display_name") or item.get("title") or ""
            if not title:
                continue

            pub_date = item.get("publication_date") or ""
            doi = item.get("doi")
            primary_loc = item.get("primary_location") or {}
            source_info = primary_loc.get("source") or {}
            venue = source_info.get("display_name") or "Journal/Conference"

            authors = []
            for authorship in item.get("authorships", []):
                author = authorship.get("author", {})
                if author.get("display_name"):
                    authors.append(author["display_name"])

            abstract = ""
            inv_index = item.get("abstract_inverted_index")
            if inv_index and isinstance(inv_index, dict):
                positions = []
                for word, pos_list in inv_index.items():
                    for p in pos_list:
                        positions.append((p, word))
                positions.sort(key=lambda x: x[0])
                abstract = " ".join(w for _, w in positions)

            oa_info = item.get("open_access") or {}
            pdf_url = oa_info.get("oa_url") or primary_loc.get("pdf_url") or ""

            results.append(make_record(
                title=title,
                authors=authors,
                year=str(item.get("publication_year") or pub_date[:4] if pub_date else ""),
                doi=doi,
                abstract=abstract,
                url=doi or item.get("id") or "",
                pdf_url=pdf_url,
                venue=venue,
                citations=item.get("cited_by_count", 0),
                sources=[source_label],
                date=pub_date,
            ))
    except Exception as e:
        print(f"[!] {source_label} fetch error: {e}", file=sys.stderr)

    return results


def fetch_semantic_scholar(query: str, limit: int = 15, api_key: Optional[str] = None) -> List[dict]:
    """Fetch papers from Semantic Scholar Graph API."""
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    fields = "title,authors,year,publicationDate,abstract,externalIds,url,venue,citationCount,openAccessPdf"
    params = {
        "query": query,
        "limit": min(limit, 50),
        "fields": fields,
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    headers = {}
    s2_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY") or os.environ.get("S2_API_KEY")
    if s2_key:
        headers["x-api-key"] = s2_key

    results = []
    try:
        raw_json = safe_urlopen(url, headers=headers, timeout=TIMEOUT_SECONDS)
        data = json.loads(raw_json.decode("utf-8"))

        for item in data.get("data", []):
            title = item.get("title") or ""
            if not title:
                continue

            ext_ids = item.get("externalIds") or {}
            doi = ext_ids.get("DOI")
            pub_date = item.get("publicationDate") or ""
            year = str(item.get("year") or pub_date[:4] if pub_date else "")
            authors = [a.get("name") for a in item.get("authors", []) if a.get("name")]
            venue = item.get("venue") or "Conference/Journal"
            oa_pdf = item.get("openAccessPdf") or {}
            pdf_url = oa_pdf.get("url") or ""

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=item.get("abstract") or "",
                url=item.get("url") or (f"https://doi.org/{doi}" if doi else ""),
                pdf_url=pdf_url,
                venue=venue,
                citations=item.get("citationCount", 0),
                sources=["Semantic Scholar"],
                date=pub_date,
            ))
    except Exception as e:
        print(f"[!] Semantic Scholar fetch error: {e}", file=sys.stderr)

    return results


def fetch_google_scholar_serpapi(query: str, limit: int = 15, api_key: Optional[str] = None) -> List[dict]:
    """Fetch papers from Google Scholar via SerpApi. Skipped if key absent."""
    key = api_key or os.environ.get("SERPAPI_KEY")
    if not key:
        return []

    base_url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_scholar",
        "q": query,
        "num": min(limit, 20),
        "api_key": key,
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    results = []
    try:
        raw_json = safe_urlopen(url, timeout=TIMEOUT_SECONDS)
        data = json.loads(raw_json.decode("utf-8"))

        for item in data.get("organic_results", []):
            title = item.get("title") or ""
            if not title:
                continue

            link = item.get("link") or ""
            snippet = item.get("snippet") or ""
            pub_info = item.get("publication_info") or {}
            authors = [a.get("name") for a in pub_info.get("authors", []) if a.get("name")]
            summary_text = pub_info.get("summary") or ""

            year_match = re.search(r"\b(19\d\d|20\d\d)\b", summary_text)
            year = year_match.group(1) if year_match else ""

            doi = None
            if "doi.org/" in link:
                doi = link

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=snippet,
                url=link,
                venue=summary_text[:60] if summary_text else "Google Scholar",
                citations=0,
                sources=["Google Scholar (SerpApi)"],
                date=year,
            ))
    except Exception as e:
        print(f"[!] Google Scholar (SerpApi) fetch error: {e}", file=sys.stderr)

    return results


def fetch_europe_pmc(query: str, limit: int = 15) -> List[dict]:
    """Fetch open research papers from Europe PMC REST API (no key required)."""
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": query,
        "format": "json",
        "resultType": "core",
        "pageSize": min(limit, 100),
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    results = []
    try:
        raw_json = safe_urlopen(url, timeout=TIMEOUT_SECONDS)
        data = json.loads(raw_json.decode("utf-8"))
        for item in data.get("resultList", {}).get("result", []):
            title = item.get("title") or ""
            if not title:
                continue

            authors = []
            author_list = item.get("authorList", {}).get("author", [])
            for a in author_list:
                if a.get("fullName"):
                    authors.append(a["fullName"])
            if not authors and item.get("authorString"):
                authors = [a.strip() for a in item["authorString"].split(",") if a.strip()]

            year = str(item.get("pubYear") or "")
            doi = item.get("doi")
            venue = item.get("journalTitle") or item.get("bookOrReportDetails", {}).get("publisher") or ""
            citations = item.get("citedByCount", 0)

            pdf_url = ""
            for ft in item.get("fullTextUrlList", {}).get("fullTextUrl", []):
                if ft.get("documentStyle") == "pdf" or str(ft.get("url", "")).endswith(".pdf"):
                    pdf_url = ft.get("url", "")
                    break

            paper_url = ""
            if item.get("source") and item.get("id"):
                paper_url = f"https://europepmc.org/article/{item['source']}/{item['id']}"

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=item.get("abstractText") or "",
                url=paper_url or (f"https://doi.org/{doi}" if doi else ""),
                pdf_url=pdf_url,
                venue=venue,
                citations=citations,
                sources=["Europe PMC"],
                date=year,
            ))
    except Exception as e:
        print(f"[!] Europe PMC fetch error: {e}", file=sys.stderr)

    return results


def fetch_pubmed(query: str, limit: int = 15, api_key: Optional[str] = None) -> List[dict]:
    """Fetch medical and bioengineering papers from PubMed via NCBI E-utilities (esearch then efetch)."""
    ncbi_key = api_key or os.environ.get("NCBI_API_KEY")
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": min(limit, 50),
    }
    if ncbi_key:
        search_params["api_key"] = ncbi_key

    results = []
    try:
        raw_search = safe_urlopen(f"{search_url}?{urllib.parse.urlencode(search_params)}", timeout=TIMEOUT_SECONDS)
        search_data = json.loads(raw_search.decode("utf-8"))
        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []

        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "xml",
        }
        if ncbi_key:
            fetch_params["api_key"] = ncbi_key

        raw_fetch = safe_urlopen(f"{fetch_url}?{urllib.parse.urlencode(fetch_params)}", timeout=TIMEOUT_SECONDS)
        root = ET.fromstring(raw_fetch.decode("utf-8"))

        for art in root.findall(".//PubmedArticle"):
            title = art.findtext(".//ArticleTitle") or ""
            if not title:
                continue

            pmid = art.findtext(".//PMID") or ""
            venue = art.findtext(".//Journal/Title") or art.findtext(".//Journal/ISOAbbreviation") or ""
            year = (
                art.findtext(".//JournalIssue/PubDate/Year")
                or art.findtext(".//JournalIssue/PubDate/MedlineDate")
                or ""
            )
            if len(year) > 4:
                m = re.search(r"\b(19\d\d|20\d\d)\b", year)
                year = m.group(1) if m else year[:4]

            doi = None
            for aid in art.findall(".//ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = aid.text
                    break

            authors = []
            for a in art.findall(".//AuthorList/Author"):
                fn = a.findtext("ForeName")
                ln = a.findtext("LastName")
                if fn and ln:
                    authors.append(f"{fn} {ln}")
                elif ln:
                    authors.append(ln)

            abstract_elem = art.find(".//Abstract")
            abstract_text = " ".join(abstract_elem.itertext()).strip() if abstract_elem is not None else ""

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=abstract_text,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else (f"https://doi.org/{doi}" if doi else ""),
                venue=venue,
                citations=0,
                sources=["PubMed"],
                date=year,
            ))
    except Exception as e:
        print(f"[!] PubMed fetch error: {e}", file=sys.stderr)

    return results


def fetch_eric(query: str, limit: int = 15) -> List[dict]:
    """Fetch education and human-computer learning literature from ERIC REST API."""
    base_url = "https://api.ies.ed.gov/eric/"
    params = {
        "search": query,
        "format": "json",
        "rows": min(limit, 50),
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    results = []
    try:
        raw_json = safe_urlopen(url, timeout=TIMEOUT_SECONDS)
        data = json.loads(raw_json.decode("utf-8"))
        for doc in data.get("response", {}).get("docs", []):
            title = doc.get("title") or ""
            if not title:
                continue

            raw_authors = doc.get("author") or []
            if isinstance(raw_authors, str):
                authors = [raw_authors]
            else:
                authors = list(raw_authors)

            year = str(doc.get("publicationdateyear") or "")
            venue = doc.get("source") or "ERIC"
            eric_id = doc.get("id") or ""
            url_link = doc.get("url") or (f"https://eric.ed.gov/?id={eric_id}" if eric_id else "")

            doi = None
            e_loc = doc.get("e_location") or ""
            if "10." in e_loc:
                doi = e_loc

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=doc.get("description") or "",
                url=url_link,
                venue=venue,
                citations=0,
                sources=["ERIC"],
                date=year,
            ))
    except Exception as e:
        print(f"[!] ERIC fetch error: {e}", file=sys.stderr)

    return results


def fetch_doaj(query: str, limit: int = 15, ph_scope: bool = False) -> List[dict]:
    """Fetch open-access articles from DOAJ REST API. Supports --ph restriction to PH journals."""
    doaj_query = f"{query} AND bibjson.journal.country:PH" if ph_scope else query
    source_label = "DOAJ-PH" if ph_scope else "DOAJ"

    encoded_q = urllib.parse.quote(doaj_query)
    url = f"https://doaj.org/api/search/articles/{encoded_q}?pageSize={min(limit, 50)}"

    results = []
    try:
        raw_json = safe_urlopen(url, timeout=TIMEOUT_SECONDS)
        data = json.loads(raw_json.decode("utf-8"))

        for item in data.get("results", []):
            bibjson = item.get("bibjson", {})
            title = bibjson.get("title") or ""
            if not title:
                continue

            authors = [a.get("name") for a in bibjson.get("author", []) if a.get("name")]
            year = str(bibjson.get("year") or "")
            venue = bibjson.get("journal", {}).get("title") or ""

            doi = None
            for ident in bibjson.get("identifier", []):
                if ident.get("type", "").lower() == "doi":
                    doi = ident.get("id")
                    break

            paper_url = ""
            pdf_url = ""
            for link in bibjson.get("link", []):
                l_url = link.get("url", "")
                if link.get("type") == "fulltext":
                    paper_url = l_url
                if str(l_url).endswith(".pdf"):
                    pdf_url = l_url

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=bibjson.get("abstract") or "",
                url=paper_url or (f"https://doi.org/{doi}" if doi else ""),
                pdf_url=pdf_url,
                venue=venue,
                citations=0,
                sources=[source_label],
                date=year,
            ))
    except Exception as e:
        print(f"[!] {source_label} fetch error: {e}", file=sys.stderr)

    return results


def fetch_dblp(query: str, limit: int = 15) -> List[dict]:
    """Fetch computer science publications from DBLP Search API."""
    base_url = "https://dblp.org/search/publ/api"
    params = {
        "q": query,
        "format": "json",
        "h": min(limit, 50),
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    headers = {"Accept": "application/json"}

    results = []
    try:
        raw_data = safe_urlopen(url, headers=headers, timeout=TIMEOUT_SECONDS)
        try:
            data = json.loads(raw_data.decode("utf-8"))
        except json.JSONDecodeError:
            # DBLP may respond with an HTML bot challenge
            print("[!] DBLP returned non-JSON response (Cloudflare/bot verification challenge). Skipping.", file=sys.stderr)
            return []

        hits = data.get("result", {}).get("hits", {}).get("hit", [])
        for hit in hits:
            info = hit.get("info", {})
            title = info.get("title", "").rstrip(".")
            if not title:
                continue

            authors = []
            raw_authors = info.get("authors", {}).get("author", [])
            if isinstance(raw_authors, dict):
                raw_authors = [raw_authors]
            for a in raw_authors:
                if isinstance(a, dict) and a.get("text"):
                    authors.append(a["text"])
                elif isinstance(a, str):
                    authors.append(a)

            year = str(info.get("year") or "")
            venue = info.get("venue") or ""
            doi = info.get("doi")
            paper_url = info.get("ee") or info.get("url") or ""
            pdf_url = paper_url if paper_url.endswith(".pdf") else ""

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract="",
                url=paper_url,
                pdf_url=pdf_url,
                venue=venue,
                citations=0,
                sources=["DBLP"],
                date=year,
            ))
    except Exception as e:
        print(f"[!] DBLP fetch error: {e}", file=sys.stderr)

    return results


def fetch_openaire(query: str, limit: int = 15) -> List[dict]:
    """Fetch research products from OpenAIRE Graph API."""
    base_url = "https://api.openaire.eu/graph/v1/researchProducts"
    params = {
        "search": query,
        "pageSize": min(limit, 50),
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    results = []
    try:
        raw_json = safe_urlopen(url, timeout=TIMEOUT_SECONDS)
        data = json.loads(raw_json.decode("utf-8"))

        for item in data.get("results", []):
            title = item.get("mainTitle") or ""
            if not title:
                continue

            authors = [a.get("fullName") for a in item.get("authors", []) if a.get("fullName")]
            pub_date = item.get("publicationDate") or ""
            year = pub_date[:4] if pub_date else ""

            doi = None
            for pid in item.get("pids", []):
                if pid.get("scheme", "").lower() == "doi":
                    doi = pid.get("value")
                    break

            descriptions = item.get("descriptions", [])
            abstract = descriptions[0] if descriptions else ""
            venue = item.get("publisher") or item.get("container", {}).get("name") or ""

            pdf_url = ""
            paper_url = f"https://doi.org/{doi}" if doi else ""
            for inst in item.get("instances", []):
                urls = inst.get("urls", [])
                for u in urls:
                    if str(u).endswith(".pdf"):
                        pdf_url = u
                    elif not paper_url:
                        paper_url = u

            citations = item.get("indicators", {}).get("citationCount", 0)

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=abstract,
                url=paper_url,
                pdf_url=pdf_url,
                venue=venue,
                citations=citations,
                sources=["OpenAIRE"],
                date=pub_date,
            ))
    except Exception as e:
        print(f"[!] OpenAIRE fetch error: {e}", file=sys.stderr)

    return results


def fetch_zenodo(query: str, limit: int = 15) -> List[dict]:
    """Fetch open science records and datasets from Zenodo REST API."""
    base_url = "https://zenodo.org/api/records"
    params = {
        "q": query,
        "size": min(limit, 50),
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    results = []
    try:
        raw_json = safe_urlopen(url, timeout=TIMEOUT_SECONDS)
        data = json.loads(raw_json.decode("utf-8"))

        for hit in data.get("hits", {}).get("hits", []):
            meta = hit.get("metadata", {})
            title = meta.get("title") or ""
            if not title:
                continue

            authors = [c.get("name") for c in meta.get("creators", []) if c.get("name")]
            pub_date = meta.get("publication_date") or ""
            year = pub_date[:4] if pub_date else ""
            doi = meta.get("doi") or hit.get("doi")
            venue = (
                meta.get("journal_title")
                or meta.get("conference_title")
                or meta.get("resource_type", {}).get("title")
                or "Zenodo"
            )
            paper_url = hit.get("links", {}).get("doi") or hit.get("links", {}).get("html") or ""

            pdf_url = ""
            for f in hit.get("files", []):
                if f.get("key", "").endswith(".pdf"):
                    pdf_url = f.get("links", {}).get("self", "")
                    break

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=meta.get("description") or "",
                url=paper_url,
                pdf_url=pdf_url,
                venue=venue,
                citations=0,
                sources=["Zenodo"],
                date=pub_date,
            ))
    except Exception as e:
        print(f"[!] Zenodo fetch error: {e}", file=sys.stderr)

    return results


def fetch_osf(query: str, limit: int = 15) -> List[dict]:
    """Fetch preprints from OSF Preprints REST API (title filter only per API design)."""
    clean_title_q = re.sub(r'["\']', '', query).strip()
    base_url = "https://api.osf.io/v2/preprints/"
    params = {
        "filter[title]": clean_title_q,
        "embed": "contributors",
        "page[size]": min(limit, 50),
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    results = []
    try:
        raw_json = safe_urlopen(url, timeout=TIMEOUT_SECONDS)
        data = json.loads(raw_json.decode("utf-8"))

        for item in data.get("data", []):
            attr = item.get("attributes", {})
            title = attr.get("title") or ""
            if not title:
                continue

            pub_date = attr.get("date_published") or attr.get("date_created") or ""
            year = pub_date[:4] if pub_date else ""
            doi = attr.get("doi")

            authors = []
            contributors = item.get("embeds", {}).get("contributors", {}).get("data", [])
            for c in contributors:
                user_attr = c.get("embeds", {}).get("users", {}).get("data", {}).get("attributes", {})
                full_name = user_attr.get("full_name")
                if full_name:
                    authors.append(full_name)

            links = item.get("links", {})
            paper_url = links.get("html") or ""

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=attr.get("description") or "",
                url=paper_url,
                venue="OSF Preprints",
                citations=0,
                sources=["OSF Preprints"],
                date=pub_date,
            ))
    except Exception as e:
        print(f"[!] OSF Preprints fetch error: {e}", file=sys.stderr)

    return results


def fetch_springer(query: str, limit: int = 15, api_key: Optional[str] = None) -> List[dict]:
    """Fetch articles from Springer Nature Meta API. Gracefully skipped if key is absent."""
    key = api_key or os.environ.get("SPRINGER_API_KEY")
    if not key:
        return []

    base_url = "https://api.springernature.com/meta/v2/json"
    params = {
        "q": query,
        "api_key": key,
        "p": min(limit, 50),
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    results = []
    try:
        raw_json = safe_urlopen(url, timeout=TIMEOUT_SECONDS)
        data = json.loads(raw_json.decode("utf-8"))

        for rec in data.get("records", []):
            title = rec.get("title") or ""
            if not title:
                continue

            authors = [c.get("creator") for c in rec.get("creators", []) if c.get("creator")]
            pub_date = rec.get("publicationDate") or ""
            year = pub_date[:4] if pub_date else ""
            doi = rec.get("doi")
            venue = rec.get("publicationName") or ""

            paper_url = ""
            pdf_url = ""
            for u in rec.get("url", []):
                if u.get("format") == "html":
                    paper_url = u.get("value", "")
                elif u.get("format") == "pdf":
                    pdf_url = u.get("value", "")

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=rec.get("abstract") or "",
                url=paper_url or (f"https://doi.org/{doi}" if doi else ""),
                pdf_url=pdf_url,
                venue=venue,
                citations=0,
                sources=["Springer Nature"],
                date=pub_date,
            ))
    except Exception as e:
        print(f"[!] Springer Nature fetch error: {e}", file=sys.stderr)

    return results


def fetch_ieee(query: str, limit: int = 15, api_key: Optional[str] = None) -> List[dict]:
    """Fetch publications from IEEE Xplore API. Gracefully skipped if key is absent."""
    key = api_key or os.environ.get("IEEE_API_KEY")
    if not key:
        return []

    base_url = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
    params = {
        "querytext": query,
        "apikey": key,
        "max_records": min(limit, 50),
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    results = []
    try:
        raw_json = safe_urlopen(url, timeout=TIMEOUT_SECONDS)
        data = json.loads(raw_json.decode("utf-8"))

        for art in data.get("articles", []):
            title = art.get("title") or ""
            if not title:
                continue

            authors = [
                a.get("full_name")
                for a in art.get("authors", {}).get("authors", [])
                if a.get("full_name")
            ]
            year = str(art.get("publication_year") or "")
            doi = art.get("doi")
            venue = art.get("publication_title") or ""
            citations = art.get("citing_paper_count", 0)

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=art.get("abstract") or "",
                url=art.get("html_url") or (f"https://doi.org/{doi}" if doi else ""),
                pdf_url=art.get("pdf_url") or "",
                venue=venue,
                citations=citations,
                sources=["IEEE Xplore"],
                date=year,
            ))
    except Exception as e:
        print(f"[!] IEEE Xplore fetch error: {e}", file=sys.stderr)

    return results


def fetch_core(query: str, limit: int = 15, api_key: Optional[str] = None) -> List[dict]:
    """Fetch full-text research outputs from CORE API v3. Gracefully skipped if key is absent."""
    key = api_key or os.environ.get("CORE_API_KEY")
    if not key:
        return []

    base_url = "https://api.core.ac.uk/v3/search/works"
    params = {
        "q": query,
        "limit": min(limit, 50),
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    headers = {"Authorization": f"Bearer {key}"}

    results = []
    try:
        raw_json = safe_urlopen(url, headers=headers, timeout=TIMEOUT_SECONDS)
        data = json.loads(raw_json.decode("utf-8"))

        for item in data.get("results", []):
            title = item.get("title") or ""
            if not title:
                continue

            authors = [a.get("name") for a in item.get("authors", []) if a.get("name")]
            year = str(item.get("yearPublished") or "")
            doi = item.get("doi")
            venue = item.get("journals", [{}])[0].get("title") if item.get("journals") else "CORE"

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=item.get("abstract") or "",
                url=item.get("downloadUrl") or (f"https://doi.org/{doi}" if doi else ""),
                pdf_url=item.get("downloadUrl") or "",
                venue=venue,
                citations=item.get("citationCount", 0),
                sources=["CORE"],
                date=year,
            ))
    except Exception as e:
        print(f"[!] CORE fetch error: {e}", file=sys.stderr)

    return results


def fetch_crossref(query: str, limit: int = 15, email: Optional[str] = None) -> List[dict]:
    """Fetch DOI-indexed publications from Crossref Search API."""
    contact_email = email or os.environ.get("RRL_EMAIL") or DEFAULT_EMAIL
    base_url = "https://api.crossref.org/works"
    params = {
        "query": query,
        "rows": min(limit, 50),
        "mailto": contact_email,
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": f"ThesisLiteratureChecker/2.0 (mailto:{contact_email})"}

    results = []
    try:
        raw_json = safe_urlopen(url, headers=headers, timeout=TIMEOUT_SECONDS)
        data = json.loads(raw_json.decode("utf-8"))

        for item in data.get("message", {}).get("items", []):
            titles = item.get("title", [])
            title = titles[0] if titles else ""
            if not title:
                continue

            authors = []
            for a in item.get("author", []):
                given = a.get("given", "").strip()
                family = a.get("family", "").strip()
                if given and family:
                    authors.append(f"{given} {family}")
                elif family:
                    authors.append(family)

            year = ""
            for date_key in ("published-print", "published-online", "created"):
                parts = item.get(date_key, {}).get("date-parts", [[]])
                if parts and parts[0]:
                    year = str(parts[0][0])
                    break

            doi = item.get("DOI")
            venue_list = item.get("container-title", [])
            venue = venue_list[0] if venue_list else ""
            citations = item.get("is-referenced-by-count", 0)

            results.append(make_record(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=item.get("abstract") or "",
                url=f"https://doi.org/{doi}" if doi else "",
                venue=venue,
                citations=citations,
                sources=["Crossref"],
                date=year,
            ))
    except Exception as e:
        print(f"[!] Crossref fetch error: {e}", file=sys.stderr)

    return results


# ==========================================
# UNPAYWALL ENRICHMENT
# ==========================================

def enrich_with_unpaywall(papers: List[dict], email: Optional[str] = None) -> None:
    """
    Given a list of papers with DOIs, queries Unpaywall to add legal free PDF links.
    Requires RRL_EMAIL environment variable or --email.
    """
    contact_email = email or os.environ.get("RRL_EMAIL")
    if not contact_email:
        print("[*] RRL_EMAIL not set. Skipping Unpaywall PDF enrichment.", file=sys.stderr)
        return

    print(f"[*] Enriching {len(papers)} candidate papers with Unpaywall open-access links...", file=sys.stderr)
    enriched_count = 0

    for paper in papers:
        doi = normalize_doi(paper.get("doi"))
        if not doi or paper.get("pdf_url"):
            continue

        url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={contact_email}"
        try:
            raw_json = safe_urlopen(url, timeout=10, max_retries=1)
            data = json.loads(raw_json.decode("utf-8"))
            if data.get("is_oa"):
                best_loc = data.get("best_oa_location") or {}
                pdf_link = best_loc.get("url_for_pdf") or best_loc.get("url")
                if pdf_link:
                    paper["pdf_url"] = pdf_link
                    enriched_count += 1
        except Exception:
            continue

    print(f"[✓] Unpaywall enrichment complete: added PDF links to {enriched_count} paper(s).", file=sys.stderr)


# ==========================================
# MANUAL IMPORT & RESOLUTION (PART 3)
# ==========================================

def resolve_crossref_doi(doi: str, email: Optional[str] = None) -> Optional[dict]:
    """Resolves DOI metadata strictly through Crossref /works/{doi}."""
    contact_email = email or os.environ.get("RRL_EMAIL") or DEFAULT_EMAIL
    clean_doi = normalize_doi(doi)
    if not clean_doi:
        return None

    url = f"https://api.crossref.org/works/{urllib.parse.quote(clean_doi)}"
    headers = {"User-Agent": f"ThesisLiteratureChecker/2.0 (mailto:{contact_email})"}
    try:
        raw_json = safe_urlopen(url, headers=headers, timeout=TIMEOUT_SECONDS, max_retries=1)
        data = json.loads(raw_json.decode("utf-8"))
        msg = data.get("message", {})

        titles = msg.get("title", [])
        title = titles[0] if titles else ""

        authors = []
        for a in msg.get("author", []):
            given = a.get("given", "").strip()
            family = a.get("family", "").strip()
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)

        year = ""
        for date_key in ("published-print", "published-online", "created"):
            parts = msg.get(date_key, {}).get("date-parts", [[]])
            if parts and parts[0]:
                year = str(parts[0][0])
                break

        venue_list = msg.get("container-title", [])
        venue = venue_list[0] if venue_list else ""
        citations = msg.get("is-referenced-by-count", 0)

        return make_record(
            title=title,
            authors=authors,
            year=year,
            doi=clean_doi,
            abstract=msg.get("abstract") or "",
            url=f"https://doi.org/{clean_doi}",
            venue=venue,
            citations=citations,
        )
    except Exception:
        return None


def resolve_crossref_title(title: str, email: Optional[str] = None) -> Optional[Tuple[dict, float]]:
    """Resolves title through Crossref query.bibliographic and checks title similarity."""
    contact_email = email or os.environ.get("RRL_EMAIL") or DEFAULT_EMAIL
    if not title:
        return None

    encoded_t = urllib.parse.quote(title)
    url = f"https://api.crossref.org/works?query.bibliographic={encoded_t}&rows=1"
    headers = {"User-Agent": f"ThesisLiteratureChecker/2.0 (mailto:{contact_email})"}
    try:
        raw_json = safe_urlopen(url, headers=headers, timeout=TIMEOUT_SECONDS, max_retries=1)
        data = json.loads(raw_json.decode("utf-8"))
        items = data.get("message", {}).get("items", [])
        if not items:
            return None

        best_item = items[0]
        titles = best_item.get("title", [])
        best_title = titles[0] if titles else ""
        sim = title_similarity(best_title, title)

        authors = []
        for a in best_item.get("author", []):
            given = a.get("given", "").strip()
            family = a.get("family", "").strip()
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)

        year = ""
        for date_key in ("published-print", "published-online", "created"):
            parts = best_item.get(date_key, {}).get("date-parts", [[]])
            if parts and parts[0]:
                year = str(parts[0][0])
                break

        venue_list = best_item.get("container-title", [])
        venue = venue_list[0] if venue_list else ""
        citations = best_item.get("is-referenced-by-count", 0)
        doi = best_item.get("DOI")

        record = make_record(
            title=best_title,
            authors=authors,
            year=year,
            doi=doi,
            abstract=best_item.get("abstract") or "",
            url=f"https://doi.org/{doi}" if doi else "",
            venue=venue,
            citations=citations,
        )
        return record, sim
    except Exception:
        return None


def parse_manual_line(line: str) -> Optional[dict]:
    """
    Parses a single line from manual import file.
    Detects tag prefixes (rg:, pej:), ResearchGate URL slugs, DOIs, URLs, or plain titles.
    Lines starting with '#' are comments.
    """
    cleaned = line.strip()
    if not cleaned or cleaned.startswith("#"):
        return None

    tag_base = "Manual Import"
    if cleaned.lower().startswith("rg:"):
        tag_base = "ResearchGate"
        cleaned = cleaned[3:].strip()
    elif cleaned.lower().startswith("pej:"):
        tag_base = "ejournals.ph"
        cleaned = cleaned[4:].strip()
    elif "researchgate.net" in cleaned.lower():
        tag_base = "ResearchGate"
    elif "ejournals.ph" in cleaned.lower():
        tag_base = "ejournals.ph"

    # ResearchGate publication slug: /publication/<id>_<Title_Words>
    rg_match = re.search(r"/publication/\d+_([A-Za-z0-9_\-\.%]+)", cleaned)
    if rg_match:
        raw_slug = rg_match.group(1)
        extracted_title = urllib.parse.unquote(raw_slug).replace("_", " ").strip()
        return {
            "kind": "rg_slug",
            "content": extracted_title,
            "url": cleaned,
            "tag_base": tag_base,
        }

    # Check DOI format
    norm_d = normalize_doi(cleaned)
    if norm_d and re.match(r"^10\.\d{4,9}/.+", norm_d):
        return {
            "kind": "doi",
            "content": norm_d,
            "url": cleaned if cleaned.startswith("http") else "",
            "tag_base": tag_base,
        }

    # Check generic URL (e.g. ejournals.ph)
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return {
            "kind": "url",
            "content": cleaned,
            "url": cleaned,
            "tag_base": tag_base,
        }

    # Otherwise plain title
    return {
        "kind": "title",
        "content": cleaned,
        "url": "",
        "tag_base": tag_base,
    }


def import_manual_file(file_path: Path, email: Optional[str] = None) -> List[dict]:
    """
    Imports literature records from a manual text file without scraping.
    Verifies DOIs and titles against Crossref. Unverified entries are preserved as stubs.
    """
    if not file_path.exists():
        print(f"[!] Manual import file not found: {file_path}", file=sys.stderr)
        return []

    lines = file_path.read_text(encoding="utf-8").splitlines()
    print(f"[*] Processing manual import file ({len(lines)} lines) from {file_path.name}...", file=sys.stderr)

    imported_papers: List[dict] = []
    verified_count = 0
    unverified_count = 0

    for idx, line in enumerate(lines, 1):
        parsed = parse_manual_line(line)
        if not parsed:
            continue

        tag_base = parsed["tag_base"]
        kind = parsed["kind"]
        content = parsed["content"]
        orig_url = parsed["url"]

        if kind == "doi":
            resolved = resolve_crossref_doi(content, email=email)
            if resolved:
                resolved["sources"] = [f"{tag_base} (manual)"]
                imported_papers.append(resolved)
                verified_count += 1
            else:
                stub = make_record(
                    title=content,
                    doi=content,
                    url=orig_url or (f"https://doi.org/{content}" if content else ""),
                    sources=[f"{tag_base} (manual, unverified)"],
                )
                imported_papers.append(stub)
                unverified_count += 1

        elif kind in ("title", "rg_slug"):
            resolved_tuple = resolve_crossref_title(content, email=email)
            if resolved_tuple and resolved_tuple[1] >= 0.80:
                record = resolved_tuple[0]
                record["sources"] = [f"{tag_base} (manual)"]
                if orig_url and not record.get("url"):
                    record["url"] = orig_url
                imported_papers.append(record)
                verified_count += 1
            else:
                stub = make_record(
                    title=content,
                    url=orig_url,
                    sources=[f"{tag_base} (manual, unverified)"],
                )
                imported_papers.append(stub)
                unverified_count += 1

        elif kind == "url":
            # Direct URLs (e.g. ejournals.ph) cannot be scraped per policy; kept as unverified stub
            stub = make_record(
                title=orig_url,
                url=orig_url,
                sources=[f"{tag_base} (manual, unverified)"],
            )
            imported_papers.append(stub)
            unverified_count += 1

    print(
        f"[✓] Manual import processed: {verified_count} verified via Crossref, "
        f"{unverified_count} retained as unverified stubs.",
        file=sys.stderr,
    )
    return imported_papers


def get_manual_search_links(queries: List[str]) -> List[Tuple[str, str]]:
    """Generates Google site: search links for ResearchGate, ejournals.ph, and HERDIN."""
    links = []
    for q in queries:
        clean_q = re.sub(r'["\']', '', q).strip()
        encoded = urllib.parse.quote_plus(clean_q)
        links.append((
            f"ResearchGate site-search for '{clean_q}'",
            f"https://www.google.com/search?q=site%3Aresearchgate.net+{encoded}",
        ))
        links.append((
            f"Philippine E-Journals (ejournals.ph) site-search for '{clean_q}'",
            f"https://www.google.com/search?q=site%3Aejournals.ph+{encoded}",
        ))
        links.append((
            f"HERDIN Health/PH Research site-search for '{clean_q}'",
            f"https://www.google.com/search?q=site%3Aherdin.ph+{encoded}",
        ))
    return links


# ==========================================
# LATEX / BIBTEX EXPORT (PART 4)
# ==========================================

def escape_bibtex(text: str) -> str:
    """
    Escapes LaTeX/BibTeX special characters (& % $ # _ { } ~ ^ \\) in a single pass.
    """
    if not text:
        return ""
    char_map = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    pattern = re.compile(r"[" + re.escape("".join(char_map.keys())) + r"]")
    return pattern.sub(lambda m: char_map[m.group(0)], text)


def generate_bibtex_key(paper: dict, seen_keys: Set[str]) -> str:
    """
    Generates a unique BibTeX key like lastname2022firstword.
    Collisions are resolved by appending letters 'b', 'c', etc.
    """
    authors = paper.get("authors", [])
    if authors:
        first_author = authors[0].strip()
        if "," in first_author:
            last = first_author.split(",")[0].strip()
        else:
            parts = first_author.split()
            last = parts[-1] if parts else "anon"
        last = re.sub(r"[^a-zA-Z]", "", last).lower() or "anon"
    else:
        last = "anon"

    year = paper.get("year", "")
    year_match = re.search(r"\b(19\d\d|20\d\d)\b", str(year))
    yr = year_match.group(1) if year_match else "nodate"

    title = paper.get("title", "")
    words = re.findall(r"[a-zA-Z]+", title.lower())
    stop_words = {"a", "an", "the", "on", "in", "of", "for", "to", "and", "with", "at", "by", "from"}
    sig_words = [w for w in words if w not in stop_words]
    first_word = sig_words[0] if sig_words else (words[0] if words else "paper")

    base_key = f"{last}{yr}{first_word}"
    key = base_key
    counter = 1
    suffixes = "abcdefghijklmnopqrstuvwxyz"
    while key in seen_keys:
        if counter < len(suffixes):
            key = f"{base_key}{suffixes[counter]}"
        else:
            key = f"{base_key}_{counter+1}"
        counter += 1

    seen_keys.add(key)
    return key


def export_latex_and_bibtex(candidates: List[dict], out_base_path: Path) -> Tuple[Path, Path]:
    """
    Writes <out>.bib and <out>_rrl.tex compilable skeleton.
    - Uses double braces around titles to protect capitalization.
    - Uses @article when a venue exists, otherwise @misc.
    - Uses the doi field, or url only when there is no DOI.
    """
    base = out_base_path.with_suffix("")
    bib_file = base.with_suffix(".bib")
    tex_file = base.parent / f"{base.stem}_rrl.tex"
    bib_file.parent.mkdir(parents=True, exist_ok=True)

    seen_keys: Set[str] = set()
    bib_entries: List[str] = []
    key_comment_list: List[str] = []

    for paper in candidates:
        key = generate_bibtex_key(paper, seen_keys)
        title = paper.get("title", "")
        key_comment_list.append(f"% - {key}: {title}")

        venue = paper.get("venue", "").strip()
        entry_type = "article" if venue else "misc"

        lines = [f"@{entry_type}{{{key},"]

        # Authors
        authors = paper.get("authors", [])
        if authors:
            escaped_authors = [escape_bibtex(a) for a in authors]
            lines.append(f"  author = {{{' and '.join(escaped_authors)}}},")

        # Title protected with double braces
        if title:
            lines.append(f"  title = {{{{{escape_bibtex(title)}}}}},")

        # Venue / Journal
        if venue:
            lines.append(f"  journal = {{{{{escape_bibtex(venue)}}}}},")

        # Year
        year = paper.get("year", "")
        if year:
            lines.append(f"  year = {{{escape_bibtex(year)}}},")

        # DOI or URL
        doi = normalize_doi(paper.get("doi"))
        url = paper.get("url", "").strip()
        if doi:
            lines.append(f"  doi = {{{doi}}},")
        elif url:
            lines.append(f"  url = {{{escape_bibtex(url)}}},")

        lines.append("}\n")
        bib_entries.append("\n".join(lines))

    # Write .bib file
    bib_file.write_text("\n".join(bib_entries), encoding="utf-8")

    # Write compilable .tex skeleton
    tex_skeleton = [
        r"\documentclass{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage{natbib}",
        r"\usepackage{url}",
        r"\usepackage{hyperref}",
        "",
        r"\title{Review of Related Literature --- Mouse Dynamics Biometrics}",
        r"\author{Thesis Literature Review}",
        r"\date{\today}",
        "",
        r"\begin{document}",
        r"\maketitle",
        "",
        r"\section{Review of Related Literature Candidates}",
        r"This document compiles candidate literature retrieved for continuous authentication and mouse biometrics research.",
        "",
        r"% Citation keys included in this collection:",
    ]
    tex_skeleton.extend(key_comment_list)
    tex_skeleton.extend([
        "",
        r"\nocite{*}",
        "",
        r"\bibliographystyle{apalike}",
        f"\\bibliography{{{bib_file.stem}}}",
        "",
        r"\end{document}",
        "",
    ])
    tex_file.write_text("\n".join(tex_skeleton), encoding="utf-8")

    print(f"[✓] Exported BibTeX bibliography to: {bib_file}", file=sys.stderr)
    print(f"[✓] Exported compilable LaTeX skeleton to: {tex_file}", file=sys.stderr)
    return bib_file, tex_file


# ==========================================
# DEDUPLICATION & MERGING
# ==========================================

def deduplicate_and_merge(paper_list: List[dict]) -> List[dict]:
    """
    Deduplicate papers across multiple queries, connectors, and manual imports.
    Matches by clean DOI, falling back to normalized title similarity (>= 0.85).
    Merges every source name, keeps the longest abstract, highest citation count,
    and updates missing metadata fields.
    """
    unique_papers: List[dict] = []

    for p in paper_list:
        title = p.get("title", "")
        clean_doi = normalize_doi(p.get("doi"))

        match_found = False
        for existing in unique_papers:
            ex_clean_doi = normalize_doi(existing.get("doi"))

            doi_match = bool(clean_doi and ex_clean_doi and clean_doi == ex_clean_doi)
            sim = title_similarity(title, existing.get("title", "")) if not doi_match else 1.0

            if doi_match or sim >= 0.80:
                match_found = True
                # Merge sources
                for s in p.get("sources", []):
                    if s not in existing["sources"]:
                        existing["sources"].append(s)

                # Keep longest abstract
                existing_abs = existing.get("abstract", "") or ""
                p_abs = p.get("abstract", "") or ""
                if len(p_abs) > len(existing_abs):
                    existing["abstract"] = p_abs

                # Keep highest citations
                existing["citations"] = max(int(existing.get("citations") or 0), int(p.get("citations") or 0))
                existing["cited_by_count"] = existing["citations"]

                # Populate missing fields
                if not existing.get("doi") and clean_doi:
                    existing["doi"] = clean_doi
                if not existing.get("url") and p.get("url"):
                    existing["url"] = p["url"]
                if not existing.get("pdf_url") and p.get("pdf_url"):
                    existing["pdf_url"] = p["pdf_url"]
                if not existing.get("year") and p.get("year"):
                    existing["year"] = p["year"]
                if not existing.get("date") and p.get("date"):
                    existing["date"] = p["date"]
                if not existing.get("venue") and p.get("venue"):
                    existing["venue"] = p["venue"]

                # Authors: prefer non-empty or longer author list
                ex_authors = existing.get("authors", [])
                p_authors = p.get("authors", [])
                if not ex_authors and p_authors:
                    existing["authors"] = p_authors
                elif len(p_authors) > len(ex_authors):
                    existing["authors"] = p_authors
                break

        if not match_found:
            new_item = dict(p)
            if "sources" not in new_item:
                new_item["sources"] = [new_item.get("source", "Unknown")]
            if clean_doi:
                new_item["doi"] = clean_doi
            unique_papers.append(new_item)

    return unique_papers


# ==========================================
# REPORT FORMATTING & HISTORY PRESERVATION
# ==========================================

def format_run_section(
    candidates: List[dict],
    queries: List[str],
    total_raw: int,
    total_deduped: int,
    source_statuses: Dict[str, dict],
    manual_search_links: List[Tuple[str, str]],
    ph_scope: bool = False,
    import_file: Optional[Path] = None,
) -> str:
    """Formats a markdown section for a single literature check run."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_candidates = [c for c in candidates if not c.get("already_logged")]
    logged_candidates = [c for c in candidates if c.get("already_logged")]

    lines = []
    lines.append(f"## [{timestamp}] — Literature Check Run")
    lines.append("")
    lines.append("**Search Queries:**")
    for q in queries:
        lines.append(f"- `{q}`")
    lines.append("")

    if ph_scope:
        lines.append("**Options:** Philippines Scope (`--ph`) Enabled (OpenAlex-PH, DOAJ-PH)")
        lines.append("")
    if import_file:
        lines.append(f"**Manual Import File:** `{import_file.name}`")
        lines.append("")

    lines.append("**Source Status Summary:**")
    for s_name, s_info in source_statuses.items():
        st = s_info.get("status", "ok")
        count = s_info.get("count", 0)
        note = s_info.get("message", "")
        if st == "ok":
            lines.append(f"- `{s_name}`: ok ({count} result(s))")
        elif st == "skipped":
            lines.append(f"- `{s_name}`: skipped ({note or 'API key not configured'})")
        else:
            lines.append(f"- `{s_name}`: error ({note or 'failed'})")
    lines.append("")

    if manual_search_links:
        lines.append("**Manual Search Links (Lookup by Hand):**")
        for label, url in manual_search_links[:6]:
            lines.append(f"- [{label}]({url})")
        lines.append("")

    lines.append("**Run Statistics:**")
    lines.append(f"- Total Raw Results Fetched: `{total_raw}`")
    lines.append(f"- Unique Candidates Across Sources: `{total_deduped}`")
    lines.append(f"- Genuinely New (Unlogged) Candidates: `{len(new_candidates)}`")
    lines.append(f"- Already in Annotated Bibliography (Filtered): `{len(logged_candidates)}`")
    lines.append("")

    if new_candidates:
        lines.append("### New Candidate Papers for Review")
        lines.append("")
        for idx, paper in enumerate(new_candidates, 1):
            sources_str = ", ".join(paper.get("sources", []))
            authors = paper.get("authors", [])
            authors_str = ", ".join(authors[:4])
            if len(authors) > 4:
                authors_str += " et al."

            lines.append(f"#### {idx}. {paper['title']}")
            lines.append(f"- **Source(s)**: {sources_str}")
            pub_info = paper.get("date") or paper.get("year") or "N/A"
            lines.append(f"- **Publication Date / Year**: {pub_info}")
            if paper.get("venue"):
                lines.append(f"- **Venue**: *{paper['venue']}*")
            if authors_str:
                lines.append(f"- **Authors**: {authors_str}")
            if paper.get("doi"):
                lines.append(f"- **DOI**: [{paper['doi']}](https://doi.org/{paper['doi']})")
            elif paper.get("url"):
                lines.append(f"- **Link**: [{paper['url']}]({paper['url']})")
            if paper.get("pdf_url"):
                lines.append(f"- **PDF Link**: [{paper['pdf_url']}]({paper['pdf_url']})")
            if paper.get("citations"):
                lines.append(f"- **Citations**: {paper['citations']}")

            abstract = paper.get("abstract", "").strip()
            if abstract:
                if len(abstract) > 360:
                    abstract = abstract[:357] + "..."
                lines.append(f"- **Abstract / Summary**: {abstract}")
            lines.append("")
    else:
        lines.append("### New Candidate Papers for Review")
        lines.append("")
        lines.append("*No new unlogged candidates discovered in this run.*")
        lines.append("")

    if logged_candidates:
        lines.append("### Filtered (Already in `annotated-bibliography.md`)")
        lines.append("")
        for paper in logged_candidates:
            sources_str = ", ".join(paper.get("sources", []))
            reason = paper.get("match_reason", "In bibliography")
            lines.append(f"- **{paper['title']}** ({paper.get('year') or 'N/A'}) — *{sources_str}* [{reason}]")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def update_new_candidates_file(new_section: str, output_path: Path) -> None:
    """
    Prepends the new run section to references/new-candidates.md while keeping
    the file header on top and all previous run sections intact below.
    """
    header = (
        "# New Literature Candidates Tracker — Mouse Dynamics Biometrics\n\n"
        "> [!NOTE]\n"
        "> This file tracks newly discovered literature candidates retrieved by `references/example-rrl-fetch.py`.\n"
        "> Candidates are cross-checked against `references/annotated-bibliography.md`. Review new candidates\n"
        "> here and manually promote relevant ones to the bibliography.\n\n"
        "---\n\n"
    )

    if output_path.exists():
        existing_content = output_path.read_text(encoding="utf-8")
        if existing_content.startswith("# New Literature Candidates Tracker"):
            parts = existing_content.split("---\n\n", 1)
            if len(parts) > 1:
                body = parts[1]
            else:
                body = existing_content
        else:
            body = existing_content
    else:
        body = ""

    updated_content = header + new_section + body
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(updated_content, encoding="utf-8")
    print(f"[✓] Saved updated candidate tracker to {output_path}", file=sys.stderr)


# ==========================================
# MAIN PIPELINE & REGISTRY
# ==========================================

AVAILABLE_SOURCES = [
    "arxiv",
    "openalex",
    "semanticscholar",
    "googlescholar",
    "crossref",
    "core",
    "europepmc",
    "pubmed",
    "eric",
    "doaj",
    "dblp",
    "openaire",
    "zenodo",
    "osf",
    "springer",
    "ieee",
]


def normalize_query_list(queries_arg: List[str]) -> List[str]:
    """Normalizes queries passed via CLI or default."""
    result = []
    for q in queries_arg:
        q = q.strip()
        if not q:
            continue
        if ";" in q:
            for sub_q in q.split(";"):
                if sub_q.strip():
                    result.append(sub_q.strip())
        else:
            result.append(q)
    return result or DEFAULT_QUERIES


def run_pipeline(
    queries: List[str],
    sources: List[str],
    limit: int = 10,
    bib_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    serpapi_key: Optional[str] = None,
    s2_key: Optional[str] = None,
    springer_key: Optional[str] = None,
    ieee_key: Optional[str] = None,
    core_key: Optional[str] = None,
    ncbi_key: Optional[str] = None,
    email: Optional[str] = None,
    ph_scope: bool = False,
    import_file: Optional[Path] = None,
    latex_out: Optional[str] = None,
    dry_run: bool = False,
    as_json: bool = False,
    max_workers: int = 8,
) -> List[dict]:
    """Executes the full parallel literature check pipeline."""
    script_dir = Path(__file__).resolve().parent
    if not bib_path:
        bib_path = script_dir / "annotated-bibliography.md"
        if not bib_path.exists():
            bib_path = script_dir.parent / "references" / "annotated-bibliography.md"

    if not output_path:
        output_path = script_dir / "new-candidates.md"
        if not output_path.parent.exists():
            output_path = script_dir.parent / "references" / "new-candidates.md"

    clean_queries = normalize_query_list(queries)
    all_raw_results: List[dict] = []
    source_statuses: Dict[str, dict] = {}

    # Step 1: Extract known papers from annotated-bibliography.md
    logged_data = extract_logged_papers(bib_path)
    print(
        f"[*] Loaded {len(logged_data['titles'])} titles, {len(logged_data['dois'])} DOIs, "
        f"and {len(logged_data['arxiv_ids'])} arXiv IDs from {bib_path.name}",
        file=sys.stderr,
    )

    # Step 2: Process Manual Import file if specified
    if import_file:
        manual_results = import_manual_file(import_file, email=email)
        all_raw_results.extend(manual_results)
        source_statuses["Manual Import"] = {
            "status": "ok",
            "count": len(manual_results),
            "message": f"Loaded from {import_file.name}",
        }

    # Step 3: Determine active sources
    user_sources = set(sources)
    run_all = "all" in user_sources or not sources
    active_sources: Set[str] = set()

    for s in AVAILABLE_SOURCES:
        if run_all or s in user_sources:
            active_sources.add(s)

    if ph_scope:
        active_sources.add("openalex_ph")
        active_sources.add("doaj_ph")

    # Step 4: Dispatch source queries in parallel
    def run_source_task(src_key: str, q: str) -> Tuple[str, str, List[dict], Optional[str]]:
        try:
            if src_key == "arxiv":
                return src_key, "arXiv", fetch_arxiv(q, limit), None
            elif src_key == "openalex":
                return src_key, "OpenAlex", fetch_openalex(q, limit, ph_scope=False, email=email), None
            elif src_key == "openalex_ph":
                return src_key, "OpenAlex-PH", fetch_openalex(q, limit, ph_scope=True, email=email), None
            elif src_key == "semanticscholar":
                return src_key, "Semantic Scholar", fetch_semantic_scholar(q, limit, api_key=s2_key), None
            elif src_key == "crossref":
                return src_key, "Crossref", fetch_crossref(q, limit, email=email), None
            elif src_key == "europepmc":
                return src_key, "Europe PMC", fetch_europe_pmc(q, limit), None
            elif src_key == "pubmed":
                return src_key, "PubMed", fetch_pubmed(q, limit, api_key=ncbi_key), None
            elif src_key == "eric":
                return src_key, "ERIC", fetch_eric(q, limit), None
            elif src_key == "doaj":
                return src_key, "DOAJ", fetch_doaj(q, limit, ph_scope=False), None
            elif src_key == "doaj_ph":
                return src_key, "DOAJ-PH", fetch_doaj(q, limit, ph_scope=True), None
            elif src_key == "dblp":
                return src_key, "DBLP", fetch_dblp(q, limit), None
            elif src_key == "openaire":
                return src_key, "OpenAIRE", fetch_openaire(q, limit), None
            elif src_key == "zenodo":
                return src_key, "Zenodo", fetch_zenodo(q, limit), None
            elif src_key == "osf":
                return src_key, "OSF Preprints", fetch_osf(q, limit), None
            elif src_key == "googlescholar":
                key = serpapi_key or os.environ.get("SERPAPI_KEY")
                if not key:
                    return src_key, "Google Scholar (SerpApi)", [], "SERPAPI_KEY not set"
                return src_key, "Google Scholar (SerpApi)", fetch_google_scholar_serpapi(q, limit, api_key=key), None
            elif src_key == "springer":
                key = springer_key or os.environ.get("SPRINGER_API_KEY")
                if not key:
                    return src_key, "Springer Nature", [], "SPRINGER_API_KEY not set"
                return src_key, "Springer Nature", fetch_springer(q, limit, api_key=key), None
            elif src_key == "ieee":
                key = ieee_key or os.environ.get("IEEE_API_KEY")
                if not key:
                    return src_key, "IEEE Xplore", [], "IEEE_API_KEY not set"
                return src_key, "IEEE Xplore", fetch_ieee(q, limit, api_key=key), None
            elif src_key == "core":
                key = core_key or os.environ.get("CORE_API_KEY")
                if not key:
                    return src_key, "CORE", [], "CORE_API_KEY not set"
                return src_key, "CORE", fetch_core(q, limit, api_key=key), None
        except Exception as e:
            return src_key, src_key, [], str(e)
        return src_key, src_key, [], "Unknown source"

    if clean_queries and active_sources:
        print(
            f"[*] Dispatching {len(clean_queries)} query(ies) across {len(active_sources)} connector(s) in parallel...",
            file=sys.stderr,
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for query in clean_queries:
                for src in active_sources:
                    futures.append(executor.submit(run_source_task, src, query))

            for future in concurrent.futures.as_completed(futures):
                src_key, display_name, items, err_msg = future.result()
                if display_name not in source_statuses:
                    source_statuses[display_name] = {"count": 0, "status": "ok", "message": ""}

                if err_msg and "not set" in err_msg:
                    source_statuses[display_name]["status"] = "skipped"
                    source_statuses[display_name]["message"] = err_msg
                elif err_msg:
                    source_statuses[display_name]["status"] = "error"
                    source_statuses[display_name]["message"] = err_msg
                else:
                    source_statuses[display_name]["count"] += len(items)
                    all_raw_results.extend(items)

    total_raw = len(all_raw_results)

    # Step 5: Deduplicate across all sources and queries
    unique_candidates = deduplicate_and_merge(all_raw_results)
    total_deduped = len(unique_candidates)

    # Step 6: Unpaywall legal PDF enrichment
    enrich_with_unpaywall(unique_candidates, email=email)

    # Step 7: Cross-check against bibliography
    for paper in unique_candidates:
        is_logged, reason = is_already_logged(paper, logged_data)
        paper["already_logged"] = is_logged
        paper["match_reason"] = reason

    # Step 8: Generate manual search links
    search_links = get_manual_search_links(clean_queries)

    # Step 9: LaTeX / BibTeX export if requested
    if latex_out:
        if latex_out == "default":
            export_base = output_path.parent / "rrl_candidates"
        else:
            export_base = Path(latex_out)
        export_latex_and_bibtex(unique_candidates, export_base)

    # Step 10: Output generation
    if as_json:
        print(json.dumps(unique_candidates, indent=2))
        return unique_candidates

    new_section = format_run_section(
        unique_candidates,
        clean_queries,
        total_raw,
        total_deduped,
        source_statuses,
        search_links,
        ph_scope=ph_scope,
        import_file=import_file,
    )

    if dry_run:
        print("\n" + "=" * 50 + " DRY RUN REPORT " + "=" * 50)
        print(new_section)
    else:
        update_new_candidates_file(new_section, output_path)

    new_count = sum(1 for p in unique_candidates if not p.get("already_logged"))
    print(
        f"\n[✓] Pipeline complete! Found {new_count} genuinely new candidate(s) out of {total_deduped} unique papers.",
        file=sys.stderr,
    )
    return unique_candidates


def main():
    parser = argparse.ArgumentParser(
        description="Fetch, deduplicate, and cross-check mouse biometrics literature candidates."
    )
    parser.add_argument(
        "--queries", "-q",
        nargs="+",
        default=DEFAULT_QUERIES,
        help="Search queries to execute (default: %(default)s)",
    )
    parser.add_argument(
        "--sources", "-s",
        nargs="+",
        choices=["all"] + AVAILABLE_SOURCES,
        default=["all"],
        help="Sources to query (default: all)",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Max results per query per source (default: 10)",
    )
    parser.add_argument(
        "--ph",
        action="store_true",
        help="Enable Philippines scope: queries OpenAlex-PH and DOAJ-PH restricted to Philippine institutions and journals",
    )
    parser.add_argument(
        "--import-file",
        default=None,
        help="Path to manual import text file (ResearchGate URLs/slugs, DOIs, pej: titles)",
    )
    parser.add_argument(
        "--latex",
        nargs="?",
        const="default",
        default=None,
        help="Export candidates to LaTeX / BibTeX (<out>.bib and <out>_rrl.tex). Optional path prefix (default: references/rrl_candidates)",
    )
    parser.add_argument(
        "--serpapi-key",
        default=None,
        help="SerpApi key for Google Scholar (or set SERPAPI_KEY env var)",
    )
    parser.add_argument(
        "--s2-key",
        default=None,
        help="Semantic Scholar API key (or set SEMANTIC_SCHOLAR_API_KEY / S2_API_KEY env var)",
    )
    parser.add_argument(
        "--springer-key",
        default=None,
        help="Springer Nature API key (or set SPRINGER_API_KEY env var)",
    )
    parser.add_argument(
        "--ieee-key",
        default=None,
        help="IEEE Xplore API key (or set IEEE_API_KEY env var)",
    )
    parser.add_argument(
        "--core-key",
        default=None,
        help="CORE API key (or set CORE_API_KEY env var)",
    )
    parser.add_argument(
        "--ncbi-key",
        default=None,
        help="NCBI E-utilities API key (or set NCBI_API_KEY env var)",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Contact email for polite pools and Unpaywall (or set RRL_EMAIL env var)",
    )
    parser.add_argument(
        "--bib-path",
        default=None,
        help="Path to annotated-bibliography.md",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Path to new-candidates.md output file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print markdown report to stdout without writing to output file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON to stdout",
    )

    args = parser.parse_args()

    bib_file = Path(args.bib_path) if args.bib_path else None
    out_file = Path(args.output) if args.output else None
    imp_file = Path(args.import_file) if args.import_file else None

    run_pipeline(
        queries=args.queries,
        sources=args.sources,
        limit=args.limit,
        bib_path=bib_file,
        output_path=out_file,
        serpapi_key=args.serpapi_key,
        s2_key=args.s2_key,
        springer_key=args.springer_key,
        ieee_key=args.ieee_key,
        core_key=args.core_key,
        ncbi_key=args.ncbi_key,
        email=args.email,
        ph_scope=args.ph,
        import_file=imp_file,
        latex_out=args.latex,
        dry_run=args.dry_run,
        as_json=args.json,
    )


if __name__ == "__main__":
    main()
