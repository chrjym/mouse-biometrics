---
name: humanize-academic-writing
description: >-
  Use this skill whenever drafting, revising, or rewriting academic prose, thesis sections, research papers, or essays to produce natural, human-authentic prose that avoids AI detection patterns (e.g., Turnitin, GPTZero, Copyleaks, Originality.ai). Trigger this skill when the user asks to bypass AI detectors, humanize text, eliminate AI tone/markers, increase burstiness and perplexity, remove robotic or formulaic phrasing, or make academic sentences sound authentically authored by a human scholar.
---

# Humanized Academic Writing Assistant (Anti-AI Detector Protocol)

This skill provides operational rules, syntactic strategies, and phraseological transformations to produce **rigorous, publication-grade academic prose** that reads naturally and bypasses automated AI detectors (e.g., Turnitin AI Detection, GPTZero, Copyleaks, Crossplag, Originality.ai).

Rather than superficial paraphrasing or synonym swapping (which often introduces unscholarly or awkward phrasing), this skill targets the **core statistical features** that AI detectors measure: **low perplexity (overly predictable token sequences)**, **uniform sentence lengths (low burstiness)**, and **formulaic rhetorical templates**.

---

## Reference Guides in this Skill

- [AI Detection Mechanisms & Classifier Vulnerabilities](references/ai-detector-mechanisms.md) — How detectors calculate perplexity, burstiness, log-probability distributions, and syntactic uniformity.
- [Human Cadence, Syntax Variation & Anti-Cliché Rules](references/human-cadence-and-patterns.md) — Concrete rewrite patterns, sentence length distribution targets, asymmetric paragraph structures, and blacklisted AI phraseology.

---

## The Four Golden Pillars of Humanized Academic Prose

```
                     +---------------------------------------+
                     |    HUMANIZED SCHOLARLY WRITING        |
                     +---------------------------------------+
                                         |
     +-------------------+---------------+-------------------+-------------------+
     |                   |                                   |                   |
+----+----+         +----+----+                         +----+----+         +----+----+
| 1. High |         | 2. Zero |                         | 3. Asym-|         | 4. Con- |
| Burst-  |         | AI Buzz-|                         | metric  |         | crete   |
| iness   |         | words   |                         | Syntax  |         | Density |
+---------+         +---------+                         +---------+         +---------+
 (Vary sentence      (Ban "delve",                       (Break parallel     (Ground in
  length 6 to         "crucial role",                     triplets and        specific
  38 words)           "testament", etc.)                  predictable lists)  mechanisms)
```

---

## 1. Maximize Burstiness (Sentence Length Rhythms)

AI models generate text with consistent, uniform sentence lengths (typically 18–25 words per sentence), creating a flat, monotonous rhythm that triggers detector classifiers.

### The Human Rhythm Rule
Always interlock **very short, impactful sentences** with **longer, multi-clause complex sentences**:
- **Short anchor sentence:** 6–11 words. Delivers a punchy, decisive thesis or pivot.
- **Moderate sentence:** 14–22 words. Provides context or evidence.
- **Complex composite sentence:** 28–38 words. Balances dependent clauses, conditional relationships, or comparative syntheses.

> **Example Human Rhythm:**  
> *"Authentication cannot rely on static perimeters. While biometric physiological traits like fingerprints or facial geometry offer high initial assurance at the login gate, they remain completely blind to subsequent physical device takeovers, credential theft, or unauthorized terminal access during an active session [1], [2]. The workstation assumes the original operator is still present. This assumption is flawed."*

---

## 2. Eliminate AI Clichés and Dead Giveaways

AI detectors flag specific high-frequency transition markers, pseudo-profound verbs, and rhetorical scaffolding. Never use the terms on the left; use the human academic alternatives on the right:

