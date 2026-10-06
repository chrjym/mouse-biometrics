#!/usr/bin/env python3
"""
Pre-Flight Thesis AI Writing Auditor (Turnitin & Classifier Pre-check)
Analyzes Markdown, LaTeX, and plain text files for statistical markers
measured by academic AI detectors (sentence burstiness, predictability, 
banned cliché n-grams, and repetitive syntactic structures).
"""

import os
import sys
import re
import math
import argparse
import json
from typing import List, Dict, Any, Tuple

# Ensure proper UTF-8 handling on Windows consoles
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# ANSI color codes for readable terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

# Check if colors should be enabled
USE_COLOR = sys.stdout.isatty() and os.name != 'nt' or os.environ.get('TERM') != ''

def colorize(text: str, color_code: str) -> str:
    if USE_COLOR:
        return f"{color_code}{text}{Colors.RESET}"
    return text

# Catalog of known AI classifier trigger n-grams and suggested academic replacements
BANNED_CLICHES = {
    # High-priority LLM dead giveaways
    r"\bdelv(e|es|ed|ing)\s+into\b": {
        "phrase": "delve into",
        "weight": 18,
        "replace": "examine, investigate, scrutinize, evaluate, assess",
        "note": "Virtually exclusive to LLM generation in academic writing."
    },
    r"\b(pivotal|crucial|vital)\s+role\b": {
        "phrase": "pivotal/crucial/vital role",
        "weight": 14,
        "replace": "central function, primary factor, functional baseline, key constraint",
        "note": "Massively over-indexed in AI models."
    },
    r"\btestament\s+to\b": {
        "phrase": "testament to",
        "weight": 15,
        "replace": "evidence of, demonstrates, substantiates, illustrates",
        "note": "Melodramatic trope heavily flagged by classifiers."
    },
    r"\b(intricate\s+tapestry|tapestry\s+of)\b": {
        "phrase": "tapestry / intricate tapestry",
        "weight": 16,
        "replace": "complex interaction, structural dependency, configuration",
        "note": "Known signature LLM metaphor."
    },
    r"\binterplay\b": {
        "phrase": "interplay",
        "weight": 8,
        "replace": "interaction, structural coupling, dynamic dependency",
        "note": "High-frequency AI buzzword."
    },
    r"\bit\s+is\s+(important|vital|crucial|essential|worth\s+noting)\s+to\s+(note|remember|mention|highlight|understand)\b": {
        "phrase": "it is important to note/remember",
        "weight": 12,
        "replace": "notably, specifically, or state the finding directly without preamble",
        "note": "Rhetorical filler that raises predictable sequence probability."
    },
    r"\bfoster(s|ed|ing)?\s+a\s+(deeper|better|robust|comprehensive)\b": {
        "phrase": "foster(s/ing) a ...",
        "weight": 10,
        "replace": "promotes, yields, generates, facilitates",
        "note": "Common corporate/AI generative template."
    },
    r"\bunderscores?\s+the\s+importance\b": {
        "phrase": "underscores the importance",
        "weight": 12,
        "replace": "highlights, demonstrates, emphasizes the necessity of",
        "note": "Generic boilerplate summary phrase."
    },
    r"\brich\s+nuances\b": {
        "phrase": "rich nuances",
        "weight": 12,
        "replace": "subtle variations, idiosyncratic discrepancies",
        "note": "Vague qualitative praise typical of AI."
    },
    r"\b(beacon\s+of\s+hope|game-?changer|transformative\s+solution)\b": {
        "phrase": "beacon / game-changer / transformative",
        "weight": 15,
        "replace": "viable framework, operational alternative, baseline model",
        "note": "Unsubstantiated hyperbole."
    },
    r"\bever-?evolving\s+landscape\b": {
        "phrase": "ever-evolving landscape",
        "weight": 15,
        "replace": "dynamic environment, shifting operational requirements",
        "note": "Common LLM cliché."
    },
    r"\bholistic\s+approach\b": {
        "phrase": "holistic approach",
        "weight": 9,
        "replace": "integrated framework, comprehensive protocol, unified model",
        "note": "Frequently overused in generative text."
    },
    r"\bshed(s|ding)?\s+light\s+on\b": {
        "phrase": "shed light on",
        "weight": 10,
        "replace": "clarify, illuminate, resolve, explicate",
        "note": "Idiomatic filler common in AI drafts."
    },
    r"\b(in\s+conclusion|to\s+sum\s+up|in\s+summary),\s*": {
        "phrase": "in conclusion / to sum up",
        "weight": 8,
        "replace": "Integrate conclusion smoothly without explicit meta-announcements",
        "note": "Mechanical transition typical of elementary AI structuring."
    }
}

