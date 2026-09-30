# Literature Source Options — Access Methods & Status

Reference for finding new candidate papers to review for the Review of Related Literature (RRL).
Updated as of September 2026 with expanded automated connectors, Philippines-scoped search,
Unpaywall open-access enrichment, manual import with Crossref verification, and LaTeX export.

| Source | Access Method | Cost / Auth | Status | Config / Env Key | Best For |
|---|---|---|---|---|---|
| **OpenAlex** | REST API, JSON | Free, no key (polite pool via `mailto`) | ✅ Active | Optional `RRL_EMAIL` | Broadest coverage (~250M works); journals, conferences, preprints. **Default source.** |
| **OpenAlex-PH** | REST API (`filter=institutions.country_code:PH`) | Free, no key | ✅ Active (`--ph`) | Optional `RRL_EMAIL` | Philippine institutional publications & local affiliated studies. |
| **arXiv** | Search API, Atom/XML | Free, no key | ✅ Active | None | CS/AI/ML preprints, trajectory analysis, latest algorithms. |
| **Semantic Scholar** | Graph REST API, JSON | Free, rate-limited; optional key | ✅ Active | `SEMANTIC_SCHOLAR_API_KEY` or `S2_API_KEY` | CS/AI/security indexing, citation counts, graph relationships. |
| **Europe PMC** | REST API, JSON (`resultType=core`) | Free, no key | ✅ Active | None | Open biomedical & engineering literature; indexes bioRxiv & medRxiv. |
| **PubMed** | NCBI E-utilities (esearch + efetch XML) | Free, optional key | ✅ Active | Optional `NCBI_API_KEY` | Medical, neuroscience, and motor tremor/kinematic studies. |
| **ERIC** | REST API, JSON | Free, no key | ✅ Active | None | Education & learning interaction literature, behavioral tasks. |
| **DOAJ** | REST API, JSON | Free, no key | ✅ Active | None | Quality open-access peer-reviewed journals globally. |
| **DOAJ-PH** | REST API (`bibjson.journal.country:PH`) | Free, no key | ✅ Active (`--ph`) | None | Open-access peer-reviewed journals based in the Philippines. |
| **Crossref** | REST API, JSON (`/works`) | Free, no key | ✅ Active | Optional `RRL_EMAIL` | Primary DOI registry, bibliographic searches, citation counts. |
| **Zenodo** | REST API, JSON (`/records`) | Free, no key | ✅ Active | None | Open datasets, replication packages, software, and preprints. |
| **OSF Preprints** | REST API, JSON (`filter[title]`) | Free, no key | ✅ Active | None | Open Science Framework preprints & psychology/motor research. |
| **DBLP** | REST API, JSON | Free, no key | ⚠️ Active / Bot-Challenge | None | Comprehensive computer science bibliography. Gracefully handled if bot challenge occurs. |
| **OpenAIRE** | Graph API v1, JSON | Free, no key | ✅ Active | None | European and global open-access research products & datasets. |
| **Google Scholar** | SerpApi (`serpapi.com/google-scholar-api`) | Free tier / paid | 🔑 Key required | `SERPAPI_KEY` | Broadest citation indexing; skips gracefully if key absent. |
| **Springer Nature** | Meta API v2, JSON | Requires developer key | 🔑 Key required | `SPRINGER_API_KEY` | Springer & Nature journals/conferences; skips gracefully if key absent. |
| **IEEE Xplore** | Search API v1, JSON | Requires developer key | 🔑 Key required | `IEEE_API_KEY` | Flagship IEEE security, biometrics, and pattern analysis papers; skips gracefully if key absent. |
| **CORE** | Search API v3, JSON | Requires free account key | 🔑 Key required | `CORE_API_KEY` | Full-text open-access papers and direct PDF downloads; skips gracefully if key absent. |
| **Unpaywall** | REST API, JSON (Enrichment) | Free with email | 📄 PDF Enrichment | `RRL_EMAIL` | Resolves legal, free publisher and repository PDF links from DOIs. |
| **ResearchGate** | Manual import via text file | Manual input | 📋 Manual Import (`--import-file`) | None | No scraping/botting. Extracts title slug and verifies via Crossref. |
| **ejournals.ph** | Manual import via text file | Manual input | 📋 Manual Import (`--import-file`) | None | No scraping/botting. Preserved as verified/unverified stubs. |
| **HERDIN** | Site search link generation | Manual lookup | 🔗 Manual Links | None | Generates Google `site:herdin.ph` search links for Philippine health/biometric literature. |

