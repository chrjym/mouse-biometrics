#!/usr/bin/env python3
r"""
tests/test_rrl_fetch.py — Offline unit test suite for RRL literature fetcher.

Tests:
1. DOI normalization (lowercase, stripping protocols/prefixes, trimming)
2. Deduplication and merging (DOI matching, title similarity fallback, keeping longest abstract & highest citations)
3. Manual-import parsing (ResearchGate slugs, unresolvable ejournals.ph URLs, Crossref resolution, stubs)
4. LaTeX / BibTeX export (special char escaping & % $ # _ { } ~ ^ \, double-braced titles, unique keys, @article/@misc, doi vs url)
5. Mocked HTTP calls for all connectors (Europe PMC, PubMed, ERIC, DOAJ, DBLP, OpenAIRE, Zenodo, OSF, Springer, IEEE, CORE, Crossref)
6. Philippines scope flags (OpenAlex-PH, DOAJ-PH)
7. Unpaywall PDF enrichment
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure references directory is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references"))

import importlib.util
spec = importlib.util.spec_from_file_location("example_rrl_fetch", REPO_ROOT / "references" / "example-rrl-fetch.py")
rrl = importlib.util.module_from_spec(spec)
sys.modules["example_rrl_fetch"] = rrl
spec.loader.exec_module(rrl)


class TestDoiNormalization(unittest.TestCase):
    """Tests for DOI normalization."""

    def test_various_doi_formats(self):
        cases = [
            ("https://doi.org/10.1038/s41598-025-32406-y", "10.1038/s41598-025-32406-y"),
            ("http://dx.doi.org/10.1109/JSYST.2012.2221932", "10.1109/jsyst.2012.2221932"),
            ("doi:10.1007/978-3-030-79997-7_23", "10.1007/978-3-030-79997-7_23"),
            ("DOI: 10.5281/ZENODO.13922262", "10.5281/zenodo.13922262"),
            ("  doi: https://doi.org/10.1142/S0218001408006363. ", "10.1142/s0218001408006363"),
            ("10.1016/j.patcog.2023.109800", "10.1016/j.patcog.2023.109800"),
            (None, None),
            ("", None),
            ("   ", None),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(rrl.normalize_doi(raw), expected)


class TestDeduplicateAndMerge(unittest.TestCase):
    """Tests for deduplication and metadata merging."""

    def test_merge_by_doi(self):
        paper1 = rrl.make_record(
            title="Short Title",
            authors=["Alice"],
            year="2024",
            doi="10.1000/182",
            abstract="Short abstract",
            url="https://source1.org",
            citations=5,
            sources=["arXiv"],
        )
        paper2 = rrl.make_record(
            title="Full Expanded Title",
            authors=["Alice", "Bob"],
            year="2024",
            doi="https://doi.org/10.1000/182",  # Equivalent DOI
            abstract="This is a substantially longer and more complete abstract for the paper.",
            venue="IEEE Transactions on Biometrics",
            pdf_url="https://source2.org/paper.pdf",
            citations=25,
            sources=["OpenAlex"],
        )

        merged = rrl.deduplicate_and_merge([paper1, paper2])
        self.assertEqual(len(merged), 1)
        res = merged[0]

        # Sources merged
        self.assertIn("arXiv", res["sources"])
        self.assertIn("OpenAlex", res["sources"])
        # Longest abstract kept
        self.assertEqual(res["abstract"], paper2["abstract"])
        # Highest citations kept
        self.assertEqual(res["citations"], 25)
        # Missing fields populated
        self.assertEqual(res["venue"], "IEEE Transactions on Biometrics")
        self.assertEqual(res["pdf_url"], "https://source2.org/paper.pdf")
        self.assertEqual(res["authors"], ["Alice", "Bob"])

    def test_merge_by_title_similarity_fallback(self):
        paper1 = rrl.make_record(
            title="Measuring Behavioral Fingerprints of Users in Mouse Trajectories",
            authors=["John Doe"],
            year="2025",
            sources=["SourceA"],
        )
        paper2 = rrl.make_record(
            title="Measuring Behavioral Fingerprints of Users in Mouse Trajectories for Continuous Authentication",
            authors=["John Doe"],
            year="2025",
            sources=["SourceB"],
            abstract="Comprehensive geometric mannerism evaluation.",
        )

        merged = rrl.deduplicate_and_merge([paper1, paper2])
        self.assertEqual(len(merged), 1)
        self.assertEqual(len(merged[0]["sources"]), 2)
        self.assertEqual(merged[0]["abstract"], "Comprehensive geometric mannerism evaluation.")

    def test_distinct_papers_remain_separate(self):
        p1 = rrl.make_record(title="Mouse Trajectory Authentication", doi="10.1111/one")
        p2 = rrl.make_record(title="Gait Recognition with YOLO", doi="10.2222/two")
        merged = rrl.deduplicate_and_merge([p1, p2])
        self.assertEqual(len(merged), 2)


class TestManualImportParsing(unittest.TestCase):
    """Tests for manual text import (ResearchGate, ejournals.ph, HERDIN, Crossref resolution)."""

    def test_parse_manual_line_rg_slug(self):
        url = "https://www.researchgate.net/publication/345678901_Mouse_Trajectory_Analysis_for_Continuous_Authentication"
        parsed = rrl.parse_manual_line(url)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["kind"], "rg_slug")
        self.assertEqual(parsed["content"], "Mouse Trajectory Analysis for Continuous Authentication")
        self.assertEqual(parsed["tag_base"], "ResearchGate")

    def test_parse_manual_line_ejournals_ph(self):
        url = "https://ejournals.ph/article.php?id=12345"
        parsed = rrl.parse_manual_line(url)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["kind"], "url")
        self.assertEqual(parsed["content"], url)
        self.assertEqual(parsed["tag_base"], "ejournals.ph")

    def test_parse_manual_line_tags(self):
        line1 = "rg: Closed-form Menger Curvature in Mouse Dynamics"
        p1 = rrl.parse_manual_line(line1)
        self.assertEqual(p1["tag_base"], "ResearchGate")
        self.assertEqual(p1["content"], "Closed-form Menger Curvature in Mouse Dynamics")

        line2 = "pej: Continuous Authentication of Online Students"
        p2 = rrl.parse_manual_line(line2)
        self.assertEqual(p2["tag_base"], "ejournals.ph")
        self.assertEqual(p2["content"], "Continuous Authentication of Online Students")

        line3 = "# Comment line should be ignored"
        self.assertIsNone(rrl.parse_manual_line(line3))

    @patch("example_rrl_fetch.resolve_crossref_title")
    def test_import_file_rg_slug_verified_and_unverified(self, mock_resolve_title):
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as tf:
            tf.write("# Manual review batch\n")
            tf.write("https://www.researchgate.net/publication/111_Verified_Mouse_Paper\n")
            tf.write("https://www.researchgate.net/publication/222_Unverified_Unknown_Paper\n")
            tf.write("https://ejournals.ph/article.php?id=9999\n")
            tf_path = Path(tf.name)

        try:
            # Mock 1st call matches Crossref with sim >= 0.8
            # Mock 2nd call fails Crossref match (sim < 0.8)
            mock_resolve_title.side_effect = [
                (rrl.make_record(title="Verified Mouse Paper", doi="10.1000/verified", venue="Journal"), 0.95),
                (rrl.make_record(title="Completely Different Topic", doi="10.1000/diff"), 0.30),
            ]

            results = rrl.import_manual_file(tf_path)
            self.assertEqual(len(results), 3)

            # 1st item: verified via slug
            self.assertEqual(results[0]["sources"], ["ResearchGate (manual)"])
            self.assertEqual(results[0]["doi"], "10.1000/verified")

            # 2nd item: unverified stub (never dropped silently)
            self.assertEqual(results[1]["sources"], ["ResearchGate (manual, unverified)"])
            self.assertEqual(results[1]["title"], "Unverified Unknown Paper")

            # 3rd item: unresolvable ejournals.ph URL kept as unverified stub without scraping
            self.assertEqual(results[2]["sources"], ["ejournals.ph (manual, unverified)"])
            self.assertEqual(results[2]["url"], "https://ejournals.ph/article.php?id=9999")

        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_manual_search_links_generator(self):
        links = rrl.get_manual_search_links(['"mouse dynamics"'])
        self.assertTrue(len(links) >= 3)
        urls = [url for _, url in links]
        self.assertTrue(any("researchgate.net" in u for u in urls))
        self.assertTrue(any("ejournals.ph" in u for u in urls))
        self.assertTrue(any("herdin.ph" in u for u in urls))


class TestBibTeXEscapingAndExport(unittest.TestCase):
    """Tests for LaTeX and BibTeX formatting, special characters, and skeletons."""

    def test_bibtex_special_character_escaping(self):
        raw = r"100% security & privacy: A $5 #1 model in user_test with {braces} and ~tilde ^caret \backslash"
        escaped = rrl.escape_bibtex(raw)

        # Check all 10 characters are escaped
        self.assertIn(r"\%", escaped)
        self.assertIn(r"\&", escaped)
        self.assertIn(r"\$", escaped)
        self.assertIn(r"\#", escaped)
        self.assertIn(r"\_", escaped)
        self.assertIn(r"\{", escaped)
        self.assertIn(r"\}", escaped)
        self.assertIn(r"\textasciitilde{}", escaped)
        self.assertIn(r"\textasciicircum{}", escaped)
        self.assertIn(r"\textbackslash{}", escaped)

        # Check no raw unescaped instances remain
        self.assertNotIn(r"%", escaped.replace(r"\%", ""))
        self.assertNotIn(r"&", escaped.replace(r"\&", ""))
        self.assertNotIn(r"$", escaped.replace(r"\$", ""))
        self.assertNotIn(r"#", escaped.replace(r"\#", ""))
        self.assertNotIn(r"_", escaped.replace(r"\_", ""))

    def test_bibtex_key_generation_and_uniqueness(self):
        seen_keys = set()
        p1 = rrl.make_record(
            title="Mathematical Feature Representations of Mouse Dynamics",
            authors=["Elvin Asgarov"],
            year="2026",
        )
        p2 = rrl.make_record(
            title="Mathematical Foundations of Continuous Authentication",
            authors=["Elvin Asgarov"],
            year="2026",
        )

        k1 = rrl.generate_bibtex_key(p1, seen_keys)
        k2 = rrl.generate_bibtex_key(p2, seen_keys)

        self.assertEqual(k1, "asgarov2026mathematical")
        self.assertEqual(k2, "asgarov2026mathematicalb")
        self.assertIn(k1, seen_keys)
        self.assertIn(k2, seen_keys)

    def test_export_latex_and_bibtex_files(self):
        candidates = [
            rrl.make_record(
                title="Mouse Dynamics & Biometric Authentication: 100% Verification",
                authors=["Khan, M. A.", "Traoré, Issa"],
                year="2024",
                venue="ACM Computing Surveys",
                doi="10.1145/3643840",
            ),
            rrl.make_record(
                title="Optimizing Mouse Dynamics via Units",
                authors=["Wang, Y."],
                year="2025",
                venue="",  # No venue -> should be @misc
                url="https://arxiv.org/abs/2504.21415",
            ),
        ]

        with tempfile.TemporaryDirectory() as td:
            out_base = Path(td) / "test_rrl"
            bib_path, tex_path = rrl.export_latex_and_bibtex(candidates, out_base)

            self.assertTrue(bib_path.exists())
            self.assertTrue(tex_path.exists())

            bib_text = bib_path.read_text(encoding="utf-8")
            tex_text = tex_path.read_text(encoding="utf-8")

            # Double braces around titles
            self.assertIn(r"title = {{Mouse Dynamics \& Biometric Authentication: 100\% Verification}}", bib_text)
            # @article for paper with venue
            self.assertIn("@article{", bib_text)
            # @misc for paper without venue
            self.assertIn("@misc{", bib_text)
            # Uses DOI field when available
            self.assertIn("doi = {10.1145/3643840}", bib_text)
            # Uses URL field only when no DOI
            self.assertIn("url = {https://arxiv.org/abs/2504.21415}", bib_text)

            # Compilable LaTeX skeleton features
            self.assertIn(r"\documentclass{article}", tex_text)
            self.assertIn(r"\nocite{*}", tex_text)
            self.assertIn(r"\bibliographystyle{apalike}", tex_text)
            self.assertIn(f"\\bibliography{{{bib_path.stem}}}", tex_text)
            self.assertIn("% - khan2024mouse:", tex_text)


class TestConnectorsMocked(unittest.TestCase):
    """Offline unit tests for all connectors with mocked HTTP responses."""

    @patch("example_rrl_fetch.safe_urlopen")
    def test_fetch_europe_pmc(self, mock_urlopen):
        mock_resp = {
            "resultList": {
                "result": [
                    {
                        "title": "Federated Biometrics in Mouse Dynamics.",
                        "authorList": {"author": [{"fullName": "Alice Smith"}]},
                        "pubYear": "2026",
                        "doi": "10.1038/s41598-026-0001",
                        "journalTitle": "Scientific Reports",
                        "citedByCount": 3,
                        "abstractText": "Novel study on mouse biometrics.",
                        "source": "MED",
                        "id": "12345",
                    }
                ]
            }
        }
        mock_urlopen.return_value = json.dumps(mock_resp).encode("utf-8")

        res = rrl.fetch_europe_pmc("mouse dynamics")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["title"], "Federated Biometrics in Mouse Dynamics.")
        self.assertEqual(res[0]["doi"], "10.1038/s41598-026-0001")
        self.assertEqual(res[0]["sources"], ["Europe PMC"])
        self.assertEqual(res[0]["citations"], 3)

    @patch("example_rrl_fetch.safe_urlopen")
    def test_fetch_pubmed(self, mock_urlopen):
        esearch_resp = json.dumps({"esearchresult": {"idlist": ["38000001"]}}).encode("utf-8")
        efetch_xml = b"""<PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <Article>
                        <ArticleTitle>Neuromuscular Mouse Dynamics</ArticleTitle>
                        <Journal><Title>IEEE TBME</Title></Journal>
                        <JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue>
                        <AuthorList>
                            <Author><ForeName>John</ForeName><LastName>Doe</LastName></Author>
                        </AuthorList>
                        <Abstract><AbstractText>Curvature study.</AbstractText></Abstract>
                    </Article>
                </MedlineCitation>
                <PubmedData>
                    <ArticleIdList>
                        <ArticleId IdType="doi">10.1109/TBME.2025.1</ArticleId>
                        <ArticleId IdType="pubmed">38000001</ArticleId>
                    </ArticleIdList>
                </PubmedData>
            </PubmedArticle>
        </PubmedArticleSet>"""
        mock_urlopen.side_effect = [esearch_resp, efetch_xml]

        res = rrl.fetch_pubmed("mouse dynamics")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["title"], "Neuromuscular Mouse Dynamics")
        self.assertEqual(res[0]["doi"], "10.1109/tbme.2025.1")
        self.assertEqual(res[0]["sources"], ["PubMed"])

    @patch("example_rrl_fetch.safe_urlopen")
    def test_fetch_eric(self, mock_urlopen):
        eric_resp = {
            "response": {
                "docs": [
                    {
                        "title": "Action Dynamics in Computer Learning",
                        "author": ["Smith, Jane"],
                        "publicationdateyear": 2024,
                        "description": "Educational interaction study.",
                        "source": "Journal of Learning",
                        "id": "EJ99999",
                    }
                ]
            }
        }
        mock_urlopen.return_value = json.dumps(eric_resp).encode("utf-8")

        res = rrl.fetch_eric("mouse dynamics")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["title"], "Action Dynamics in Computer Learning")
        self.assertEqual(res[0]["sources"], ["ERIC"])

    @patch("example_rrl_fetch.safe_urlopen")
    def test_fetch_doaj_standard_and_ph(self, mock_urlopen):
        doaj_resp = {
            "results": [
                {
                    "bibjson": {
                        "title": "Philippine Biometrics Evaluation",
                        "author": [{"name": "Santos, Maria"}],
                        "year": "2024",
                        "journal": {"title": "Philippine Computing Journal"},
                        "identifier": [{"type": "doi", "id": "10.9999/pcj.2024"}],
                        "link": [{"type": "fulltext", "url": "https://pcj.ph/paper.pdf"}],
                    }
                }
            ]
        }
        mock_urlopen.return_value = json.dumps(doaj_resp).encode("utf-8")

        res_ph = rrl.fetch_doaj("biometrics", ph_scope=True)
        self.assertEqual(len(res_ph), 1)
        self.assertEqual(res_ph[0]["sources"], ["DOAJ-PH"])

    @patch("example_rrl_fetch.safe_urlopen")
    def test_fetch_openaire(self, mock_urlopen):
        openaire_resp = {
            "results": [
                {
                    "mainTitle": "Inverse Biometrics for Mouse Dynamics",
                    "authors": [{"fullName": "Issa Traore"}],
                    "publicationDate": "2023-05-01",
                    "pids": [{"scheme": "doi", "value": "10.1142/s0218001408006363"}],
                    "descriptions": ["Feature extraction analysis."],
                    "publisher": "World Scientific",
                    "indicators": {"citationCount": 42},
                }
            ]
        }
        mock_urlopen.return_value = json.dumps(openaire_resp).encode("utf-8")

        res = rrl.fetch_openaire("mouse dynamics")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["title"], "Inverse Biometrics for Mouse Dynamics")
        self.assertEqual(res[0]["doi"], "10.1142/s0218001408006363")
        self.assertEqual(res[0]["citations"], 42)
        self.assertEqual(res[0]["sources"], ["OpenAIRE"])

    @patch("example_rrl_fetch.safe_urlopen")
    def test_fetch_zenodo(self, mock_urlopen):
        zenodo_resp = {
            "hits": {
                "hits": [
                    {
                        "metadata": {
                            "title": "Mouse Dynamics Benchmark Dataset",
                            "creators": [{"name": "Research Group"}],
                            "publication_date": "2024-01-15",
                            "doi": "10.5281/zenodo.123456",
                            "description": "<p>Dataset containing mouse strokes.</p>",
                            "journal_title": "Zenodo Data Repository",
                        },
                        "links": {"doi": "https://doi.org/10.5281/zenodo.123456"},
                    }
                ]
            }
        }
        mock_urlopen.return_value = json.dumps(zenodo_resp).encode("utf-8")

        res = rrl.fetch_zenodo("mouse dynamics")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["title"], "Mouse Dynamics Benchmark Dataset")
        self.assertEqual(res[0]["abstract"], "Dataset containing mouse strokes.")
        self.assertEqual(res[0]["sources"], ["Zenodo"])

    @patch("example_rrl_fetch.safe_urlopen")
    def test_fetch_osf(self, mock_urlopen):
        osf_resp = {
            "data": [
                {
                    "attributes": {
                        "title": "Perceptual Dynamics in Mouse Inputs",
                        "doi": "10.31219/osf.io/xyz",
                        "date_published": "2024-08-01",
                        "description": "Preprint on motor trajectories.",
                    },
                    "embeds": {
                        "contributors": {
                            "data": [
                                {"embeds": {"users": {"data": {"attributes": {"full_name": "Dr. Motor"}}}}}
                            ]
                        }
                    },
                    "links": {"html": "https://osf.io/xyz"},
                }
            ]
        }
        mock_urlopen.return_value = json.dumps(osf_resp).encode("utf-8")

        res = rrl.fetch_osf("mouse")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["title"], "Perceptual Dynamics in Mouse Inputs")
        self.assertEqual(res[0]["authors"], ["Dr. Motor"])
        self.assertEqual(res[0]["sources"], ["OSF Preprints"])

    def test_keyed_sources_skipped_when_key_absent(self):
        # When environment variables and arguments are None, keyed sources return empty list
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(rrl.fetch_springer("test", api_key=None), [])
            self.assertEqual(rrl.fetch_ieee("test", api_key=None), [])
            self.assertEqual(rrl.fetch_core("test", api_key=None), [])
            self.assertEqual(rrl.fetch_google_scholar_serpapi("test", api_key=None), [])

    @patch("example_rrl_fetch.safe_urlopen")
    def test_fetch_springer_with_key(self, mock_urlopen):
        springer_resp = {
            "records": [
                {
                    "title": "Behavioral Authentication in Springer",
                    "creators": [{"creator": "Author Springer"}],
                    "publicationDate": "2024-03-01",
                    "doi": "10.1007/s0001",
                    "publicationName": "Springer Journal",
                    "abstract": "Springer abstract.",
                }
            ]
        }
        mock_urlopen.return_value = json.dumps(springer_resp).encode("utf-8")
        res = rrl.fetch_springer("test", api_key="dummy_springer_key")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["sources"], ["Springer Nature"])

    @patch("example_rrl_fetch.safe_urlopen")
    def test_fetch_ieee_with_key(self, mock_urlopen):
        ieee_resp = {
            "articles": [
                {
                    "title": "Continuous Mouse Authentication via Discrete Fréchet",
                    "authors": {"authors": [{"full_name": "IEEE Author"}]},
                    "publication_year": "2024",
                    "doi": "10.1109/TIFS.2024.1",
                    "publication_title": "IEEE TIFS",
                    "citing_paper_count": 10,
                }
            ]
        }
        mock_urlopen.return_value = json.dumps(ieee_resp).encode("utf-8")
        res = rrl.fetch_ieee("test", api_key="dummy_ieee_key")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["sources"], ["IEEE Xplore"])
        self.assertEqual(res[0]["citations"], 10)

    @patch("example_rrl_fetch.safe_urlopen")
    def test_fetch_crossref(self, mock_urlopen):
        crossref_resp = {
            "message": {
                "items": [
                    {
                        "title": ["Crossref Indexed Mouse Biometrics"],
                        "author": [{"given": "Jane", "family": "Cross"}],
                        "published-print": {"date-parts": [[2025, 1, 1]]},
                        "DOI": "10.1000/crossref-1",
                        "container-title": ["Crossref Journal"],
                        "is-referenced-by-count": 14,
                    }
                ]
            }
        }
        mock_urlopen.return_value = json.dumps(crossref_resp).encode("utf-8")
        res = rrl.fetch_crossref("mouse")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["title"], "Crossref Indexed Mouse Biometrics")
        self.assertEqual(res[0]["authors"], ["Jane Cross"])
        self.assertEqual(res[0]["sources"], ["Crossref"])

    @patch("example_rrl_fetch.safe_urlopen")
    def test_enrich_with_unpaywall(self, mock_urlopen):
        unpaywall_resp = {
            "is_oa": True,
            "best_oa_location": {"url_for_pdf": "https://legal.oa/file.pdf"},
        }
        mock_urlopen.return_value = json.dumps(unpaywall_resp).encode("utf-8")

        candidates = [
            rrl.make_record(title="OA Paper", doi="10.1000/oa", pdf_url=""),
            rrl.make_record(title="Already has PDF", doi="10.1000/has-pdf", pdf_url="https://existing.pdf"),
        ]

        rrl.enrich_with_unpaywall(candidates, email="test@example.edu")
        self.assertEqual(candidates[0]["pdf_url"], "https://legal.oa/file.pdf")
        self.assertEqual(candidates[1]["pdf_url"], "https://existing.pdf")


if __name__ == "__main__":
    unittest.main(verbosity=2)