# Subordinate / non-standard clause openers for checking fronting
FRONTED_OPENERS = {
    'while', 'although', 'though', 'despite', 'whereas', 'because', 'since',
    'given', 'granted', 'by', 'to', 'through', 'operating', 'using', 'applying',
    'with', 'in', 'under', 'upon', 'after', 'before', 'without', 'for', 'at'
}

STANDARD_SUBJECT_OPENERS = {
    'the', 'this', 'these', 'those', 'it', 'we', 'our', 'they', 'their', 'such',
    'a', 'an', 'many', 'most', 'some', 'several'
}

def clean_text_for_analysis(raw_text: str, file_ext: str) -> str:
    """Strip markup and format artifacts while preserving sentence boundaries."""
    text = raw_text

    # Exclude Bibliography/References section (mirroring Turnitin's 'Exclude Bibliography' setting)
    ref_heading_match = re.search(r'(?i)^\s*#{1,6}\s*(references|bibliography|works\s+cited)\b', text, flags=re.MULTILINE)
    if ref_heading_match:
        text = text[:ref_heading_match.start()]
    
    # Clean LaTeX markup if applicable
    if file_ext in ('.tex', '.latex'):
        # Strip comments
        text = re.sub(r'%.*$', '', text, flags=re.MULTILINE)
        # Strip inline and display math
        text = re.sub(r'\$\$.*?\$\$', ' [MATH] ', text, flags=re.DOTALL)
        text = re.sub(r'\$.*?\$', ' [MATH] ', text)
        # Strip common LaTeX environments
        text = re.sub(r'\\begin\{(equation|align|table|figure)\*?\}.*?\\end\{\1\*?\}', ' ', text, flags=re.DOTALL)
        # Strip commands like \cite{...}, \ref{...}, \textbf{...}
        text = re.sub(r'\\[a-zA-Z]+\*?(?:\[.*?\])?\{([^}]*)\}', r'\1', text)
        text = re.sub(r'\\[a-zA-Z]+', ' ', text)

    # Clean Markdown markup
    elif file_ext in ('.md', '.markdown'):
        # Strip code blocks
        text = re.sub(r'```.*?```', ' ', text, flags=re.DOTALL)
        text = re.sub(r'`.*?`', ' ', text)
        # Strip images and links [text](url) -> text
        text = re.sub(r'!\[.*?\]\(.*?\)', ' ', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Strip headers (# Header)
        text = re.sub(r'^\s*#{1,6}\s+.*$', '', text, flags=re.MULTILINE)
        # Strip horizontal rules
        text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
        # Strip bold/italic markers
        text = re.sub(r'[*_]{1,3}', '', text)
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)

    return text

def split_into_paragraphs(cleaned_text: str) -> List[str]:
    """Split text into substantive paragraphs (ignoring single short lines or headers)."""
    raw_paras = [p.strip() for p in re.split(r'\n\s*\n', cleaned_text)]
    # Filter out empty or trivial one-line fragments (like table rows or stray titles)
    return [p for p in raw_paras if len(p.split()) >= 15]

def split_into_sentences(paragraph: str) -> List[str]:
    """Split a paragraph into sentences with robust punctuation boundary detection."""
    # Protect common abbreviations: e.g., i.e., et al., Fig., Eq., etc.
    p = re.sub(r'\b(e\.g\.|i\.e\.|et al\.|Fig\.|Eq\.|vs\.|al\.)\s*', lambda m: m.group(0).replace('.', '__DOT__'), paragraph)
    # Protect numbered citations like [1], [1, 2], [1]-[3]
    p = re.sub(r'\[\d+([,\-\s]+\d+)*\]', ' [REF] ', p)
    # Split on sentence-ending punctuation followed by whitespace
    raw_sents = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'\(\[])', p)
    # Restore protected periods
    sents = [s.replace('__DOT__', '.').strip() for s in raw_sents if s.strip()]
    return sents