### Excluded Connectors (Per Project Policy)
- **bioRxiv / medRxiv**: Not implemented as separate connectors because their API lacks keyword search, and Europe PMC already indexes their full preprint collections.
- **Scopus / Lens.org**: Excluded because they mandate paid institutional subscriptions and proprietary authentication.

---

## Command-Line Flags & Options

The automated literature tool lives at `references/example-rrl-fetch.py`.

```bash
# Basic run with default queries across all active free sources
python references/example-rrl-fetch.py

# Run in parallel with custom queries
python references/example-rrl-fetch.py --queries '"mouse dynamics" "authentication"' '"curvature" "mouse trajectory"'

# Enable Philippines Scope (queries OpenAlex-PH and DOAJ-PH)
python references/example-rrl-fetch.py --ph

# Manual import of ResearchGate / ejournals.ph links/DOIs/titles (with Crossref verification)
python references/example-rrl-fetch.py --import-file manual_rrl.txt

# Export results to BibTeX (.bib) and compilable LaTeX skeleton (.tex)
python references/example-rrl-fetch.py --latex references/rrl_candidates

# Query specific connectors only
python references/example-rrl-fetch.py --sources arxiv openalex europepmc crossref pubmed

# Dry-run report to stdout without modifying new-candidates.md
python references/example-rrl-fetch.py --dry-run
```

---

## How Manual Import Works (`--import-file`)

Per platform terms of service and bot protection policies, ResearchGate and Philippine E-Journals (`ejournals.ph`) are **never scraped or automated via headless browsers**. Instead, manual import is used:
1. Student pastes DOIs, titles, or URLs into a text file (`#` for comments).
   - Optional prefixes: `rg: <Title>` or `pej: <Title>`.
   - ResearchGate URLs (`/publication/<id>_<Slug>`) automatically have their title extracted from the URL slug without requesting the page.
2. The script attempts to verify DOIs via Crossref `/works/{doi}` and titles via Crossref `query.bibliographic` (requiring $\ge 80\%$ title similarity).
3. Verified papers are tagged `"ResearchGate (manual)"` or `"ejournals.ph (manual)"`.
4. Unverified papers or opaque links (e.g. `ejournals.ph/article.php?id=...`) are **never dropped silently**; they are retained as candidate stubs labeled `"ResearchGate (manual, unverified)"` or `"ejournals.ph (manual, unverified)"`.
5. Pre-formatted Google `site:` search links for ResearchGate, ejournals.ph, and HERDIN are displayed in every report for easy manual lookup.

---

## LaTeX & BibTeX Export (`--latex`)

When `--latex [out_path]` is specified:
- Generates `<out>.bib` with:
  - Cleaned and escaped LaTeX special characters: `& % $ # _ { } ~ ^ \`
  - Protected title capitalization via double curly braces: `title = {{Title Here}},`
  - Standardized citation keys: `lastname2022firstword` (with collision suffixes `b`, `c`, ...)
  - `@article` when a venue/journal is present, `@misc` otherwise
  - `doi` field when a DOI is available, or `url` only when no DOI exists.
- Generates `<out>_rrl.tex`:
  - Compilable LaTeX document with `\usepackage{natbib}`, `\bibliographystyle{apalike}`, and `\nocite{*}`.
  - Comment list of all citation keys included in the collection.
