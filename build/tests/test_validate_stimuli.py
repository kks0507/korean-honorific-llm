#!/usr/bin/env python3
"""Unit tests for build/validate_stimuli.py — stdlib unittest, synthetic fixture.

Run:  python3 -m unittest discover -s build/tests -t build/tests -v
  or: python3 build/tests/test_validate_stimuli.py
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import validate_stimuli as vs  # noqa: E402

COLUMNS = vs.REQUIRED_COLUMNS

# --------------------------------------------------------------------------
# fake design files
# --------------------------------------------------------------------------

E1_DESIGN = {
    "id": "E1",
    "conditions": [
        {"code": "a", "A": "A1", "B": "B1"},
        {"code": "b", "A": "A1", "B": "B2"},
        {"code": "c", "A": "A2", "B": "B1"},
        {"code": "d", "A": "A2", "B": "B2"},
    ],
    "comprehension_question": {"template": "이야기 속 인물은 화자에게 어떤 사람입니까?"},
    "n_sets": 2,
    "item_rules": ["목표 문장은 8–12어절, 해체 평서문."],
}

E2_DESIGN = {
    "id": "E2",
    "conditions": E1_DESIGN["conditions"],
    "comprehension_question": {
        "template": "이 말에서 화자가 '-시-'로 높이려는 대상은 누구입니까?"},
    "n_sets": 1,
    "item_rules": [],
}

E3_DESIGN = {
    "id": "E3",
    "conditions": E1_DESIGN["conditions"],
    "comprehension_question": {
        "template": "이 말에서 화자가 높여서 대하고 있는 사람은 누구입니까?"},
    "n_sets": 1,
    "item_rules": [],
}

E4_DESIGN = {
    "id": "E4",
    "conditions": E1_DESIGN["conditions"],
    "comprehension_question": {"template": None},
    "n_sets": 2,
    "item_rules": [],
}

# --------------------------------------------------------------------------
# fake stimuli
# --------------------------------------------------------------------------

CTX = "화자는 친구와 이야기하고 있다. 이야기 속 인물은 화자의 {}."

# set -> (A1 person, A2 person, B1 sentence, B2 sentence, B1 region, B2 region,
#         options per cond as (options, answer))
E1_SETS = {
    1: {
        "A1": "할머니다", "A2": "여동생이다",
        "B1": "어제 오후에 시골에서 버스를 타고 혼자 서울로 올라오셨어.",
        "B2": "어제 오후에 시골에서 버스를 타고 혼자 서울로 올라왔어.",
        "cr1": "올라오셨어", "cr2": "올라왔어",
        "cq": {
            "a": ("할머니|여동생|할아버지|친구", "할머니"),
            "b": ("여동생|할머니|할아버지|친구", "할머니"),
            "c": ("할머니|남동생|여동생|친구", "여동생"),
            "d": ("할머니|남동생|친구|여동생", "여동생"),
        },
    },
    2: {
        "A1": "지도교수다", "A2": "학과 후배다",
        "B1": "지난주에 학회 발표를 일찍 마치고 바로 연구실로 돌아오셨어.",
        "B2": "지난주에 학회 발표를 일찍 마치고 바로 연구실로 돌아왔어.",
        "cr1": "돌아오셨어", "cr2": "돌아왔어",
        "cq": {
            "a": ("지도교수|학과 후배|학과장|친구", "지도교수"),
            "b": ("학과 후배|지도교수|학과장|친구", "지도교수"),
            "c": ("지도교수|사촌 동생|학과 후배|친구", "학과 후배"),
            "d": ("지도교수|사촌 동생|친구|학과 후배", "학과 후배"),
        },
    },
}

NORM = {"a": "적격", "b": "덜 선호 — 구어에서 -시- 생략이 흔함",
        "c": "부적격 — 비높임 대상에 -시-", "d": "적격"}


def _row(**fields) -> dict:
    row = {c: "" for c in COLUMNS}
    row.update(fields)
    return row


def e1_rows() -> list[dict]:
    rows = []
    for s, spec in E1_SETS.items():
        for cond in vs.CONDS:
            a_level, b_level = E1_DESIGN["conditions"][vs.COND_INDEX[cond]]["A"], \
                E1_DESIGN["conditions"][vs.COND_INDEX[cond]]["B"]
            person = spec["A1"] if a_level == "A1" else spec["A2"]
            options, answer = spec["cq"][cond]
            rows.append(_row(
                exp="E1", set_id=f"{s:02d}", cond=cond,
                A_level=a_level, B_level=b_level, role="target",
                context=CTX.format(person),
                sentence=spec["B1"] if b_level == "B1" else spec["B2"],
                critical_region=spec["cr1"] if b_level == "B1" else spec["cr2"],
                cq_question=E1_DESIGN["comprehension_question"]["template"],
                cq_options=options, cq_answer=answer,
                list=str(vs.expected_list(s, cond)),
                norm_status=NORM[cond], note="관계 유형 메모",
            ))
    return rows


def e2_rows() -> list[dict]:
    ctx = "약국에서 약사가 할머니 손님에게 말한다."
    q = E2_DESIGN["comprehension_question"]["template"]
    spec = {
        "a": ("할머니, 요즘 무릎이 많이 아프세요?", "아프세요?",
              "듣는 사람(할머니)|무릎|화자 자신|높이려는 대상이 없다", "듣는 사람(할머니)"),
        "b": ("할머니, 요즘 무릎이 많이 아파요?", "아파요?", "", ""),
        "c": ("할머니, 이 약은 다른 약보다 가격이 좀 비싸세요.", "비싸세요.",
              "듣는 사람(할머니)|가격|화자 자신|높이려는 대상이 없다", "듣는 사람(할머니)"),
        "d": ("할머니, 이 약은 다른 약보다 가격이 좀 비싸요.", "비싸요.", "", ""),
    }
    rows = []
    for cond, (sentence, cr, options, answer) in spec.items():
        cd = E2_DESIGN["conditions"][vs.COND_INDEX[cond]]
        rows.append(_row(
            exp="E2", set_id="01", cond=cond, A_level=cd["A"], B_level=cd["B"],
            role="target", context=ctx, sentence=sentence, critical_region=cr,
            cq_question=q if options else "", cq_options=options, cq_answer=answer,
            list=str(vs.expected_list(1, cond)),
            norm_status="적격" if cond != "c" else "비표준 — 사물 높임", note="",
        ))
    return rows


def e3_rows() -> list[dict]:
    q = E3_DESIGN["comprehension_question"]["template"]
    options = "듣는 사람|이야기 속 인물(동생)|둘 다|아무도 없다"
    spec = {
        "a": ("화자가 지도교수에게 자기 동생 이야기를 한다.", "동생이 어제 서울에 오셨어요.",
              "오셨어요", "둘 다", "부적격"),
        "b": ("화자가 지도교수에게 자기 동생 이야기를 한다.", "동생이 어제 서울에 왔어요.",
              "왔어요", "듣는 사람", "적격"),
        "c": ("화자가 친구에게 자기 동생 이야기를 한다.", "동생이 어제 서울에 오셨어.",
              "오셨어", "이야기 속 인물(동생)", "부적격"),
        "d": ("화자가 친구에게 자기 동생 이야기를 한다.", "동생이 어제 서울에 왔어.",
              "왔어", "아무도 없다", "적격"),
    }
    rows = []
    for cond, (ctx, sentence, cr, answer, norm) in spec.items():
        cd = E3_DESIGN["conditions"][vs.COND_INDEX[cond]]
        rows.append(_row(
            exp="E3", set_id="01", cond=cond, A_level=cd["A"], B_level=cd["B"],
            role="target", context=ctx, sentence=sentence, critical_region=cr,
            cq_question=q, cq_options=options, cq_answer=answer,
            list=str(vs.expected_list(1, cond)), norm_status=norm, note="",
        ))
    return rows


def e4_rows() -> list[dict]:
    b1_ctx = "화자가 친구에게 자기 조카 이야기를 한다."
    b2_ctx = "학생이 지도교수에게 말한다."
    return [
        _row(exp="E4", set_id="01", cond="b1", B_level="B1", role="violation",
             context=b1_ctx, sentence="조카가 벌써 유치원에 다니셔.",
             critical_region="다니셔", norm_status="부적격 — 형태 위반"),
        _row(exp="E4", set_id="01", cond="b1", B_level="B1", role="control",
             context=b1_ctx, sentence="조카가 벌써 유치원에 다녀.",
             critical_region="다녀", norm_status="적격"),
        _row(exp="E4", set_id="02", cond="b2", B_level="B2", role="violation",
             context=b2_ctx, sentence="교수님, 저 내일 수업에 못 가.",
             critical_region="가", norm_status="부적격 — 화용 위반"),
        _row(exp="E4", set_id="02", cond="b2", B_level="B2", role="control",
             context=b2_ctx, sentence="교수님, 저 내일 수업에 못 가요.",
             critical_region="가요", norm_status="적격"),
    ]


def find(rows: list[dict], set_id: str, cond: str, role: str | None = None) -> dict:
    for r in rows:
        if r["set_id"] == set_id and r["cond"] == cond and (role is None or r["role"] == role):
            return r
    raise KeyError((set_id, cond, role))


# --------------------------------------------------------------------------
# harness
# --------------------------------------------------------------------------

class StimuliTestCase(unittest.TestCase):
    """Builds a throwaway repo: content/experiments/*.json + content/stimuli/."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="stimuli-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "content" / "experiments").mkdir(parents=True)
        (self.root / "content" / "stimuli").mkdir(parents=True)
        for design in (E1_DESIGN, E2_DESIGN, E3_DESIGN, E4_DESIGN):
            self.write_design(design)

    def write_design(self, design: dict) -> None:
        path = self.root / "content" / "experiments" / f"{design['id']}.json"
        path.write_text(json.dumps(design, ensure_ascii=False), encoding="utf-8")

    def write_csv(self, exp: str, rows: list[dict], columns=COLUMNS) -> None:
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=columns, quoting=csv.QUOTE_ALL,
                                extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        path = self.root / "content" / "stimuli" / f"{exp}.csv"
        path.write_text(buf.getvalue(), encoding="utf-8")

    def run_validator(self, exp: str, rows: list[dict]) -> dict:
        self.write_csv(exp, rows)
        result = vs.validate(self.root, [exp])
        self.assertEqual(result["input_errors"], [])
        return result["files"][0]

    def run_main(self, *argv: str) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = vs.main([*argv, "--root", str(self.root)])
        return code, buf.getvalue()

    # assertions ----------------------------------------------------------
    def checks(self, issues: list[dict]) -> list[str]:
        return [i["check"] for i in issues]

    def assertNoErrors(self, res: dict) -> None:
        self.assertEqual(res["errors"], [], f"unexpected errors: {res['errors']}")

    def assertHas(self, issues: list[dict], check: str, **where) -> dict:
        for issue in issues:
            if issue["check"] == check and all(issue.get(k) == v for k, v in where.items()):
                return issue
        self.fail(f"no {check!r} {where} in {json.dumps(issues, ensure_ascii=False)}")


# --------------------------------------------------------------------------
# tests
# --------------------------------------------------------------------------

class TestValidFiles(StimuliTestCase):
    def test_valid_e1_passes_without_warnings(self):
        res = self.run_validator("E1", e1_rows())
        self.assertNoErrors(res)
        self.assertEqual(res["warnings"], [], f"unexpected warnings: {res['warnings']}")
        self.assertEqual(res["sets"], 2)
        table = res["tables"]["cond_by_list"]
        self.assertEqual(sum(table[c]["total"] for c in vs.CONDS), 8)
        self.assertEqual(res["tables"]["cq_answer_position"],
                         {"1": 2, "2": 2, "3": 2, "4": 2})

    def test_valid_e3_passes(self):
        res = self.run_validator("E3", e3_rows())
        self.assertNoErrors(res)
        self.assertEqual(res["warnings"], [], res["warnings"])

    def test_valid_e4_passes(self):
        res = self.run_validator("E4", e4_rows())
        self.assertNoErrors(res)
        self.assertEqual(res["warnings"], [], res["warnings"])
        self.assertEqual(res["tables"]["cond_by_role"],
                         {"b1": {"violation": 1, "control": 1},
                          "b2": {"violation": 1, "control": 1}})

    def test_exit_code_zero_and_human_report(self):
        self.write_csv("E1", e1_rows())
        code, out = self.run_main("E1")
        self.assertEqual(code, 0)
        self.assertIn("0 error(s)", out)
        self.assertIn("조건 × 목록", out)

    def test_json_flag_emits_parsable_result(self):
        self.write_csv("E1", e1_rows())
        code, out = self.run_main("E1", "--json")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["files"][0]["id"], "E1")

    def test_no_args_validates_every_csv_present(self):
        self.write_csv("E1", e1_rows())
        self.write_csv("E4", e4_rows())
        code, out = self.run_main("--json")
        self.assertEqual(code, 0)
        self.assertEqual([f["id"] for f in json.loads(out)["files"]], ["E1", "E4"])


class TestInputProblems(StimuliTestCase):
    def test_missing_csv_exits_2(self):
        code, out = self.run_main("E1", "--json")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["missing"], ["E1"])

    def test_no_csv_at_all_exits_2(self):
        self.assertEqual(self.run_main()[0], 2)

    def test_bad_id_exits_2(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.run_main("E9")[0], 2)

    def test_missing_design_file_exits_2(self):
        self.write_csv("E1", e1_rows())
        (self.root / "content" / "experiments" / "E1.json").unlink()
        self.assertEqual(self.run_main("E1")[0], 2)

    def test_non_utf8_csv_exits_2(self):
        path = self.root / "content" / "stimuli" / "E1.csv"
        path.write_bytes("\"exp\"\n\"실험\"\n".encode("cp949"))
        self.assertEqual(self.run_main("E1")[0], 2)


class TestErrors(StimuliTestCase):
    def test_missing_condition_is_error(self):
        rows = [r for r in e1_rows() if not (r["set_id"] == "02" and r["cond"] == "d")]
        res = self.run_validator("E1", rows)
        issue = self.assertHas(res["errors"], "set_conditions", set="02")
        self.assertIn("d", issue["msg"])

    def test_latin_square_violation_is_error(self):
        rows = e1_rows()
        a, b = find(rows, "01", "a"), find(rows, "01", "b")
        a["list"], b["list"] = b["list"], a["list"]
        res = self.run_validator("E1", rows)
        self.assertHas(res["errors"], "latin_square", set="01", cond="a")
        self.assertHas(res["errors"], "latin_square", set="01", cond="b")

    def test_latin_coverage_and_balance(self):
        rows = e1_rows()
        find(rows, "01", "a")["list"] = find(rows, "01", "b")["list"]
        res = self.run_validator("E1", rows)
        self.assertHas(res["errors"], "latin_coverage", set="01")

    def test_e1_a1_a2_sentence_mismatch_is_error(self):
        rows = e1_rows()
        find(rows, "02", "c")["sentence"] = (
            "지난주에 학회 발표를 일찍 마치고 곧장 연구실로 돌아오셨어.")
        res = self.run_validator("E1", rows)
        self.assertHas(res["errors"], "e1_same_sentence", set="02", cond="a/c")

    def test_comprehension_answer_mismatch_is_error(self):
        rows = e1_rows()
        find(rows, "01", "a")["cq_answer"] = "① 할머니"
        res = self.run_validator("E1", rows)
        self.assertHas(res["errors"], "cq_answer", set="01", cond="a")

    def test_comprehension_options_count_and_duplicates(self):
        rows = e1_rows()
        find(rows, "01", "a")["cq_options"] = "할머니|여동생|친구"
        find(rows, "01", "b")["cq_options"] = "할머니|여동생|할머니|친구"
        res = self.run_validator("E1", rows)
        self.assertHas(res["errors"], "cq_options", set="01", cond="a")
        self.assertHas(res["errors"], "cq_duplicate", set="01", cond="b")

    def test_cross_experiment_duplicate_sentence_is_error(self):
        other = e4_rows()
        other[0]["sentence"] = E1_SETS[1]["B1"]
        self.write_csv("E4", other)
        res = self.run_validator("E1", e1_rows())  # only E1 requested
        issue = self.assertHas(res["errors"], "cross_duplicate")
        self.assertIn("E4 01-violation", issue["msg"])
        # E1's own A1/A2 sharing is not a duplicate
        self.assertNotIn("duplicate_pair", self.checks(res["errors"]))

    def test_same_context_and_sentence_twice_is_error(self):
        rows = e1_rows()
        find(rows, "01", "c")["context"] = find(rows, "01", "a")["context"]
        res = self.run_validator("E1", rows)
        self.assertHas(res["errors"], "duplicate_pair")

    def test_two_eojeol_difference_is_error(self):
        rows = e1_rows()
        for cond in ("b", "d"):
            find(rows, "01", cond)["sentence"] = (
                "어제 오후에 시골에서 버스를 타고 혼자 부산으로 올라왔어.")
        res = self.run_validator("E1", rows)
        issue = self.assertHas(res["errors"], "eojeol_diff", set="01")
        self.assertIn("2개", issue["msg"])
        # a == c and b == d, so the identical pair is reported once
        self.assertEqual(self.checks(res["errors"]).count("eojeol_diff"), 1)

    def test_critical_region_outside_difference_is_error_in_e1(self):
        rows = e1_rows()
        find(rows, "01", "a")["critical_region"] = "시골에서"
        res = self.run_validator("E1", rows)
        self.assertHas(res["errors"], "critical_region", set="01", cond="a")

    def test_unknown_codes_and_design_mismatch(self):
        rows = e1_rows()
        find(rows, "01", "a")["cond"] = "e"
        find(rows, "01", "b")["A_level"] = "A2"
        find(rows, "01", "c")["role"] = "filler"
        find(rows, "01", "d")["exp"] = "E2"
        res = self.run_validator("E1", rows)
        self.assertHas(res["errors"], "unknown_value", set="01", cond="e")
        self.assertHas(res["errors"], "design_mismatch", set="01", cond="b")
        self.assertHas(res["errors"], "unknown_value", set="01", cond="c")
        self.assertHas(res["errors"], "exp_mismatch", set="01", cond="d")

    def test_empty_sentence_and_bad_norm_status(self):
        rows = e1_rows()
        find(rows, "02", "a")["sentence"] = "  "
        find(rows, "02", "b")["norm_status"] = "애매함"
        res = self.run_validator("E1", rows)
        self.assertHas(res["errors"], "empty_sentence", set="02", cond="a")
        self.assertHas(res["errors"], "norm_status", set="02", cond="b")

    def test_set_count_must_match_design(self):
        rows = [r for r in e1_rows() if r["set_id"] == "01"]
        res = self.run_validator("E1", rows)
        self.assertHas(res["errors"], "set_count")

    def test_missing_column_is_error(self):
        self.write_csv("E1", e1_rows(), columns=[c for c in COLUMNS if c != "list"])
        res = vs.validate(self.root, ["E1"])["files"][0]
        self.assertHas(res["errors"], "columns")

    def test_e3_endings_must_be_the_only_difference(self):
        rows = e3_rows()
        find(rows, "01", "c")["sentence"] = "동생이 어제 서울로 오셨어."
        res = self.run_validator("E3", rows)
        self.assertHas(res["errors"], "e3_ending", set="01", cond="a/c")

    def test_e4_diff_range_and_balance(self):
        rows = e4_rows()
        find(rows, "01", "b1", "control")["sentence"] = "그 아이가 이미 학교에 다녀."
        for r in rows:
            if r["set_id"] == "02":
                r["cond"], r["B_level"] = "b1", "B1"
        res = self.run_validator("E4", rows)
        self.assertHas(res["errors"], "eojeol_diff", set="01")
        self.assertHas(res["errors"], "e4_balance")

    def test_exit_code_one_when_errors(self):
        rows = e1_rows()
        find(rows, "01", "a")["cq_answer"] = "고모"
        self.write_csv("E1", rows)
        self.assertEqual(self.run_main("E1")[0], 1)


class TestWarnings(StimuliTestCase):
    def test_eojeol_count_spread_is_warning(self):
        res = self.run_validator("E2", e2_rows())
        self.assertNoErrors(res)
        issue = self.assertHas(res["warnings"], "length_spread", set="01")
        self.assertIn("a=5", issue["msg"])
        self.assertIn("c=8", issue["msg"])

    def test_spread_warning_does_not_fail_the_run(self):
        self.write_csv("E2", e2_rows())
        self.assertEqual(self.run_main("E2")[0], 0)

    def test_answer_position_skew_is_warning(self):
        rows = e1_rows()
        for r in rows:
            opts = r["cq_options"].split("|")
            opts.remove(r["cq_answer"])
            r["cq_options"] = "|".join([r["cq_answer"], *opts])
        res = self.run_validator("E1", rows)
        self.assertNoErrors(res)
        self.assertHas(res["warnings"], "cq_position_skew")
        self.assertEqual(res["tables"]["cq_answer_position"],
                         {"1": 8, "2": 0, "3": 0, "4": 0})

    def test_review_note_is_listed(self):
        rows = e1_rows()
        find(rows, "02", "b")["note"] = "검토 필요: 생략형이 너무 자연스러울 수 있음"
        res = self.run_validator("E1", rows)
        self.assertNoErrors(res)
        self.assertHas(res["warnings"], "review_needed", set="02")
        self.assertEqual(res["review_sets"][0]["set"], "02")

    def test_repeated_predicate_stem_is_warning(self):
        rows = e3_rows() * 3
        for i, r in enumerate(rows):
            r = rows[i] = dict(r)
            r["set_id"] = f"{i // 4 + 1:02d}"
            r["list"] = str(vs.expected_list(i // 4 + 1, r["cond"]))
            r["context"] = f"{r['context']} ({i // 4 + 1})"
        self.write_design({**E3_DESIGN, "n_sets": 3})
        res = self.run_validator("E3", rows)
        issue = self.assertHas(res["warnings"], "predicate_repeat")
        self.assertIn("01, 02, 03", issue["msg"])

    def test_length_range_from_item_rules(self):
        rows = e1_rows()
        for cond in vs.CONDS:
            r = find(rows, "01", cond)
            r["sentence"] = r["sentence"].replace("어제 오후에 ", "")
        res = self.run_validator("E1", rows)
        self.assertNoErrors(res)
        self.assertHas(res["warnings"], "length_range")

    def test_bom_is_warning_not_column_error(self):
        self.write_csv("E1", e1_rows())
        path = self.root / "content" / "stimuli" / "E1.csv"
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        res = vs.validate(self.root, ["E1"])["files"][0]
        self.assertNoErrors(res)
        self.assertHas(res["warnings"], "bom")


class TestHelpers(unittest.TestCase):
    def test_expected_list_rule(self):
        # s = 1: a -> 4, b -> 1, c -> 2, d -> 3
        self.assertEqual([vs.expected_list(1, c) for c in vs.CONDS], [4, 1, 2, 3])
        self.assertEqual([vs.expected_list(4, c) for c in vs.CONDS], [1, 2, 3, 4])

    def test_eojeol_diff(self):
        self.assertEqual(vs.eojeol_diff("어제 올라오셨어.", "어제 올라왔어.")[0], 1)
        self.assertEqual(vs.eojeol_diff("못 가.", "못 가요.")[1:], (["가."], ["가요."]))
        self.assertEqual(vs.eojeol_diff("가 나 다", "가 나 다 라")[0], 1)
        self.assertEqual(vs.eojeol_diff("가 나 다", "마 나 바")[0], 2)
        self.assertEqual(vs.eojeol_diff("같다", "같다")[0], 0)

    def test_only_last_differs(self):
        self.assertTrue(vs.only_last_differs("동생이 왔어요.", "동생이 왔어."))
        self.assertFalse(vs.only_last_differs("동생이 왔어.", "동생이 왔어."))
        self.assertFalse(vs.only_last_differs("동생이 왔어요.", "동생은 왔어."))

    def test_predicate_stem(self):
        self.assertEqual(vs.predicate_stem("어제 올라오셨어."), "올라")
        self.assertEqual(vs.predicate_stem("못 가 ."), "가")
        self.assertIsNone(vs.predicate_stem("  "))


if __name__ == "__main__":
    unittest.main(verbosity=2)
