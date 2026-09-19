#!/usr/bin/env python3
"""Unit tests for build/validate_cards.py — stdlib unittest, synthetic fixture.

Run:  python3 -m unittest discover -s build/tests -v
  or: python3 build/tests/test_validate_cards.py
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import validate_cards as vc  # noqa: E402

PAGES = 4
PID = "P02"

PAGE_TEXT = {
    1: "Korean honorifics encode social relations between speaker and subject.\n"
       "We evaluate eight models on a full paradigm.",
    2: "The honorific marker -si agreed with the subject in 88.2 percent of items.\n"
       "Accuracy reached 34.7 and the effect size was 0.66 overall.",
    3: "Multilingual decoder models lagged behind Korean-focused encoders.\n"
       "We collected 1,500 stimulus sentences for the evaluation set.",
    4: "Future work should extend the paradigm to addressee honorifics.",
}


def _item(src: str = "p.1") -> dict:
    return {"label": "라벨", "text": "설명", "src": src}


def _valid_card() -> dict:
    return {
        "id": PID,
        "role": "subdata",
        "short": "Cho & Kwon (2026)",
        "title": "Korean Honorifics in LLMs",
        "title_ko": "대규모 언어모델의 한국어 경어",
        "citation": {"apa": "Cho, S., & Kwon, N. (2026).", "year": 2026,
                     "venue": "ACL", "status": "preprint", "doi": None,
                     "url": None, "bib_notes": "원문 미표기"},
        "one_line": "경어 표지 처리 능력을 평가한다.",
        "w5h1": {
            k: {"headline": "한 문장 요약", "items": [_item()]}
            for k in vc.W5H1_KEYS
        },
        "layers": {
            "word": [
                {"term": f"term{i}", "gloss_ko": "용어", "definition": "정의",
                 "note": "비고", "src": "p.1"}
                for i in range(4)
            ],
            "sentence": [
                {"kind": "result",
                 "quote": "The honorific marker -si agreed with the subject",
                 "paraphrase_ko": "주어와 일치했다.",
                 "numbers": ["88.2%"], "src": "p.2"},
                {"kind": "claim",
                 "quote": "Korean honorifics encode social relations",
                 "paraphrase_ko": "사회적 관계를 부호화한다.",
                 "numbers": [], "src": "p.1"},
                {"kind": "method",
                 "quote": "We collected 1,500 stimulus sentences",
                 "paraphrase_ko": "자극 문장을 수집했다.",
                 "numbers": ["1,500"], "src": "p.3"},
                {"kind": "future_work",
                 "quote": "Future work should extend the paradigm",
                 "paraphrase_ko": "패러다임 확장이 필요하다.",
                 "numbers": [], "src": "p.4"},
                {"kind": "limitation",
                 "quote": "Multilingual decoder models lagged behind",
                 "paraphrase_ko": "다국어 모델이 뒤처졌다.",
                 "numbers": [], "src": "p.3"},
                {"kind": "hypothesis",
                 "quote": "We evaluate eight models on a full paradigm",
                 "paraphrase_ko": "여덟 모델을 평가한다.",
                 "numbers": [], "src": "p.1"},
            ],
            "paragraph": [
                {"section": "Intro", "move": "background",
                 "summary_ko": "배경", "src": "p.1"},
                {"section": "Intro", "move": "gap", "summary_ko": "공백",
                 "src": "p.1"},
                {"section": "Method", "move": "method", "summary_ko": "방법",
                 "src": "p.2"},
                {"section": "Results", "move": "evidence", "summary_ko": "근거",
                 "src": "p.2-3"},
            ],
            "context": [
                {"axis": "lineage", "text_ko": "계보", "related": [], "src": "p.1"},
                {"axis": "theory", "text_ko": "이론", "related": [], "src": "p.1"},
                {"axis": "model_generation", "text_ko": "세대", "related": [],
                 "src": "p.2"},
            ],
        },
        "design": {"phenomenon": "주어 높임", "stimuli": "문장", "conditions": [],
                   "n_items": 1500, "measures": [], "models": [], "humans": None,
                   "stats": "혼합효과모형", "is_factorial": "아님 — 단일 요인"},
        "stimulus_examples": [
            {"ko": "교수님께서 편지를 쓰셨다.", "gloss": "professor-NOM.HON ...",
             "condition": "H", "src": "p.2"}
        ],
        "key_numbers": [
            {"what": "정확도", "value": "34.7%", "src": "p.2"},
            {"what": "효과크기", "value": "0.66", "src": "p.2"},
        ],
        "limitations": [
            {"text_ko": "모델 세대가 낡았다.", "stated_by": "author", "src": "p.4"}
        ],
        "successor_hooks": [
            {"id": "P02-H1", "hook_ko": "최신 모델 재검증", "basis_ko": "근거",
             "kind": "model_generation", "src": "p.4"},
            {"id": "P02-H2", "hook_ko": "청자 높임 확장", "basis_ko": "근거",
             "kind": "author_future_work", "src": "p.4"},
        ],
        "open_materials": [{"what": "자극", "url": "https://example.org/stimuli"}],
        "prior_analysis_check": {"source": "없음", "agreements": "해당 없음",
                                 "discrepancies": []},
        "verification": {"status": "draft", "by": "agent", "notes": []},
    }


class CardTestCase(unittest.TestCase):
    """Builds a throwaway repo: manifest + page text + content/papers/."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="cards-"))
        self.addCleanup(shutil.rmtree, self.root, True)

        txt = self.root / "papers" / "txt"
        txt.mkdir(parents=True)
        (self.root / "content" / "papers").mkdir(parents=True)

        body = "\n".join(
            f"===== [{PID} p.{n}/{PAGES}] =====\n{PAGE_TEXT[n]}\n"
            for n in range(1, PAGES + 1)
        )
        (txt / f"{PID}.txt").write_text(body, encoding="utf-8")
        (txt / f"{PID}.layout.txt").write_text(body, encoding="utf-8")
        (txt / "manifest.json").write_text(json.dumps([{
            "id": PID, "pdf": f"{PID}_Fake.pdf", "pages": PAGES, "words": 60,
            "words_per_page": [15, 15, 15, 15], "sha256": "0" * 64,
            "blank_pages": [],
        }]), encoding="utf-8")

    def write(self, card: dict) -> None:
        path = self.root / "content" / "papers" / f"{PID}.json"
        path.write_text(json.dumps(card, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    def run_validator(self, card: dict) -> dict:
        self.write(card)
        return vc.validate(self.root, [PID])["files"][0]

    def assertNoErrors(self, res: dict) -> None:
        self.assertEqual(res["errors"], [], f"unexpected errors: {res['errors']}")

    def run_main(self, *argv: str) -> tuple[int, str]:
        """Invoke the CLI, capturing its report instead of printing it."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = vc.main([*argv, "--root", str(self.root)])
        return code, buf.getvalue()


class TestValidCard(CardTestCase):
    def test_valid_card_passes(self):
        res = self.run_validator(_valid_card())
        self.assertNoErrors(res)
        self.assertEqual(res["warnings"], [],
                         f"unexpected warnings: {res['warnings']}")

    def test_exit_code_zero_for_valid_card(self):
        self.write(_valid_card())
        code, out = self.run_main(PID)
        self.assertEqual(code, 0)
        self.assertIn("0 error(s)", out)

    def test_json_flag_emits_parsable_result(self):
        self.write(_valid_card())
        code, out = self.run_main(PID, "--json")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["totals"]["files"], 1)
        self.assertEqual(payload["files"][0]["id"], PID)

    def test_no_args_validates_every_card_present(self):
        self.write(_valid_card())
        code, out = self.run_main("--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["totals"]["files"], 1)

    def test_missing_requested_card_fails(self):
        self.write(_valid_card())
        code, out = self.run_main("P09", "--json")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["missing"], ["P09"])


class TestErrors(CardTestCase):
    def test_missing_src_is_error(self):
        card = _valid_card()
        del card["layers"]["word"][0]["src"]
        res = self.run_validator(card)
        self.assertTrue(
            any("layers.word[0]" in e and "missing `src`" in e for e in res["errors"]),
            res["errors"],
        )

    def test_missing_src_in_w5h1_item_is_error(self):
        card = _valid_card()
        del card["w5h1"]["who"]["items"][0]["src"]
        res = self.run_validator(card)
        self.assertTrue(
            any("w5h1.who.items[0]" in e and "missing `src`" in e
                for e in res["errors"]),
            res["errors"],
        )

    def test_out_of_range_page_is_error(self):
        card = _valid_card()
        card["layers"]["paragraph"][0]["src"] = "p.99"
        res = self.run_validator(card)
        self.assertTrue(
            any("outside 1..4" in e for e in res["errors"]), res["errors"]
        )

    def test_malformed_src_is_error(self):
        card = _valid_card()
        card["layers"]["context"][0]["src"] = "page 3"
        res = self.run_validator(card)
        self.assertTrue(
            any("does not match" in e for e in res["errors"]), res["errors"]
        )

    def test_sixteen_token_quote_is_error(self):
        card = _valid_card()
        card["layers"]["sentence"][0]["quote"] = " ".join(f"w{i}" for i in range(16))
        res = self.run_validator(card)
        self.assertTrue(
            any("16 tokens" in e for e in res["errors"]), res["errors"]
        )

    def test_fifteen_token_quote_is_not_a_length_error(self):
        card = _valid_card()
        card["layers"]["sentence"][0]["quote"] = " ".join(f"w{i}" for i in range(15))
        res = self.run_validator(card)
        self.assertFalse(any("tokens, limit" in e for e in res["errors"]),
                         res["errors"])

    def test_id_filename_mismatch_is_error(self):
        card = _valid_card()
        card["id"] = "P07"
        res = self.run_validator(card)
        self.assertTrue(
            any("does not match filename" in e for e in res["errors"]), res["errors"]
        )

    def test_bad_role_is_error(self):
        card = _valid_card()
        card["role"] = "supporting"
        res = self.run_validator(card)
        self.assertTrue(any("`role`" in e for e in res["errors"]), res["errors"])

    def test_missing_top_level_key_is_error(self):
        card = _valid_card()
        del card["design"]
        res = self.run_validator(card)
        self.assertTrue(
            any("missing required top-level key `design`" in e
                for e in res["errors"]), res["errors"]
        )

    def test_w5h1_missing_key_is_error(self):
        card = _valid_card()
        del card["w5h1"]["why"]
        res = self.run_validator(card)
        self.assertTrue(any("w5h1: missing `why`" in e for e in res["errors"]),
                        res["errors"])

    def test_w5h1_empty_items_is_error(self):
        card = _valid_card()
        card["w5h1"]["how"]["items"] = []
        res = self.run_validator(card)
        self.assertTrue(any("`items` missing or empty" in e for e in res["errors"]),
                        res["errors"])

    def test_w5h1_missing_headline_is_error(self):
        card = _valid_card()
        del card["w5h1"]["what"]["headline"]
        res = self.run_validator(card)
        self.assertTrue(any("`headline`" in e for e in res["errors"]), res["errors"])

    def test_layer_minimum_for_subdata(self):
        card = _valid_card()
        card["layers"]["sentence"] = card["layers"]["sentence"][:5]
        res = self.run_validator(card)
        self.assertTrue(
            any("layers.sentence: 5 entries" in e and ">= 6" in e
                for e in res["errors"]), res["errors"]
        )

    def test_core_role_raises_layer_minimums(self):
        card = _valid_card()
        card["role"] = "core"
        res = self.run_validator(card)
        msgs = " ".join(res["errors"])
        self.assertIn("layers.word: 4 entries", msgs)
        self.assertIn(">= 8", msgs)
        self.assertIn("successor_hooks: 2 entries", msgs)

    def test_enum_violations(self):
        card = _valid_card()
        card["layers"]["sentence"][0]["kind"] = "finding"
        card["layers"]["paragraph"][0]["move"] = "intro"
        card["layers"]["context"][0]["axis"] = "history"
        card["successor_hooks"][0]["kind"] = "todo"
        card["limitations"][0]["stated_by"] = "reviewer"
        card["citation"]["status"] = "submitted"
        card["verification"]["status"] = "done"
        res = self.run_validator(card)
        msgs = " ".join(res["errors"])
        for field in ["`kind`", "`move`", "`axis`", "`stated_by`", "`status`"]:
            self.assertIn(field, msgs)
        self.assertGreaterEqual(len(res["errors"]), 7, res["errors"])

    def test_bad_hook_id_is_error(self):
        card = _valid_card()
        card["successor_hooks"][0]["id"] = "H1"
        res = self.run_validator(card)
        self.assertTrue(any("`P02-H1`" in e for e in res["errors"]), res["errors"])

    def test_hook_id_of_other_paper_is_error(self):
        card = _valid_card()
        card["successor_hooks"][0]["id"] = "P09-H1"
        res = self.run_validator(card)
        self.assertTrue(
            any("does not belong to P02" in e for e in res["errors"]), res["errors"]
        )

    def test_invalid_json_is_error(self):
        path = self.root / "content" / "papers" / f"{PID}.json"
        path.write_text("{ not json", encoding="utf-8")
        res = vc.validate(self.root, [PID])["files"][0]
        self.assertTrue(any("invalid JSON" in e for e in res["errors"]),
                        res["errors"])

    def test_exit_code_one_when_errors(self):
        card = _valid_card()
        del card["layers"]["word"][0]["src"]
        self.write(card)
        self.assertEqual(self.run_main(PID)[0], 1)


class TestWarnings(CardTestCase):
    def test_number_absent_from_page_is_warning_only(self):
        card = _valid_card()
        card["key_numbers"][0]["value"] = "99.9%"
        res = self.run_validator(card)
        self.assertNoErrors(res)
        self.assertTrue(
            any("key_numbers[0].value" in w and "'99.9'" in w
                for w in res["warnings"]), res["warnings"]
        )

    def test_sentence_numbers_absent_is_warning_only(self):
        card = _valid_card()
        card["layers"]["sentence"][0]["numbers"] = ["12.5%"]
        res = self.run_validator(card)
        self.assertNoErrors(res)
        self.assertTrue(
            any("layers.sentence[0].numbers[0]" in w for w in res["warnings"]),
            res["warnings"],
        )

    def test_recalculated_value_is_skipped(self):
        card = _valid_card()
        card["key_numbers"][0]["value"] = "77.7% (재계산)"
        res = self.run_validator(card)
        self.assertNoErrors(res)
        self.assertEqual(res["warnings"], [], res["warnings"])

    def test_figure_read_value_is_skipped(self):
        card = _valid_card()
        card["key_numbers"][0]["value"] = "0.98 / 0.98 (그림 판독)"
        res = self.run_validator(card)
        self.assertNoErrors(res)
        self.assertEqual(res["warnings"], [], res["warnings"])

    def test_number_found_on_neighbouring_page(self):
        card = _valid_card()
        # 0.66 lives on p.2; cite p.3 and the ±1 window must still find it.
        card["key_numbers"][1]["src"] = "p.3"
        res = self.run_validator(card)
        self.assertNoErrors(res)
        self.assertEqual(res["warnings"], [], res["warnings"])

    def test_quote_not_on_page_is_warning_only(self):
        card = _valid_card()
        card["layers"]["sentence"][0]["quote"] = "Completely fabricated sentence here"
        res = self.run_validator(card)
        self.assertNoErrors(res)
        self.assertTrue(
            any("layers.sentence[0]" in w and "quote not found" in w
                for w in res["warnings"]), res["warnings"]
        )

    def test_quote_matches_despite_punctuation_and_case(self):
        card = _valid_card()
        card["layers"]["sentence"][1]["quote"] = "KOREAN “honorifics” encode—social relations"
        res = self.run_validator(card)
        self.assertNoErrors(res)
        self.assertEqual(res["warnings"], [], res["warnings"])

    def test_quote_matches_across_hyphenated_line_break(self):
        txt = self.root / "papers" / "txt" / f"{PID}.txt"
        txt.write_text(
            txt.read_text(encoding="utf-8").replace(
                "social relations", "so-\ncial relations"),
            encoding="utf-8",
        )
        card = _valid_card()
        card["layers"]["sentence"][1]["quote"] = "honorifics encode social relations"
        res = self.run_validator(card)
        self.assertEqual(res["warnings"], [], res["warnings"])

    def test_warnings_do_not_fail_the_run(self):
        card = _valid_card()
        card["key_numbers"][0]["value"] = "99.9%"
        self.write(card)
        self.assertEqual(self.run_main(PID)[0], 0)


class TestHelpers(unittest.TestCase):
    def test_src_pages(self):
        self.assertEqual(vc.src_pages("p.3"), [3])
        self.assertEqual(vc.src_pages("p.3-5"), [3, 4, 5])
        self.assertEqual(vc.src_pages("p.6 Table 2"), [6])
        self.assertEqual(vc.src_pages("p.3 §2.1"), [3])
        self.assertIsNone(vc.src_pages("3"))
        self.assertIsNone(vc.src_pages("pp.3"))

    def test_numeric_tokens(self):
        self.assertEqual(vc.numeric_tokens("34.7%"), ["34.7"])
        self.assertEqual(vc.numeric_tokens("N = 44"), ["44"])
        self.assertEqual(vc.numeric_tokens("1,500 items"), ["1,500"])
        self.assertEqual(vc.numeric_tokens("원문 미표기"), [])

    def test_number_present_respects_boundaries(self):
        self.assertTrue(vc.number_present("accuracy 34.7 percent", "34.7"))
        self.assertFalse(vc.number_present("accuracy 134.75 percent", "34.7"))
        self.assertTrue(vc.number_present("we used 1500 items", "1,500"))

    def test_valid_card_fixture_is_deep_copied(self):
        a, b = _valid_card(), _valid_card()
        a["layers"]["word"][0]["src"] = "p.9"
        self.assertNotEqual(a["layers"]["word"][0]["src"],
                            b["layers"]["word"][0]["src"])
        self.assertEqual(b, copy.deepcopy(b))


if __name__ == "__main__":
    unittest.main(verbosity=2)