| Dead Giveaway AI Words (BANNED) | Authentic Academic Replacements |
| :--- | :--- |
| *Delve into / Delving* | Examine, analyze, investigate, evaluate, assess |
| *Pivotal / Crucial role* | Essential mechanism, primary factor, functional baseline |
| *A testament to...* | Demonstrates, provides empirical evidence for, reflects |
| *Intricate tapestry / Interplay* | Interaction, structural coupling, dynamic dependency |
| *Beacon of hope / Game-changer* | Viable framework, operational alternative |
| *Furthermore, Moreover, Additionally (overuse)* | Vary with clause integration, *"Simultaneously"*, *"In parallel"*, *"Equally problematic is..."* |
| *In conclusion / To sum up* | Concluding paragraph integrated without meta-announcements |
| *It is important / vital to remember* | State the finding directly without the meta-commentary |
| *Shed light on* | Clarify, illuminate, resolve, explicate |
| *Ever-evolving landscape* | Dynamic environment, shifting operational requirements |
| *Holistic approach* | Integrated framework, comprehensive protocol |

---

## 3. Break Parallelism & The "Rule of Three" Habit

A hallmark of LLM generation is the compulsive creation of balanced triplets (*"analyzing data, optimizing parameters, and verifying accuracy"* or *"comprehensive, robust, and reliable"*). 

### How to Break It:
1. **Asymmetric Enumerations:** Use two elements or four elements, never standard symmetric triplets.
2. **Shift Part-of-Speech:** Instead of three parallel gerunds (*"evaluating, calculating, and deciding"*), use an action noun followed by an infinitive clause (*"trajectory evaluation followed by dynamic threshold calibration to reach an authentication decision"*).
3. **Embed Interruptions:** Insert parenthetical thoughts, em-dashes, or qualifying clauses between items (*"chord deviation—specifically its orthogonal maximum—and discrete Menger curvature"*).

---

## 4. Increase Perplexity (Unpredictable, Scholarly Lexical Choices)

Perplexity measures how surprised a language model is by the next word. High perplexity = human writing. Low perplexity = AI writing.

### Strategies to Increase Natural Perplexity:
1. **Domain-Specific Mathematical & Physical Nouns:** Use precise nomenclature (*"orthogonality"*, *"monotonic ordering"*, *"circumradius"*, *"stochastic drift"*, *"discretization jitter"*) rather than vague concepts (*"strong security"*, *"effective calculation"*).
2. **Inverted Subject-Verb Configurations:**  
   - *AI-typical (Predictable):* *"The curvature increases when the hand accelerates."*
   - *Human-inverted (Unpredictable):* *"With hand acceleration comes an abrupt, localized elevation in trajectory curvature."*
3. **Subordinate Front-Loading:** Start sentences with prepositional, participial, or concessive clauses rather than standard `Subject + Verb + Object`:
   - *"Granted that single strokes suffer from sensor jitter, consecutive action accumulation nevertheless mitigates transient error."*
   - *"Operating strictly beneath the 1-second threshold, discrete strokes isolate self-contained motor intentions."*

---

## 5. Revision Checklist for Any Draft

Before finalizing any paragraph:
- [ ] Are sentence lengths varied between 6 words and 35+ words?
- [ ] Are words like *"delve"*, *"crucial role"*, *"testament"*, and *"tapestry"* 100% absent?
- [ ] Are transition words (*"Furthermore"*, *"Moreover"*) used at most once per page?
- [ ] Does the paragraph avoid balanced, three-item bullet lists or triplet phrases?
- [ ] Are claims supported with concrete figures, citations, or formulas rather than generic adjectives?
- [ ] Is there at least one sentence beginning with an adverbial, participial, or concessive clause?

---

## 6. Automated Pre-Flight Auditor CLI

A local audit script is provided at `paper/tools/audit_writing.py` to evaluate draft files (`.md`, `.tex`, `.txt`) against Turnitin and classifier triggers before submission:

```powershell
# Basic audit on any thesis draft or chapter
python paper/tools/audit_writing.py path/to/chapter.md

# Detailed paragraph-by-paragraph breakdown
python paper/tools/audit_writing.py path/to/chapter.md -v

# JSON output for automated pipelines
python paper/tools/audit_writing.py path/to/chapter.md --json
```

The auditor evaluates:
1. **Burstiness ($\sigma^2$ variance & standard deviation)** — flags uniform sentence lengths.
2. **AI Cliché n-grams** — catalogs dead giveaways and outputs scholarly replacements.
3. **Flat sentence streaks** — flags 3+ consecutive sentences within $\pm 3$ words of each other.
4. **Symmetric triplets & rule-of-three patterns**.
5. **Syntactic fronting ratio**.

