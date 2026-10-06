# Literature Source Options — Access Methods & Status

Reference for finding new candidate papers to review for the RRL. Checked directly
(not from training memory) as of 2026-08-31. Re-verify anything time-sensitive (API
status, pricing, access tiers) if it's been a while since this was last checked.

| Source | Access method | Cost/auth | Status | Best for |
|---|---|---|---|---|
| **arXiv** | RSS/Atom feed or Search API | Free, no key | ✅ Working today | Preprints, CS/ML-heavy coverage |
| **OpenAlex** | REST API, JSON | Free, no key (add `mailto=` for faster "polite pool") | ✅ Working today | Broadest coverage — ~250M works, includes IEEE/ACM/Springer/journals, not just preprints. **Best default source.** |
| **Semantic Scholar** | REST API, JSON | Free, no key for basic use (rate-limited; optional `SEMANTIC_SCHOLAR_API_KEY`) | ✅ Working today | Strong CS/AI/security coverage specifically |
| **Google Scholar** | SerpApi (`serpapi.com/google-scholar-api`) | Free tier available (100 searches/mo); requires `SERPAPI_KEY` | ✅ Working via SerpApi | Broadest citation indexing; skips gracefully if key absent |
| **CORE** | REST API, JSON | Free, requires quick signup for a key | ✅ Working today | Full-text/PDF access when available, not just metadata |
| **Crossref** | REST API, JSON | Free, no key | ✅ Working today | DOI-level metadata/citation verification (secondary source) |
| **SciSpace** | REST API, JSON | Early-access/waitlist — not self-serve yet (`docs.api.scispace.com`) | 🟡 Pending | Once available: full-text search, systematic review helpers |
| **Anara** | None | N/A | ❌ Not automatable | Workspace-only product, no external access at all |

## Where the working code lives

`references/example-rrl-fetch.py` implements the four automated sources: arXiv, OpenAlex,
Semantic Scholar, and Google Scholar (via SerpApi). Run it directly, or wire it into a
scheduled GitHub Action (`.github/workflows/literature-checker.yml`).

## How to use this when helping with the thesis

When the user asks to check for new literature ("any new papers on this," "check for
updates," etc.):
1. Run or reference the fetch script's latest output.
2. Cross-check each candidate's title/DOI against `annotated-bibliography.md` — most
   results will already be logged; only genuinely new ones matter.
3. Present new candidates to the user for their own review — don't auto-add anything to
   the annotated bibliography without the user confirming it's relevant and worth
   including (per the skill's plan-first rule).