def analyze_paragraph(para: str, para_index: int) -> Dict[str, Any]:
    """Compute burstiness, cliché detections, and syntactic patterns for a single paragraph."""
    sentences = split_into_sentences(para)
    if not sentences:
        return {}

    sentence_words = []
    sentence_data = []

    for idx, s in enumerate(sentences):
        words = re.findall(r'\b[a-zA-Z0-9\'-]+\b', s)
        wc = len(words)
        first_word = words[0].lower() if words else ""
        is_fronted = first_word in FRONTED_OPENERS
        is_standard_subject = first_word in STANDARD_SUBJECT_OPENERS

        sentence_words.append(wc)
        sentence_data.append({
            "index": idx + 1,
            "text": s,
            "word_count": wc,
            "first_word": first_word,
            "is_fronted": is_fronted,
            "is_standard_subject": is_standard_subject
        })

    num_sentences = len(sentence_words)
    mean_len = sum(sentence_words) / num_sentences if num_sentences > 0 else 0
    
    # Calculate variance and standard deviation of sentence lengths (Burstiness Metric)
    if num_sentences > 1:
        variance = sum((x - mean_len) ** 2 for x in sentence_words) / (num_sentences - 1)
        std_dev = math.sqrt(variance)
    else:
        variance = 0.0
        std_dev = 0.0

    # Check for short anchors (< 12 words) and long complex sentences (> 28 words)
    has_short_anchor = any(wc <= 12 for wc in sentence_words)
    has_long_complex = any(wc >= 28 for wc in sentence_words)

    # Check for consecutive flat-length sentences (streak of 3 sentences with +- 3 words)
    flat_streaks = 0
    for i in range(len(sentence_words) - 2):
        w1, w2, w3 = sentence_words[i], sentence_words[i+1], sentence_words[i+2]
        if abs(w1 - w2) <= 3 and abs(w2 - w3) <= 3 and abs(w1 - w3) <= 4:
            flat_streaks += 1

    # Check syntactic fronting ratio
    fronted_count = sum(1 for s in sentence_data if s["is_fronted"])
    standard_count = sum(1 for s in sentence_data if s["is_standard_subject"])
    fronting_ratio = fronted_count / num_sentences if num_sentences > 0 else 0

    # Scan for banned cliché n-grams
    cliche_matches = []
    for pattern, info in BANNED_CLICHES.items():
        for match in re.finditer(pattern, para, flags=re.IGNORECASE):
            cliche_matches.append({
                "phrase": info["phrase"],
                "matched_text": match.group(0),
                "weight": info["weight"],
                "replace": info["replace"],
                "note": info["note"]
            })

    # Detect parallel triplets (rule of three: e.g. "X-ing, Y-ing, and Z-ing" or "X, Y, and Z")
    triplet_matches = []
    triplet_pattern = re.compile(
        r'\b([a-zA-Z]+ing),\s+([a-zA-Z]+ing),\s+and\s+([a-zA-Z]+ing)\b|\b([a-zA-Z]+(?:able|ive|al|ous)),\s+([a-zA-Z]+(?:able|ive|al|ous)),\s+and\s+([a-zA-Z]+(?:able|ive|al|ous))\b',
        re.IGNORECASE
    )
    for tm in triplet_pattern.finditer(para):
        triplet_matches.append(tm.group(0))

    # Calculate paragraph AI Risk Score (0-100)
    risk_score = 0.0
    
    # Factor 1: Cliché penalty (up to 40 pts)
    for cm in cliche_matches:
        risk_score += cm["weight"]

    # Factor 2: Burstiness penalty (up to 30 pts)
    # Optimal variance for scholarly human text is >= 35.0 (std_dev >= 6.0)
    if num_sentences >= 3:
        if variance < 15.0:
            risk_score += 25.0
        elif variance < 28.0:
            risk_score += 15.0
        elif variance < 40.0:
            risk_score += 5.0

        if not has_short_anchor:
            risk_score += 5.0
        if not has_long_complex:
            risk_score += 5.0
        if flat_streaks > 0:
            risk_score += (flat_streaks * 6.0)

    # Factor 3: Triplet habit penalty (up to 10 pts)
    risk_score += min(len(triplet_matches) * 5.0, 10.0)

    # Factor 4: Syntactic monotony penalty (all standard subjects, 0 fronting)
    if num_sentences >= 3 and fronting_ratio == 0 and standard_count >= 3:
        risk_score += 8.0

    risk_score = min(max(round(risk_score, 1), 0.0), 100.0)

    return {
        "index": para_index,
        "text_preview": (para[:120] + "...") if len(para) > 120 else para,
        "full_text": para,
        "num_sentences": num_sentences,
        "sentence_lengths": sentence_words,
        "mean_length": round(mean_len, 1),
        "variance": round(variance, 1),
        "std_dev": round(std_dev, 2),
        "has_short_anchor": has_short_anchor,
        "has_long_complex": has_long_complex,
        "flat_streaks": flat_streaks,
        "fronting_ratio": round(fronting_ratio, 2),
        "cliche_matches": cliche_matches,
        "triplet_matches": triplet_matches,
        "risk_score": risk_score
    }

