#!/usr/bin/env python3
"""Unit tests for build/build_dashboard.py — stdlib unittest.

Run:  python3 -m unittest discover -s build/tests -t build/tests -v
  or: python3 build/tests/test_build_dashboard.py
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_dashboard as bd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "03_산출물-설계.md"
EXPECTED_TABS = ["home", "why", "what", "who", "when", "where", "how",
                 "papers", "track", "refs"]


def data_block(page: str, name: str):
    m = re.search(
        r'<script type="application/json" id="data-%s">(.*?)</script>' % re.escape(name),
        page, re.S)
    if not m:
        raise AssertionError(f"data block data-{name} not found")
    return json.loads(m.group(1))


def spec_section_tokens() -> list[str]:
    """Backticked ids in the §2.3 table of docs/03_산출물-설계.md."""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("### 2.3")
    end = text.index("### 2.4", start)
    return re.findall(r"`([^`]+)`", text[start:end])


def copy_repo(dst: Path) -> None:
    shutil.copytree(ROOT / "content", dst / "content")
    shutil.copy2(ROOT / bd.HANDOFF_NAME, dst / bd.HANDOFF_NAME)


class BuildRealContent(unittest.TestCase):
    """Build once from the real content/ into a temp file."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "index.html"
        cls.summary = bd.build(ROOT, cls.out)
        cls.page = cls.out.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_build_succeeds_and_size_is_reasonable(self):
        self.assertTrue(self.out.exists())
        size = self.out.stat().st_size
        self.assertGreater(size, 200_000)
        self.assertLess(size, 3_500_000, f"dashboard is {size:,} bytes")
        self.assertTrue(self.page.lstrip().lower().startswith("<!doctype html>"))

    def test_ten_tab_buttons_in_order(self):
        tabs = re.findall(r'<button[^>]*role="tab"[^>]*data-tab="([a-z]+)"', self.page)
        self.assertEqual(tabs, EXPECTED_TABS)
        for t in EXPECTED_TABS:
            self.assertIn(f'id="panel-{t}"', self.page)

    def test_spec_section_ids_exist(self):
        tokens = spec_section_tokens()
        self.assertGreater(len(tokens), 25, "could not read §2.3 of the spec")
        papers = data_block(self.page, "papers")
        refs = data_block(self.page, "references")["references"]
        hook_ids = {h["id"] for p in papers for h in p["successor_hooks"]}
        for tok in tokens:
            if tok.startswith("paper-P"):
                continue            # checked for every paper below
            if tok.startswith("hook-"):
                self.assertIn(tok[len("hook-"):], hook_ids)
                continue
            if tok.startswith("ref-"):
                continue            # checked in test_reference_anchors
            self.assertIn(f'id="{tok}"', self.page, f"section id {tok} missing")
        for p in papers:
            self.assertIn(f'id="paper-{p["id"]}"', self.page)
        self.assertEqual(len(refs), len({r["anchor"] for r in refs}))

    def test_every_paper_card_is_embedded(self):
        papers = data_block(self.page, "papers")
        on_disk = sorted(p.stem for p in (ROOT / "content" / "papers").glob("P*.json"))
        self.assertEqual([p["id"] for p in papers], on_disk)
        for p in papers:
            for key in ("who", "when", "where", "what", "how", "why"):
                self.assertTrue(p["w5h1"][key]["headline"], f"{p['id']} {key}")
            for key in ("word", "sentence", "paragraph", "context"):
                self.assertTrue(p["layers"][key], f"{p['id']} layers.{key}")

    def test_reference_anchors(self):
        refs = data_block(self.page, "references")["references"]
        src = json.loads((ROOT / "content" / "references.json").read_text(encoding="utf-8"))
        self.assertEqual(len(refs), len(src["references"]))
        self.assertEqual([r["anchor"] for r in refs],
                         [f"ref-{r['n']}" for r in src["references"]])
        for r in refs:
            if r.get("doi"):
                self.assertTrue(str(r.get("url", "")).startswith("https://doi.org/"),
                                f"[{r['n']}] DOI url")

    def test_matrix_has_30_cells_pointing_at_sections(self):
        cells = data_block(self.page, "matrix")["cells"]
        self.assertEqual(len(cells), 30)
        for c in cells:
            self.assertIn(f'id="{c["anchor"]}"', self.page, c["anchor"])

    def test_stimuli_rows_match_csv(self):
        stim = data_block(self.page, "stimuli")
        for path in (ROOT / "content" / "stimuli").glob("*.csv"):
            lines = [ln for ln in path.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
            self.assertIn(path.stem, stim)
            # quoted fields contain no newlines in these files: rows = lines - header
            self.assertEqual(len(stim[path.stem]["rows"]), len(lines) - 1, path.name)

    def test_tracker_tables_parsed(self):
        tr = data_block(self.page, "tracker")
        self.assertIn("상태", tr["ledger"]["headers"])
        self.assertGreater(len(tr["ledger"]["rows"]), 10)
        self.assertGreater(len(tr["decisions"]["rows"]), 3)
        self.assertGreater(len(tr["verification"]["rows"]), 3)
        self.assertTrue(tr["ledger_counts"])

    def test_no_external_resources(self):
        self.assertIsNone(re.search(r"<script[^>]*\bsrc\s*=", self.page, re.I))
        self.assertIsNone(re.search(r'<link[^>]*href\s*=\s*["\']?https?:', self.page, re.I))
        self.assertNotIn("@import", self.page)
        self.assertIsNone(re.search(r"url\(\s*['\"]?https?:", self.page, re.I))
        self.assertNotIn("fonts.googleapis", self.page)

    def test_json_blocks_are_valid_and_html_safe(self):
        blocks = re.findall(r'<script type="application/json" id="data-([a-z]+)">(.*?)</script>',
                            self.page, re.S)
        names = [b[0] for b in blocks]
        for want in ("meta", "papers", "synthesis", "candidates", "experiments", "stimuli",
                     "evaluation", "models", "implications", "roadmap", "references",
                     "matrix", "tracker"):
            self.assertIn(want, names)
        for name, body in blocks:
            json.loads(body)
            self.assertNotIn("<", body, f"raw '<' inside data-{name}")

    def test_theme_tokens_and_toggle(self):
        self.assertIn("prefers-color-scheme: dark", self.page)
        self.assertIn(':root[data-theme="dark"]', self.page)
        for mode in ("light", "dark", "system"):
            self.assertIn(f'data-theme-set="{mode}"', self.page)


class BuildEdgeCases(unittest.TestCase):

    def test_missing_stimulus_files_are_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            copy_repo(root)
            for name in ("E3.csv", "fillers.csv"):
                p = root / "content" / "stimuli" / name
                if p.exists():
                    p.unlink()
            summary = bd.build(root, root / "dashboard" / "index.html")
            page = (root / "dashboard" / "index.html").read_text(encoding="utf-8")
            stim = data_block(page, "stimuli")
            self.assertNotIn("E3", stim)
            self.assertIn("E3", summary["stimuli_missing"])
            self.assertIn("E3", data_block(page, "meta")["stimuli_missing"])

    def test_no_stimuli_folder_at_all(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            copy_repo(root)
            shutil.rmtree(root / "content" / "stimuli")
            summary = bd.build(root, root / "out.html")
            self.assertEqual(summary["stimuli_rows"], {})

    def test_hostile_text_is_escaped_in_json(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            copy_repo(root)
            p = root / "content" / "papers" / "P01.json"
            card = json.loads(p.read_text(encoding="utf-8"))
            card["one_line"] = '</script><script>alert("x")</script> & "따옴표"'
            p.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
            bd.build(root, root / "out.html")
            page = (root / "out.html").read_text(encoding="utf-8")
            self.assertNotIn('<script>alert("x")', page)
            papers = data_block(page, "papers")
            self.assertEqual(papers[0]["one_line"], card["one_line"])

    def test_missing_handoff_does_not_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            copy_repo(root)
            (root / bd.HANDOFF_NAME).unlink()
            summary = bd.build(root, root / "out.html")
            self.assertTrue(any(bd.HANDOFF_NAME in w for w in summary["warnings"]))


class MarkdownParsing(unittest.TestCase):

    def test_split_row_keeps_code_pipes_and_escaped_pipes(self):
        row = "| a | `x | y` | b \\| c | d |"
        self.assertEqual(bd.split_row(row), ["a", "`x | y`", "b | c", "d"])

    def test_parse_markdown_tables_by_section(self):
        md = ("# T\n\n## 4. 작업 대장\n\n상태: ☐ 대기 · ☑ 완료\n\n"
              "| ID | 상태 |\n|---|---|\n| P0-01 | ☑ |\n| P0-02 | ☐ |\n\n"
              "```\n## not a heading\n```\n"
              "## 5. 사실\n\n### 5.1 정정\n\n| 기존 | 원문 |\n|---|---|\n| a | b |\n")
        secs = bd.parse_markdown(md)
        by_num = {s["number"]: s for s in secs if s["number"]}
        self.assertEqual(by_num["4"]["tables"][0]["rows"], [["P0-01", "☑"], ["P0-02", "☐"]])
        self.assertEqual(by_num["5.1"]["tables"][0]["headers"], ["기존", "원문"])
        self.assertNotIn("not a heading", [s["title"] for s in secs])


if __name__ == "__main__":
    unittest.main()
