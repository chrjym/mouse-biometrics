# Measuring Behavioral Fingerprints of Users in Mouse Trajectories for Continuous Authentication

[![Python 3.11](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Status: Experimental Model](https://img.shields.io/badge/Status-Experimental%20Model-orange.svg)]()
[![Domain: Behavioral Biometrics](https://img.shields.io/badge/Domain-Continuous%20Authentication-green.svg)]()

---

## 1. Title & Overview

* **Project Title:** Measuring Behavioral Fingerprints of Users in Mouse Trajectories for Continuous Authentication
* **Research Domain:** Continuous Behavioral Biometrics, Post-Login Workstation Security, and Neuromuscular Mannerism Capture.

### Summary
Traditional perimeter security mechanisms (passwords, PINs, static biometrics) verify user identity solely at initial session login. Once an operator is authenticated, host operating systems remain blind to unauthorized console takeovers, session hijacking, or automated peripheral injection. 

This research investigates an **explainable, continuous authentication model** that passively monitors user identity throughout an active session. Instead of relying on multi-minute statistical aggregations or opaque deep learning black boxes, this study captures individual **behavioral fingerprints directly from short, sub-second mouse trajectory strokes** using closed-form differential geometry, convex hull spatial bounding, Discrete Fréchet curve morphometry, and dynamic thresholding.

---

## 2. Core Methodology & Architecture Pipeline

The proposed experimental model processes cursor movements through an end-to-end 5-stage pipeline:

$$\text{Short-Signal Capture} \longrightarrow \text{Closed-Form Geometry} \longrightarrow \text{Convex Hull Bounding} \longrightarrow \text{Fréchet Morphometry} \longrightarrow \text{Dynamic Thresholding}$$

```
+---------------------------------------------------------------------------------------------------+
|                                  CONTINUOUS AUTHENTICATION PIPELINE                               |
+-------------------+--------------------+--------------------+--------------------+----------------+
| 1. Short-Signal   | 2. Closed-Form     | 3. Convex Hull     | 4. Fréchet         | 5. Dynamic     |
|    Capture        |    Geometry        |    Bounding        |    Morphometry     |    Threshold   |
|                   |                    |                    |                    |                |
| Point-to-point    | Menger Curvature,  | 2D Minimum polygon | Discrete Fréchet   | Calibrated     |
| stroke segment    | Chord Deviation,   | for gross spatial  | Distance with      | per-action     |
| (< 1.0s window)   | Straightness Ratio | dispersion         | point-ordering     | trust score    |
+-------------------+--------------------+--------------------+--------------------+----------------+
```

1. **Short-Signal Capture:** Segments continuous desktop mouse movement into atomic, point-to-point trajectory strokes (sub-second duration) between clicks, pauses, or sharp direction reversals.
2. **Closed-Form Geometry Extraction:** Computes localized, closed-form differential-geometric mannerisms on each stroke with explicit safeguards against division-by-zero and collinearity:
   - **Orthogonal Chord Deviation ($d_\perp$):** Perpendicular displacement from the baseline chord connecting the stroke's initial and final coordinates.
   - **Discrete Menger Curvature ($\kappa$):** Triplet circumcircle curvature capturing fine motor tremor and localized inflection points.
   - **Straightness Ratio ($S$):** Ratio of net Euclidean displacement to total cumulative path length.
3. **Convex Hull Bounding:** Wraps a minimum 2D convex polygon around the trajectory coordinates to encapsulate gross spatial dispersion, path variance, and motor overshoot.
4. **Fréchet Morphometry:** Evaluates candidate bounded trajectory curves against the user's enrolled profile using **Discrete Fréchet Distance ($\delta_F$)**, strictly preserving monotonic temporal point progression without the artificial velocity distortions common to elastic time warping.
5. **Dynamic Thresholding:** Compares curve dissimilarity scores against a calibrated decision threshold feeding a per-action dynamic trust accumulator, allowing gradual behavioral drift (such as motor fatigue) while immediately flagging anomalous stroke sequences.

---

## 3. Repository Directory Layout

```
thesis-mouse-biometrics/
├── README.md                                  # Repository overview, architecture, and guide (this file)
├── references/                                # Academic literature, surveys, and chapter drafts
│   ├── adviser-log.md                         # Running log of adviser feedback, scope guidance, and decisions
│   ├── background_pure_paragraphs.md          # Cited Chapter 1 Background of the Study (IEEE format)
│   ├── measurement-comparison-survey.md       # Consolidated survey of mouse measurements vs. matching methods
│   ├── rrl-candidate-papers.md                # 20 curated and fact-checked RRL sources (2018–2026)
│   ├── literature-sources.md                  # Academic APIs, queries, and fetch documentation
│   └── example-rrl-fetch.py                   # Automated literature fetch and deduplication script
├── scripts/                                   # Operational command-line utilities
│   └── audit_writing.py                       # Pre-flight AI writing cadence & Turnitin sensitivity auditor
├── .agents/                                   # Specialized agent workflows and skill configurations
│   └── skills/
│       ├── mouse-biometrics-thesis/           # Primary skill for thesis domain, adviser logs, and RRL
│       ├── academic-writing/                  # Academic tone, chapter templates, and publication standards
│       └── humanize-academic-writing/         # Natural burstiness, anti-AI patterns, and cadence rules
└── .github/workflows/
    └── literature-checker.yml                 # Automated GitHub Actions workflow for weekly literature fetching
```

---

## 4. Tooling & Usage Guide

### 4.1 Running the Local AI Writing Cadence Auditor
An offline Python utility is provided to audit thesis chapter drafts against Turnitin sensitivity, uniform sentence lengths (low burstiness), and banned LLM cliché n-grams:

```powershell
# Run basic audit on a chapter draft
python scripts/audit_writing.py references/background_pure_paragraphs.md

# Run with detailed paragraph-by-paragraph breakdown
python scripts/audit_writing.py references/background_pure_paragraphs.md -v

# Output results in machine-readable JSON
python scripts/audit_writing.py references/background_pure_paragraphs.md --json
```

### 4.2 Fetching New Literature Candidates
To query academic APIs, import manual entries, and cross-check new candidate papers against the compiled bibliography:

```powershell
# Run literature checker with default queries across all active free sources
python references/example-rrl-fetch.py

# Query custom topics with increased limit
python references/example-rrl-fetch.py --queries '"mouse dynamics" "authentication"' '"curvature" "mouse trajectory"' --limit 15

# Enable Philippines scope (queries OpenAlex-PH and DOAJ-PH)
python references/example-rrl-fetch.py --ph

# Import manual ResearchGate / ejournals.ph entries (with Crossref verification)
python references/example-rrl-fetch.py --import-file manual_rrl.txt

# Export candidate papers to BibTeX (.bib) and compilable LaTeX skeleton (.tex)
python references/example-rrl-fetch.py --latex references/rrl_candidates

# Run specific connectors only
python references/example-rrl-fetch.py --sources arxiv openalex europepmc pubmed crossref doaj

# Dry-run report to stdout without writing to new-candidates.md
python references/example-rrl-fetch.py --dry-run
```

#### Supported Connectors & Keys
* **Free / No Key:** OpenAlex, arXiv, Semantic Scholar, Europe PMC, PubMed (NCBI), ERIC, DOAJ, DBLP, OpenAIRE, Zenodo, OSF Preprints, Crossref.
* **Optional / Key-Required:** Google Scholar (`SERPAPI_KEY`), Springer Nature (`SPRINGER_API_KEY`), IEEE Xplore (`IEEE_API_KEY`), CORE (`CORE_API_KEY`), Semantic Scholar (`SEMANTIC_SCHOLAR_API_KEY`), NCBI (`NCBI_API_KEY`).
* **Enrichment:** Unpaywall (`RRL_EMAIL`) automatically adds legal, free publisher and repository PDF links.
* **Manual Import:** ResearchGate, ejournals.ph, and HERDIN via text files without violating bot/scraping policies.

See [`references/literature-sources.md`](file:///home/tin/thesis-mouse-biometrics/references/literature-sources.md) for full endpoint specifications, access methods, and policy details.

---

## 5. Baseline Academic References

* **Survey Baseline:** M. A. Khan et al., *"Mouse Dynamics Behavioral Biometrics: A Survey of Methodologies, Challenges, and Opportunities,"* *ACM Computing Surveys*, 2024.
* **Short-Unit Segmentation:** Y. Wang et al., *"Optimizing Mouse Dynamics for User Authentication: LT-AMouse via Mouse Authentication Units,"* *arXiv:2504.21415*, 2025.
* **Neuromotor Modeling:** M. Djioua & R. Plamondon, *"Kinematic Neuromotor Modeling of Rapid Mouse Trajectory Strokes,"* *IEEE TSMC*, 2019.
* **Differential Geometry:** E. Asgarov, *"Mathematical Feature Representations of Mouse Dynamics,"* *JPIT*, 2026.
* **Curve Morphometry:** H. Alt & M. Godau, *"Computing the Fréchet distance between two polygonal curves,"* *IJFCS*, 1995.
