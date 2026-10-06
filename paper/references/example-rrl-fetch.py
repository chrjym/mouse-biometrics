#!/usr/bin/env python3
"""
example-rrl-fetch.py — Fetch, deduplicate, and cross-check mouse biometrics candidate literature.

Sources supported:
- arXiv (Search API / Atom XML, free, no key)
- OpenAlex (REST API, free, no key, polite pool via mailto)
- Semantic Scholar (Graph API, free, no key; supports optional SEMANTIC_SCHOLAR_API_KEY)
- Google Scholar via SerpApi (optional, requires SERPAPI_KEY env var or --serpapi-key)

Workflow:
1. Queries all configured sources for primary and secondary thesis search terms.
2. Normalizes and deduplicates results across sources by DOI and fuzzy title similarity.
3. Cross-checks against titles, DOIs, and arXiv IDs in paper/references/annotated-bibliography.md.
4. Filters out known papers and outputs clean, unlogged candidate papers.
5. Prepends new candidate runs to paper/references/new-candidates.md (preserving historical runs).

Usage:
    python paper/references/example-rrl-fetch.py
    python paper/references/example-rrl-fetch.py --dry-run
    python paper/references/example-rrl-fetch.py --queries '"mouse dynamics" "authentication"' '"curvature" "mouse trajectory"'
    python paper/references/example-rrl-fetch.py --sources arxiv openalex semanticscholar
    python paper/references/example-rrl-fetch.py --serpapi-key YOUR_KEY
"""

import argparse
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
from typing import Dict, List, Optional, Set, Tuple

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

USER_AGENT = "ThesisLiteratureChecker/2.0 (mailto:thesis-research@example.edu; academic-thesis-project)"
TIMEOUT_SECONDS = 20


def safe_urlopen(url: str, headers: Optional[dict] = None, timeout: int = TIMEOUT_SECONDS) -> bytes:
    """
    Safely opens a URL with headers, handling Windows SSL certificate store fallbacks.
    """
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except urllib.error.URLError as e:
        err_msg = str(e)
        if "CERTIFICATE_VERIFY_FAILED" in err_msg or "certificate verify failed" in err_msg:
            # Fallback to unverified SSL context if OS root certificates are missing
            import ssl
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                return response.read()
        raise


