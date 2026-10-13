---
name: academic-writing
description: >-
  Use this skill whenever the user is drafting, revising, editing, restructuring, or reviewing academic prose, thesis chapters (Introduction, Review of Related Literature, Methodology, Results, Discussion, Conclusion), research papers, conference/journal manuscripts, abstracts, thesis defenses, or academic rebuttals. Trigger this skill whenever the user asks to write, rewrite, polish, formalize, or review scholarly content, improve academic tone and hedging, synthesize related literature, ensure mathematical and algorithmic rigor, or adhere to publication guidelines (e.g., IEEE, ACM, APA).
---

# Academic Writing & Manuscript Engineering Assistant

This skill guides the drafting, revision, structural analysis, and mathematical formalization of academic manuscripts, thesis chapters, journal articles, and research proposals. It enforces scholarly rigor, precision, cohesive discourse flow, proper hedging, and publication-standard reporting across scientific and technical disciplines.

---

## Reference Guides in this Skill

For detailed structural blueprints, rhetorical frameworks, and academic phraseology, consult the dedicated references:

- [Academic Style, Tone & Phraseology](references/style-and-tone.md) — Scholarly register, active vs. passive voice balance, epistemic hedging, signposting transitions, and nominalization elimination.
- [Thesis & Academic Paper Chapter Templates](references/chapter-templates.md) — Structural frameworks for Abstract (5-step formula), Introduction (Swales' CARS model), RRL thematic synthesis, Methodology, Experimental Evaluation, and Discussion/Threats to Validity.
- [Academic Argumentation & Literature Synthesis Guide](references/argumentation-and-synthesis.md) — Toulmin argumentation model, thematic synthesis matrices, MEAL paragraph architecture, academic critique, and claim-to-evidence proportionality.

---

## Core Operational Principles

When assisting with any academic writing task, strictly enforce these foundational standards:

### 1. Scholarly Register & Tone
- **Reject Promotional Language:** Eliminate colloquial hyperboles and unsubstantiated marketing phrases (e.g., *"revolutionary"*, *"game-changing"*, *"unprecedented"*, *"incredibly fast"*). Replace with objective, quantifiable characterizations (e.g., *"computationally lightweight"*, *"achieving sub-millisecond latency"*, *"statistically significant improvement"*).
- **Epistemic Calibration (Hedging):** Calibrate assertions to empirical evidence. Use definitive phrasing only for proven theorems or defined parameters; use hedged verbs (*"suggests"*, *"indicates"*, *"tends to exhibit"*) for empirical findings and behavioral interpretations.
- **The Known-New Contract:** Anchor sentences with known or previously established conceptual subjects, and place novel insights or complex technical terms at the sentence conclusion (stress position).

### 2. Literature Synthesis & Citation Integrity
- **Synthesize Thematically, Never Merely Summarize:** Do not present the literature review as a disconnected list of isolated summaries (*"Author A did X. Author B did Y."*). Synthesize thematically (*"While classical approaches [1, 2] relied on aggregated parametric statistics, recent efforts [3, 4] have pivoted toward structural and local geometric representations..."*).
- **Paraphrase with Analytical Voice:** Always translate working notes and bibliography entries into the manuscript's distinctive voice. Never lift raw summary sentences verbatim.
- **Bridge Literature Gaps Directly to Contributions:** Every cited limitation in prior work should serve as rhetorical justification for the chosen methodology.

### 3. Mathematical & Algorithmic Rigor
- **Formal Symbol Definition:** Define every mathematical symbol and variable prior to or immediately following its introduction in an equation.
- **Maintain Notation Consistency:** Standardize notation across all sections (e.g., scalars $s$, vectors $\mathbf{v}$, matrices $\mathbf{M}$, sets $\mathcal{S}$).
- **Document Edge Cases & Safeguards:** For any algorithmic formulation, explicitly detail mathematical failure modes (e.g., zero-division, colinear points, null inputs) and the formal safeguards applied.
- **Pseudocode Standards:** Algorithms must clearly specify `Input`, `Output`, `Preconditions`, step-by-step logic, and asymptotic time and space complexity ($\mathcal{O}$).

---

## Workflow: Drafting & Revising Academic Content

Follow this systematic 5-phase procedure when generating or polishing scholarly drafts:

```
+-------------------------------------------------------------+
| Phase 1: Context & Constraint Verification                   |
| - Verify target section, word/page budget, and audience     |
| - Check relevant literature, bibliography, or draft notes   |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| Phase 2: Argument Outline & Structural Mapping              |
| - Apply appropriate chapter template (e.g., CARS Model)     |
| - Map claims using MEAL paragraph framework                 |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| Phase 3: Drafting with Cohesive Logic & Rigor               |
| - Execute paragraph-by-paragraph draft                       |
| - Embed formal equations, tables, and algorithmic blocks    |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| Phase 4: Line-by-Line Academic Polish                        |
| - Eliminate nominalizations and passive ambiguity           |
| - Smooth discourse connectives and paragraph transitions     |
| - Calibrate hedging and tone precision                      |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| Phase 5: Verification against Academic Polish Checklist     |
+-------------------------------------------------------------+
```

---

## Academic Polish Checklist

Before returning any drafted or revised text to the user, run this internal validation audit:

1. **Clarity & Conciseness:** Are sentences free of wordy filler (e.g., *"in order to"*, *"due to the fact that"*, *"it is interesting to note that"* replaced with *"to"*, *"because"*, *"notably"*)?
2. **Attribution & Evidence:** Is every factual assertion backed by either a specific citation, mathematical deduction, or empirical data point?
3. **Consistency:** Are technical terms, acronyms, and mathematical variables defined at first mention and used uniformly?
4. **Tone & Objectivity:** Has all emotional, defensive, or exaggerated prose been eliminated in favor of calm, scholarly critique?
5. **Formatting:** Are equations properly formatted in LaTeX math syntax, tables clearly titled with column units, and figures captioned with self-contained descriptions?