def audit_file(filepath: str) -> Dict[str, Any]:
    """Run complete writing analysis on a given document."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Target document not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        raw_text = f.read()

    file_ext = os.path.splitext(filepath)[1].lower()
    cleaned = clean_text_for_analysis(raw_text, file_ext)
    paragraphs = split_into_paragraphs(cleaned)

    para_results = []
    total_words = 0
    all_sentence_lengths = []
    all_cliches = []
    all_triplets = []

    for idx, p in enumerate(paragraphs, start=1):
        res = analyze_paragraph(p, idx)
        if res:
            para_results.append(res)
            all_sentence_lengths.extend(res["sentence_lengths"])
            all_cliches.extend(res["cliche_matches"])
            all_triplets.extend(res["triplet_matches"])
            total_words += sum(res["sentence_lengths"])

    # Global corpus metrics
    total_sentences = len(all_sentence_lengths)
    global_mean = sum(all_sentence_lengths) / total_sentences if total_sentences > 0 else 0
    if total_sentences > 1:
        global_variance = sum((x - global_mean) ** 2 for x in all_sentence_lengths) / (total_sentences - 1)
        global_std_dev = math.sqrt(global_variance)
    else:
        global_variance = 0.0
        global_std_dev = 0.0

    # Calculate overall file risk score (weighted average of paragraph scores + global penalty)
    if para_results:
        avg_para_risk = sum(p["risk_score"] for p in para_results) / len(para_results)
    else:
        avg_para_risk = 0.0

    # Adjust for document-level burstiness
    overall_risk = avg_para_risk
    if global_variance < 30.0 and total_sentences >= 5:
        overall_risk = min(overall_risk + 10.0, 100.0)

    overall_risk = min(max(round(overall_risk, 1), 0.0), 100.0)

    return {
        "file": os.path.abspath(filepath),
        "total_words": total_words,
        "total_paragraphs": len(para_results),
        "total_sentences": total_sentences,
        "global_mean_sentence_length": round(global_mean, 1),
        "global_variance": round(global_variance, 1),
        "global_std_dev": round(global_std_dev, 2),
        "overall_risk_score": overall_risk,
        "total_cliches": len(all_cliches),
        "total_triplets": len(all_triplets),
        "paragraphs": para_results
    }

def print_audit_report(result: Dict[str, Any], detailed: bool = False):
    """Print human-readable audit report to the console."""
    score = result["overall_risk_score"]
    
    if score <= 18.0:
        status_label = colorize("LOW RISK (Authentic Human Cadence)", Colors.GREEN)
        badge = colorize("PASSED", Colors.GREEN)
    elif score <= 40.0:
        status_label = colorize("MODERATE RISK (Potential Classifier Vulnerability)", Colors.YELLOW)
        badge = colorize("CAUTION", Colors.YELLOW)
    else:
        status_label = colorize("HIGH RISK (High Probability of Turnitin/AI Flag)", Colors.RED)
        badge = colorize("FLAGGED", Colors.RED)

    print("\n" + "=" * 78)
    print(colorize(f"  THESIS AI CADENCE AUDIT: {os.path.basename(result['file'])}", Colors.BOLD))
    print("=" * 78)

    print(f"\n* Status:               [{badge}] {status_label}")
    print(f"* Overall AI Risk:      {score}% (Turnitin Sensitivity Metric)")
    print(f"* Word Count:           {result['total_words']} words across {result['total_paragraphs']} substantive paragraphs")
    print(f"* Sentence Count:       {result['total_sentences']} sentences")
    print(f"* Mean Sentence Length: {result['global_mean_sentence_length']} words/sentence")
    print(f"* Sentence Variance:    {result['global_variance']} (Std Dev: {result['global_std_dev']})")
    print(f"  └─ Optimum Target:    Variance >= 35.0 (Std Dev >= 6.0) for organic burstiness")
    print(f"* Banned AI N-Grams:    {result['total_cliches']} occurrences")
    print(f"* Symmetric Triplets:   {result['total_triplets']} occurrences")

    # Cliché table summary if found
    all_cliches = []
    for p in result["paragraphs"]:
        for c in p["cliche_matches"]:
            all_cliches.append((p["index"], c))

    if all_cliches:
        print("\n" + "-" * 78)
        print(colorize("  [!] DETECTED AI CLICHÉ N-GRAMS (IMMEDIATE REWRITE RECOMMENDED)", Colors.RED))
        print("-" * 78)
        for p_idx, c in all_cliches:
            print(f"  • Para {p_idx}: Matched '{colorize(c['matched_text'], Colors.YELLOW)}'")
            print(f"    Suggested alternatives: {colorize(c['replace'], Colors.GREEN)}")
            print(f"    Reason: {c['note']}")
            print()

    # Low burstiness warnings
    low_burst_paras = [p for p in result["paragraphs"] if p["num_sentences"] >= 3 and p["variance"] < 25.0]
    if low_burst_paras:
        print("-" * 78)
        print(colorize("  [!] LOW BURSTINESS PARAGRAPHS (UNIFORM SENTENCE CADENCE DETECTED)", Colors.YELLOW))
        print("-" * 78)
        for p in low_burst_paras:
            print(f"  • Para {p['index']} (Risk: {p['risk_score']}%, Variance: {p['variance']}, Std Dev: {p['std_dev']}):")
            print(f"    Sentence lengths: {p['sentence_lengths']} words")
            print(f"    Preview: \"{p['text_preview']}\"")
            tips = []
            if not p["has_short_anchor"]:
                tips.append("Add a short anchor sentence (6-11 words)")
            if not p["has_long_complex"]:
                tips.append("Combine two clauses into a complex sentence (28-38 words)")
            if p["flat_streaks"] > 0:
                tips.append(f"Break up {p['flat_streaks']} flat streak(s) of uniform sentences")
            print(f"    Fix: {'; '.join(tips)}\n")

    # If detailed flag requested, print each paragraph breakdown
    if detailed:
        print("\n" + "=" * 78)
        print(colorize("  DETAILED PARAGRAPH-BY-PARAGRAPH BREAKDOWN", Colors.CYAN))
        print("=" * 78)
        for p in result["paragraphs"]:
            p_color = Colors.GREEN if p["risk_score"] <= 20 else (Colors.YELLOW if p["risk_score"] <= 40 else Colors.RED)
            print(f"\nParagraph #{p['index']} - Risk Score: {colorize(str(p['risk_score']) + '%', p_color)}")
            print(f"Lengths: {p['sentence_lengths']} | Mean: {p['mean_length']} | Variance: {p['variance']}")
            print(f"Text: \"{p['text_preview']}\"")

    print("\n" + "=" * 78)
    if score <= 18.0:
        print(colorize("  VERDICT: Prose demonstrates high perplexity and natural burstiness. Ready for Turnitin.", Colors.GREEN))
    elif score <= 40.0:
        print(colorize("  VERDICT: Low-risk, but resolve the flagged phrases and adjust flat sentence clusters.", Colors.YELLOW))
    else:
        print(colorize("  VERDICT: High probability of AI detector flag. Restructure paragraphs with high burstiness.", Colors.RED))
    print("=" * 78 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="Pre-Flight Thesis AI Writing Auditor (Turnitin & Classifier Pre-check)"
    )
    parser.add_argument("paths", nargs="+", help="Path(s) to markdown (.md), LaTeX (.tex), or plain text files.")
    parser.add_argument("-v", "--detailed", action="store_true", help="Show detailed paragraph breakdown.")
    parser.add_argument("--json", action="store_true", help="Output results in machine-readable JSON.")
    args = parser.parse_args()

    results = []
    for p in args.paths:
        try:
            res = audit_file(p)
            results.append(res)
            if not args.json:
                print_audit_report(res, detailed=args.detailed)
        except Exception as e:
            print(f"Error processing {p}: {e}", file=sys.stderr)

    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2))

if __name__ == "__main__":
    main()