def normalize_string(text: str) -> str:
    """Normalize string for fuzzy/exact matching by lowercasing and stripping non-alphanumerics."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


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


def extract_logged_papers(bib_path: Path) -> Dict[str, Set[str]]:
    """
    Parses references/annotated-bibliography.md to extract known paper titles, DOIs, and arXiv IDs.
    Filters out markdown section headers and metadata keywords.
    """
    logged_titles: Set[str] = set()
    logged_dois: Set[str] = set()
    logged_arxiv_ids: Set[str] = set()

    if not bib_path.exists():
        print(f"Warning: Annotated bibliography not found at {bib_path}", file=sys.stderr)
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
    for doi in dois:
        clean_doi = doi.lower().rstrip(")., \t\r\n")
        logged_dois.add(clean_doi)

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
    doi = (paper.get("doi") or "").lower().strip()
    if doi:
        clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
        if clean_doi in logged_data["dois"]:
            return True, f"DOI match: {clean_doi}"
        for logged_doi in logged_data["dois"]:
            if clean_doi in logged_doi or logged_doi in clean_doi:
                return True, f"DOI substring match: {clean_doi}"

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
    print(f"[*] Querying arXiv API for: {query} (limit: {limit})...", file=sys.stderr)
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
        xml_data = raw_xml.decode("utf-8")

        root = ET.fromstring(xml_data)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

        for entry in root.findall("atom:entry", ns):
            title_elem = entry.find("atom:title", ns)
            title = re.sub(r"\s+", " ", title_elem.text.strip()) if title_elem is not None and title_elem.text else ""
            if not title:
                continue

            summary_elem = entry.find("atom:summary", ns)
            summary = re.sub(r"\s+", " ", summary_elem.text.strip()) if summary_elem is not None and summary_elem.text else ""

            published_elem = entry.find("atom:published", ns)
            pub_date = published_elem.text.strip()[:10] if published_elem is not None and published_elem.text else ""

            id_elem = entry.find("atom:id", ns)
            paper_url = id_elem.text.strip() if id_elem is not None and id_elem.text else ""

            authors = [
                a.find("atom:name", ns).text.strip()
                for a in entry.findall("atom:author", ns)
                if a.find("atom:name", ns) is not None and a.find("atom:name", ns).text
            ]

            doi_elem = entry.find("arxiv:doi", ns)
            doi = doi_elem.text.strip() if doi_elem is not None and doi_elem.text else None
            if doi and not doi.startswith("http"):
                doi = f"https://doi.org/{doi}"

            results.append({
                "sources": ["arXiv"],
                "title": title,
                "authors": authors,
                "date": pub_date,
                "year": pub_date[:4] if pub_date else "",
                "doi": doi,
                "url": paper_url or doi or "",
                "venue": "arXiv Preprint",
                "abstract": summary,
            })
    except Exception as e:
        print(f"[!] arXiv fetch error: {e}", file=sys.stderr)

    return results


def fetch_openalex(query: str, limit: int = 15) -> List[dict]:
    """Fetch works from OpenAlex REST API."""
    print(f"[*] Querying OpenAlex API for: {query} (limit: {limit})...", file=sys.stderr)
    base_url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "sort": "publication_date:desc",
        "per_page": min(limit, 50),
        "mailto": "thesis-research@example.edu",
    }
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

            results.append({
                "sources": ["OpenAlex"],
                "title": title,
                "authors": authors,
                "date": pub_date,
                "year": str(item.get("publication_year") or pub_date[:4] if pub_date else ""),
                "doi": doi,
                "url": doi or item.get("id") or "",
                "venue": venue,
                "abstract": abstract,
                "cited_by_count": item.get("cited_by_count", 0),
            })
    except Exception as e:
        print(f"[!] OpenAlex fetch error: {e}", file=sys.stderr)

    return results


def fetch_semantic_scholar(query: str, limit: int = 15, api_key: Optional[str] = None) -> List[dict]:
    """Fetch papers from Semantic Scholar Graph API with rate limit handling and optional API key."""
    print(f"[*] Querying Semantic Scholar API for: {query} (limit: {limit})...", file=sys.stderr)
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    fields = "title,authors,year,publicationDate,abstract,externalIds,url,venue,citationCount"
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
    for attempt in range(2):
        try:
            raw_json = safe_urlopen(url, headers=headers, timeout=TIMEOUT_SECONDS)
            data = json.loads(raw_json.decode("utf-8"))

            for item in data.get("data", []):
                title = item.get("title") or ""
                if not title:
                    continue

                ext_ids = item.get("externalIds") or {}
                doi = ext_ids.get("DOI")
                if doi and not doi.startswith("http"):
                    doi = f"https://doi.org/{doi}"

                pub_date = item.get("publicationDate") or ""
                year = str(item.get("year") or pub_date[:4] if pub_date else "")

                authors = [a.get("name") for a in item.get("authors", []) if a.get("name")]
                venue = item.get("venue") or "Conference/Journal"

                results.append({
                    "sources": ["Semantic Scholar"],
                    "title": title,
                    "authors": authors,
                    "date": pub_date,
                    "year": year,
                    "doi": doi,
                    "url": item.get("url") or doi or "",
                    "venue": venue,
                    "abstract": item.get("abstract") or "",
                    "cited_by_count": item.get("citationCount", 0),
                })
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                print("[*] Semantic Scholar rate-limited (429). Waiting 3 seconds before retry...", file=sys.stderr)
                time.sleep(3)
                continue
            else:
                print(f"[!] Semantic Scholar fetch error (HTTP {e.code}): {e.reason}", file=sys.stderr)
                break
        except Exception as e:
            print(f"[!] Semantic Scholar fetch error: {e}", file=sys.stderr)
            break

    return results


def fetch_google_scholar_serpapi(query: str, limit: int = 15, api_key: Optional[str] = None) -> List[dict]:
    """
    Fetch papers from Google Scholar via SerpApi.
    Requires SERPAPI_KEY. Gracefully skips if key is not provided.
    """
    key = api_key or os.environ.get("SERPAPI_KEY")
    if not key:
        print("[*] SERPAPI_KEY not set. Skipping Google Scholar (SerpApi). Set SERPAPI_KEY to enable.", file=sys.stderr)
        return []

    print(f"[*] Querying Google Scholar via SerpApi for: {query} (limit: {limit})...", file=sys.stderr)
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

            results.append({
                "sources": ["Google Scholar (SerpApi)"],
                "title": title,
                "authors": authors,
                "date": year,
                "year": year,
                "doi": doi,
                "url": link,
                "venue": summary_text[:60] if summary_text else "Google Scholar",
                "abstract": snippet,
            })
    except Exception as e:
        print(f"[!] Google Scholar (SerpApi) fetch error: {e}", file=sys.stderr)

    return results


# ==========================================
# DEDUPLICATION & MERGING
# ==========================================

def deduplicate_and_merge(paper_list: List[dict]) -> List[dict]:
    """
    Deduplicate papers across multiple queries and sources.
    Merges sources, abstract, author, and date metadata when matches are found.
    """
    unique_papers: List[dict] = []

    for p in paper_list:
        title = p.get("title", "")
        doi = (p.get("doi") or "").lower().strip()
        clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()

        match_found = False
        for existing in unique_papers:
            ex_doi = (existing.get("doi") or "").lower().strip()
            ex_clean_doi = ex_doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()

            doi_match = bool(clean_doi and ex_clean_doi and clean_doi == ex_clean_doi)
            sim = title_similarity(title, existing.get("title", ""))

            if doi_match or sim >= 0.85:
                match_found = True
                for s in p.get("sources", []):
                    if s not in existing["sources"]:
                        existing["sources"].append(s)

                if not existing.get("doi") and p.get("doi"):
                    existing["doi"] = p["doi"]
                if not existing.get("url") and p.get("url"):
                    existing["url"] = p["url"]
                if not existing.get("date") and p.get("date"):
                    existing["date"] = p["date"]
                if not existing.get("year") and p.get("year"):
                    existing["year"] = p["year"]
                if not existing.get("venue") and p.get("venue"):
                    existing["venue"] = p["venue"]
                if not existing.get("abstract") and p.get("abstract"):
                    existing["abstract"] = p["abstract"]
                elif existing.get("abstract") and p.get("abstract") and len(p["abstract"]) > len(existing["abstract"]):
                    existing["abstract"] = p["abstract"]
                if not existing.get("authors") and p.get("authors"):
                    existing["authors"] = p["authors"]
                break

        if not match_found:
            if "sources" not in p:
                p["sources"] = [p.get("source", "Unknown")]
            unique_papers.append(p)

    return unique_papers


# ==========================================
# REPORT FORMATTING & HISTORY PRESERVATION
# ==========================================

def format_run_section(candidates: List[dict], queries: List[str], total_raw: int, total_deduped: int) -> str:
    """Formats a markdown section for a single run."""
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
    lines.append(f"**Run Statistics:**")
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
            authors_str = ", ".join(paper.get("authors", [])[:4])
            if len(paper.get("authors", [])) > 4:
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
                lines.append(f"- **DOI / Link**: [{paper['doi']}]({paper['doi']})")
            elif paper.get("url"):
                lines.append(f"- **Link**: [{paper['url']}]({paper['url']})")

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
        for idx, paper in enumerate(logged_candidates, 1):
            sources_str = ", ".join(paper.get("sources", []))
            reason = paper.get("match_reason", "In bibliography")
            lines.append(f"- **{paper['title']}** ({paper.get('year') or 'N/A'}) — *{sources_str}* [{reason}]")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def update_new_candidates_file(new_section: str, output_path: Path) -> None:
    """
    Prepends the new run section to paper/references/new-candidates.md while keeping
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
# MAIN RUNNER
# ==========================================

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
    dry_run: bool = False,
    as_json: bool = False,
) -> List[dict]:
    """Executes the full literature check pipeline."""
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

    # Step 1: Extract known papers from annotated-bibliography.md
    logged_data = extract_logged_papers(bib_path)
    print(f"[*] Loaded {len(logged_data['titles'])} titles, {len(logged_data['dois'])} DOIs, and {len(logged_data['arxiv_ids'])} arXiv IDs from {bib_path.name}", file=sys.stderr)

    # Step 2: Fetch papers across all queries and sources
    all_raw_results: List[dict] = []
    selected_sources = set(sources) if sources and "all" not in sources else {"arxiv", "openalex", "semanticscholar", "googlescholar"}

    for query in clean_queries:
        print(f"\n========================================\n[*] Executing Query: {query}\n========================================", file=sys.stderr)

        if "arxiv" in selected_sources:
            all_raw_results.extend(fetch_arxiv(query, limit))
            time.sleep(1.5)

        if "openalex" in selected_sources:
            all_raw_results.extend(fetch_openalex(query, limit))
            time.sleep(1.0)

        if "semanticscholar" in selected_sources:
            all_raw_results.extend(fetch_semantic_scholar(query, limit, api_key=s2_key))
            time.sleep(1.0)

        if "googlescholar" in selected_sources:
            all_raw_results.extend(fetch_google_scholar_serpapi(query, limit, api_key=serpapi_key))
            time.sleep(1.0)

    total_raw = len(all_raw_results)

    # Step 3: Deduplicate across sources
    unique_candidates = deduplicate_and_merge(all_raw_results)
    total_deduped = len(unique_candidates)

    # Step 4: Cross-check against bibliography
    for paper in unique_candidates:
        is_logged, reason = is_already_logged(paper, logged_data)
        paper["already_logged"] = is_logged
        paper["match_reason"] = reason

    # Step 5: Output generation
    if as_json:
        print(json.dumps(unique_candidates, indent=2))
        return unique_candidates

    new_section = format_run_section(unique_candidates, clean_queries, total_raw, total_deduped)

    if dry_run:
        print("\n" + "=" * 50 + " DRY RUN REPORT " + "=" * 50)
        print(new_section)
    else:
        update_new_candidates_file(new_section, output_path)

    new_count = sum(1 for p in unique_candidates if not p.get("already_logged"))
    print(f"\n[✓] Pipeline complete! Found {new_count} genuinely new candidate(s) out of {total_deduped} unique papers.", file=sys.stderr)
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
        choices=["all", "arxiv", "openalex", "semanticscholar", "googlescholar"],
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
        "--serpapi-key",
        default=None,
        help="SerpApi API key for Google Scholar (or set SERPAPI_KEY env var)",
    )
    parser.add_argument(
        "--s2-key",
        default=None,
        help="Semantic Scholar API key (or set SEMANTIC_SCHOLAR_API_KEY / S2_API_KEY env var)",
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

    run_pipeline(
        queries=args.queries,
        sources=args.sources,
        limit=args.limit,
        bib_path=bib_file,
        output_path=out_file,
        serpapi_key=args.serpapi_key,
        s2_key=args.s2_key,
        dry_run=args.dry_run,
        as_json=args.json,
    )


if __name__ == "__main__":
    main()
