#!/usr/bin/env python3
"""Validate 자극 CSV files `content/stimuli/E?.csv`.

The CSV contract is docs/에이전트-지침/P4_자극작성.md; the per-experiment design
(`n_sets`, `conditions`, `comprehension_question.template`, `item_rules`) is read
from `content/experiments/E?.json`.

ERRORs break the design (exit 1).  WARNINGs flag things a person should look at
and never fail the run.  Input problems -- a requested CSV or its design file is
missing, a file is not UTF-8 or not parseable, a bad argument -- exit 2.

Usage:
    python3 build/validate_stimuli.py [E1 E2 ...]   # no args = every E?.csv present
    python3 build/validate_stimuli.py E1 --json      # machine-readable dump
"""

from __future__ import annotations

import argparse
import codecs
import csv
import difflib
import io
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

# --------------------------------------------------------------------------
# contract constants (docs/에이전트-지침/P4_자극작성.md is the source of truth)
# --------------------------------------------------------------------------

REQUIRED_COLUMNS = [
    "exp", "set_id", "cond", "A_level", "B_level", "role", "context",
    "sentence", "critical_region", "cq_question", "cq_options", "cq_answer",
    "list", "norm_status", "note",
]

EXP_RE = re.compile(r"^E[1-4]$")
FACTORIAL = ("E1", "E2", "E3")          # 2x2 within-set designs, a-d per set
COND_INDEX = {"a": 0, "b": 1, "c": 2, "d": 3}   # k in the Latin-square rule
CONDS = tuple(COND_INDEX)
A_LEVELS = ("A1", "A2")
B_LEVELS = ("B1", "B2")
TARGET_ROLE = "target"
E4_CONDS = {"b1": "B1", "b2": "B2"}      # E4 rows carry the violation type only
E4_ROLES = ("violation", "control")
N_LISTS = 4
LIST_VALUES = tuple(str(n) for n in range(1, N_LISTS + 1))
N_OPTIONS = 4
POS_MARKS = "①②③④"
NORM_PREFIXES = ("적격", "덜 선호", "부적격", "비표준")
REVIEW_PREFIX = "검토 필요:"

# E2.json comprehension_question.role: "B1 조건에서만 묻는다."
CQ_B1_ONLY = {"E2"}

# thresholds
LENGTH_SPREAD_MAX = 1           # eojeol-count spread allowed inside a set
E4_DIFF_RANGE = (1, 2)          # violation vs control eojeol differences
STEM_CHARS = 2                  # predicate "stem" = first 2 chars of last eojeol
STEM_REPEAT_MIN = 3             # warn when a stem is used by >= 3 sets
SKEW_MIN_ITEMS = 4              # need at least this many answers to judge skew
SKEW_MAX_SHARE = 0.5            # warn when one position holds > 50% of answers
LABEL_LIMIT = 12                # rows listed in an aggregated warning

# "목표 문장은 8–12어절" in item_rules -> (8, 12)
LENGTH_RULE_RE = re.compile(r"(\d+)\s*[–~-]\s*(\d+)\s*어절")
DIGITS_RE = re.compile(r"^[0-9]+$")
TWO_DIGITS_RE = re.compile(r"^[0-9]{2}$")


class InputError(Exception):
    """A problem with the inputs themselves (exit 2), not with their content."""


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def expected_list(set_no: int, cond: str) -> int:
    """Latin-square list for set s and condition k: ((k - s) mod 4) + 1."""
    return ((COND_INDEX[cond] - set_no) % N_LISTS) + 1


def eojeols(sentence: str) -> list[str]:
    return sentence.split()


def eojeol_diff(s1: str, s2: str) -> tuple[int, list[str], list[str]]:
    """Word-level (어절) difference: (count, differing tokens of s1, of s2).

    The count is the size of every non-equal block, taking the longer side of
    a replacement, so one substituted eojeol counts 1 and an extra eojeol
    counts 1 as well.
    """
    t1, t2 = eojeols(s1), eojeols(s2)
    sm = difflib.SequenceMatcher(a=t1, b=t2, autojunk=False)
    count = 0
    d1: list[str] = []
    d2: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        count += max(i2 - i1, j2 - j1)
        d1.extend(t1[i1:i2])
        d2.extend(t2[j1:j2])
    return count, d1, d2


def only_last_differs(s1: str, s2: str) -> bool:
    """Same eojeol count, every eojeol equal except the last, which differs."""
    t1, t2 = eojeols(s1), eojeols(s2)
    return (len(t1) == len(t2) and len(t1) >= 1
            and t1[:-1] == t2[:-1] and t1[-1] != t2[-1])


def _bare(text: str) -> str:
    return "".join(ch for ch in text if ch.isalnum())


def critical_region_hits(cr: str, tokens: list[str]) -> bool:
    """Does the critical region overlap one of the differing eojeols?"""
    parts = [p for p in cr.split() if _bare(p)]
    for part in parts:
        for tok in tokens:
            if part in tok or _bare(part) == _bare(tok):
                return True
    return False


def predicate_stem(sentence: str) -> str | None:
    """Crude predicate stem: first two letters of the last word-bearing eojeol."""
    for tok in reversed(eojeols(sentence)):
        core = _bare(tok)
        if core:
            return core[:STEM_CHARS]
    return None


def norm_text(text: str) -> str:
    """Comparison key for duplicate checks: NFC + collapsed whitespace."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def shorten(text: str, limit: int = 60) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


# --------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------

class Design:
    def __init__(self, exp: str, n_sets: int, cond_map: dict[str, tuple],
                 cq_template: str | None, length_range: tuple[int, int] | None):
        self.exp = exp
        self.n_sets = n_sets
        self.cond_map = cond_map
        self.cq_template = cq_template
        self.length_range = length_range


def load_design(root: Path, exp: str) -> Design:
    path = Path(root) / "content" / "experiments" / f"{exp}.json"
    if not path.exists():
        raise InputError(f"{exp}: 설계 파일 content/experiments/{exp}.json 없음")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"{exp}: 설계 파일을 읽을 수 없음 ({exc})") from exc
    if not isinstance(data, dict):
        raise InputError(f"{exp}: 설계 파일 최상위가 객체가 아님")

    n_sets = data.get("n_sets")
    if not isinstance(n_sets, int) or isinstance(n_sets, bool) or n_sets < 1:
        raise InputError(f"{exp}: 설계 파일 `n_sets`가 양의 정수가 아님 ({n_sets!r})")

    cond_map: dict[str, tuple] = {}
    if exp in FACTORIAL:
        for c in data.get("conditions") or []:
            if isinstance(c, dict) and c.get("code") in COND_INDEX:
                cond_map[c["code"]] = (c.get("A"), c.get("B"))
        if set(cond_map) != set(CONDS):
            raise InputError(f"{exp}: 설계 파일 `conditions`에 a·b·c·d가 모두 있어야 함")

    cq = data.get("comprehension_question")
    template = cq.get("template") if isinstance(cq, dict) else None
    template = template.strip() if isinstance(template, str) and template.strip() else None

    length_range = None
    for rule in data.get("item_rules") or []:
        if isinstance(rule, str):
            m = LENGTH_RULE_RE.search(rule)
            if m:
                length_range = (int(m.group(1)), int(m.group(2)))
                break

    return Design(exp, n_sets, cond_map, template, length_range)


def read_csv(path: Path) -> tuple[list[str], list[tuple[int, dict]], bool]:
    """-> (header, [(line_number, record)], has_bom). Raises InputError."""
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise InputError(f"{Path(path).name}: 읽을 수 없음 ({exc})") from exc
    has_bom = raw.startswith(codecs.BOM_UTF8)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InputError(
            f"{Path(path).name}: UTF-8이 아님 (byte {exc.start}: {exc.reason})"
        ) from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    try:
        header = [h.strip() for h in (reader.fieldnames or [])]
        reader.fieldnames = header
        records = [(reader.line_num, rec) for rec in reader]
    except csv.Error as exc:
        raise InputError(f"{Path(path).name}: CSV 구문 오류 ({exc})") from exc
    return header, records, has_bom


# --------------------------------------------------------------------------
# rows and report
# --------------------------------------------------------------------------

class Row:
    def __init__(self, exp: str, line: int, rec: dict):
        def g(key: str) -> str:
            value = rec.get(key)
            return value if isinstance(value, str) else ""

        self.is_e4 = exp == "E4"
        self.line = line
        self.exp = g("exp").strip()
        self.set_id = g("set_id").strip()
        self.cond = g("cond").strip()
        self.a_level = g("A_level").strip()
        self.b_level = g("B_level").strip()
        self.role = g("role").strip()
        self.context = g("context")
        self.sentence = g("sentence")
        self.cr = g("critical_region")
        self.cq_question = g("cq_question")
        self.cq_options = g("cq_options")
        self.cq_answer = g("cq_answer")
        self.list = g("list").strip()
        self.norm_status = g("norm_status")
        self.note = g("note")
        # filled in by check_row
        self.set_no: int | None = None
        self.cond_ok = False
        self.answer_pos: int | None = None

    @property
    def tag(self) -> str:
        """Condition label used in messages: `a` (E1–E3) or `b1 violation` (E4)."""
        if self.is_e4:
            return " ".join(p for p in (self.cond, self.role) if p) or "?"
        return self.cond or "?"

    @property
    def short(self) -> str:
        """Compact row id for aggregated warnings: `01a` / `01-violation`."""
        sid = self.set_id or "?"
        if self.is_e4:
            return f"{sid}-{self.role or '?'}"
        return f"{sid}{self.cond or '?'}"


def _labels(rows: list[Row], extra=None) -> str:
    labs = [r.short + (f"({extra(r)})" if extra else "") for r in rows]
    text = ", ".join(labs[:LABEL_LIMIT])
    if len(labs) > LABEL_LIMIT:
        text += f" 외 {len(labs) - LABEL_LIMIT}개"
    return text


class Report:
    def __init__(self, exp: str, path: str, n_sets: int):
        self.id = exp
        self.path = path
        self.n_sets = n_sets
        self.rows = 0
        self.sets = 0
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.tables: dict = {}
        self.review_sets: list[dict] = []

    @staticmethod
    def _issue(check: str, msg: str, row: Row | None, set_id: str | None,
               cond: str | None) -> dict:
        issue = {"check": check, "msg": msg, "set": None, "cond": None, "line": None}
        if row is not None:
            issue.update(set=row.set_id or None, cond=row.tag, line=row.line)
        if set_id is not None:
            issue["set"] = set_id
        if cond is not None:
            issue["cond"] = cond
        return issue

    def error(self, check: str, msg: str, row: Row | None = None, *,
              set_id: str | None = None, cond: str | None = None) -> None:
        self.errors.append(self._issue(check, msg, row, set_id, cond))

    def warn(self, check: str, msg: str, row: Row | None = None, *,
             set_id: str | None = None, cond: str | None = None) -> None:
        self.warnings.append(self._issue(check, msg, row, set_id, cond))

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "rows": self.rows,
            "sets": self.sets,
            "n_sets": self.n_sets,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "tables": self.tables,
            "review_sets": self.review_sets,
        }


# --------------------------------------------------------------------------
# row-level checks
# --------------------------------------------------------------------------

def check_row(rep: Report, exp: str, row: Row, rec: dict, design: Design,
              agg: dict[str, list[Row]]) -> None:
    if None in rec:
        rep.error("fields", f"필드가 헤더보다 {len(rec[None])}개 많음", row)
    short = [k for k, v in rec.items() if k is not None and v is None]
    if short:
        rep.error("fields", f"필드가 헤더보다 적음 (값 없는 열: {', '.join(short)})", row)

    # --- exp / set_id -------------------------------------------------------
    if not EXP_RE.match(row.exp):
        rep.error("unknown_value", f"exp {row.exp!r}: E1–E4가 아님", row)
    elif row.exp != exp:
        rep.error("exp_mismatch", f"exp {row.exp!r}가 파일 {exp}.csv와 다름", row)

    if DIGITS_RE.match(row.set_id):
        n = int(row.set_id)
        if 1 <= n <= design.n_sets:
            row.set_no = n
        else:
            rep.error("set_id", f"set_id {row.set_id!r}: 설계 범위 "
                      f"01–{design.n_sets:02d} 밖", row)
        if not TWO_DIGITS_RE.match(row.set_id):
            rep.warn("set_id_format", f"set_id {row.set_id!r}: 두 자리(01, 02 …)로 적음", row)
    else:
        rep.error("unknown_value", f"set_id {row.set_id!r}: 세트 번호(정수)가 아님", row)

    # --- codes --------------------------------------------------------------
    if exp in FACTORIAL:
        row.cond_ok = row.cond in COND_INDEX
        if not row.cond_ok:
            rep.error("unknown_value", f"cond {row.cond!r}: a·b·c·d 중 하나가 아님", row)
        a_ok = row.a_level in A_LEVELS
        if not a_ok:
            rep.error("unknown_value", f"A_level {row.a_level!r}: A1·A2 중 하나가 아님", row)
        b_ok = row.b_level in B_LEVELS
        if not b_ok:
            rep.error("unknown_value", f"B_level {row.b_level!r}: B1·B2 중 하나가 아님", row)
        if row.role != TARGET_ROLE:
            rep.error("unknown_value", f"role {row.role!r}: E1–E3은 `target`", row)
        if row.cond_ok and a_ok and b_ok:
            want = design.cond_map[row.cond]
            if (row.a_level, row.b_level) != tuple(want):
                rep.error("design_mismatch",
                          f"cond {row.cond}는 설계상 {want[0]}·{want[1]}인데 "
                          f"{row.a_level}·{row.b_level}", row)
        if row.list in LIST_VALUES:
            if row.set_no is not None and row.cond_ok:
                want_list = expected_list(row.set_no, row.cond)
                if int(row.list) != want_list:
                    rep.error("latin_square",
                              f"list={row.list}, 규칙 ((k − s) mod 4) + 1에 따르면 "
                              f"{want_list} (s={row.set_no}, k={COND_INDEX[row.cond]})",
                              row)
        else:
            rep.error("unknown_value", f"list {row.list!r}: 1–4가 아님", row)
    else:  # E4
        row.cond_ok = row.cond in E4_CONDS
        if not row.cond_ok:
            rep.error("unknown_value", f"cond {row.cond!r}: E4는 b1·b2 중 하나", row)
        if row.a_level:
            rep.error("unknown_value", f"A_level {row.a_level!r}: E4는 비움", row)
        if row.b_level not in B_LEVELS:
            rep.error("unknown_value", f"B_level {row.b_level!r}: B1·B2 중 하나가 아님", row)
        elif row.cond_ok and E4_CONDS[row.cond] != row.b_level:
            rep.error("design_mismatch",
                      f"cond {row.cond}와 B_level {row.b_level}가 맞지 않음", row)
        if row.role not in E4_ROLES:
            rep.error("unknown_value", f"role {row.role!r}: E4는 violation·control", row)
        if row.list:
            rep.error("unknown_value", f"list {row.list!r}: E4는 비움", row)

    # --- text fields ----------------------------------------------------------
    if not row.sentence.strip():
        rep.error("empty_sentence", "sentence가 비어 있음", row)
    elif design.length_range and exp in FACTORIAL:
        lo, hi = design.length_range
        if not lo <= len(eojeols(row.sentence)) <= hi:
            agg["length_range"].append(row)
    if not row.context.strip():
        agg["context_empty"].append(row)
    if not row.cr.strip():
        agg["cr_empty"].append(row)
    if not row.norm_status.strip().startswith(NORM_PREFIXES):
        rep.error("norm_status",
                  f"norm_status {shorten(row.norm_status, 30)!r}: "
                  f"{'/'.join(NORM_PREFIXES)} 중 하나로 시작하지 않음", row)
    for value in (row.context, row.sentence, row.cr, row.cq_question,
                  row.cq_options, row.cq_answer):
        if unicodedata.normalize("NFC", value) != value:
            agg["nfc"].append(row)
            break

    check_cq(rep, exp, row, design, agg)


def check_cq(rep: Report, exp: str, row: Row, design: Design,
             agg: dict[str, list[Row]]) -> None:
    question = row.cq_question.strip()
    options_raw = row.cq_options.strip()
    answer = row.cq_answer.strip()

    if exp == "E4":
        if question or options_raw or answer:
            rep.error("cq_e4", "E4는 이해 문항 열(cq_*)을 비움", row)
        return

    wanted = design.cq_template is not None and (
        exp not in CQ_B1_ONLY or row.b_level == "B1")
    if not question:
        if options_raw or answer:
            rep.error("cq_orphan", "cq_question이 비었는데 cq_options/cq_answer가 있음", row)
        if wanted:
            agg["cq_missing"].append(row)
        return
    if not wanted and exp in CQ_B1_ONLY:
        agg["cq_unexpected"].append(row)
    if design.cq_template and question != design.cq_template:
        agg["cq_template"].append(row)

    if not options_raw:
        rep.error("cq_options", "cq_question이 있는데 cq_options가 비어 있음", row)
        return
    options = [o.strip() for o in row.cq_options.split("|")]
    well_formed = True
    if len(options) != N_OPTIONS:
        rep.error("cq_options", f"선택지 {len(options)}개 — `|`로 구분한 {N_OPTIONS}개여야 함",
                  row)
        well_formed = False
    if any(not o for o in options):
        rep.error("cq_options", "빈 선택지가 있음", row)
        well_formed = False
    dups = sorted(o for o, n in Counter(options).items() if o and n > 1)
    if dups:
        rep.error("cq_duplicate", f"선택지 중복: {', '.join(dups)}", row)
        well_formed = False
    if answer not in options:
        rep.error("cq_answer", f"cq_answer {answer!r}가 선택지와 글자 그대로 일치하지 않음 "
                  f"(선택지: {' | '.join(options)})", row)
    elif well_formed:
        row.answer_pos = options.index(answer)


def emit_row_aggregates(rep: Report, exp: str, design: Design,
                        agg: dict[str, list[Row]]) -> None:
    if agg["length_range"]:
        lo, hi = design.length_range
        rows = agg["length_range"]
        rep.warn("length_range",
                 f"설계 item_rules의 {lo}–{hi}어절 밖인 문장 {len(rows)}개: "
                 f"{_labels(rows, lambda r: len(eojeols(r.sentence)))}")
    if agg["context_empty"]:
        rows = agg["context_empty"]
        rep.warn("context_empty", f"context가 빈 행 {len(rows)}개: {_labels(rows)}")
    if agg["cr_empty"]:
        rows = agg["cr_empty"]
        rep.warn("critical_region", f"critical_region이 빈 행 {len(rows)}개: {_labels(rows)}")
    if agg["nfc"]:
        rows = agg["nfc"]
        rep.warn("unicode_nfc", f"NFC 정규형이 아닌 텍스트가 있는 행 {len(rows)}개 "
                 f"(모델 토큰화가 달라짐): {_labels(rows)}")
    if agg["cq_missing"]:
        rows = agg["cq_missing"]
        scope = "B1 행" if exp in CQ_B1_ONLY else "모든 행"
        rep.warn("cq_missing", f"설계상 이해 문항을 묻는 {scope} 중 cq_question이 빈 행 "
                 f"{len(rows)}개: {_labels(rows)}")
    if agg["cq_unexpected"]:
        rows = agg["cq_unexpected"]
        rep.warn("cq_unexpected", f"설계상 B1에서만 묻는데 B2 행에 이해 문항이 있음 "
                 f"{len(rows)}개: {_labels(rows)}")
    if agg["cq_template"]:
        rows = agg["cq_template"]
        rep.warn("cq_template", f"cq_question이 설계 template {design.cq_template!r}와 "
                 f"다른 행 {len(rows)}개: {_labels(rows)}")


# --------------------------------------------------------------------------
# set-level checks
# --------------------------------------------------------------------------

def group_sets(rows: list[Row]) -> dict[int, list[Row]]:
    sets: dict[int, list[Row]] = defaultdict(list)
    for r in rows:
        if r.set_no is not None:
            sets[r.set_no].append(r)
    return dict(sorted(sets.items()))


def check_set_count(rep: Report, sets: dict[int, list[Row]], design: Design) -> None:
    if len(sets) != design.n_sets:
        absent = [f"{n:02d}" for n in range(1, design.n_sets + 1) if n not in sets]
        extra = ""
        if absent:
            shown = ", ".join(absent[:LABEL_LIMIT])
            if len(absent) > LABEL_LIMIT:
                shown += " …"
            extra = f" (없는 세트: {shown})"
        rep.error("set_count", f"세트 수 {len(sets)} ≠ 설계 n_sets {design.n_sets}{extra}")


def check_factorial_sets(rep: Report, exp: str, rows: list[Row], design: Design) -> None:
    sets = group_sets(rows)
    rep.sets = len(sets)
    check_set_count(rep, sets, design)

    for s, members in sets.items():
        sid = f"{s:02d}"
        by_cond: dict[str, list[Row]] = defaultdict(list)
        for r in members:
            if r.cond_ok:
                by_cond[r.cond].append(r)
        missing = [c for c in CONDS if c not in by_cond]
        dups = [c for c in CONDS if len(by_cond.get(c, [])) > 1]
        if missing:
            rep.error("set_conditions", f"조건 {', '.join(missing)} 누락", set_id=sid)
        if dups:
            rep.error("set_conditions", f"조건 {', '.join(dups)}이(가) 두 번 이상", set_id=sid)

        # each list must see this set exactly once
        seen = Counter(int(r.list) for r in members if r.list in LIST_VALUES)
        off = [f"목록 {n}={seen.get(n, 0)}" for n in range(1, N_LISTS + 1)
               if seen.get(n, 0) != 1]
        if off:
            rep.error("latin_coverage",
                      f"각 목록에 이 세트가 정확히 한 번이어야 함: {', '.join(off)}", set_id=sid)

        first = {c: rs[0] for c, rs in by_cond.items()}
        check_minimal_pairs(rep, exp, sid, first)

        lengths = {c: len(eojeols(r.sentence)) for c, r in first.items()
                   if r.sentence.strip()}
        if len(lengths) > 1:
            spread = max(lengths.values()) - min(lengths.values())
            if spread > LENGTH_SPREAD_MAX:
                detail = " ".join(f"{c}={lengths[c]}" for c in CONDS if c in lengths)
                rep.warn("length_spread",
                         f"조건 간 어절 수 차이 {spread} (> {LENGTH_SPREAD_MAX}): {detail}",
                         set_id=sid)

    check_latin_balance(rep, rows, len(sets))
    rep.tables["cond_by_list"] = cond_by_list_table(rows)


def check_minimal_pairs(rep: Report, exp: str, sid: str, first: dict[str, Row]) -> None:
    def have(*conds: str) -> bool:
        return all(c in first and first[c].sentence.strip() for c in conds)

    # A contrast: E1 identical strings, E3 differ only in the final eojeol
    for x, y in (("a", "c"), ("b", "d")):
        if not have(x, y):
            continue
        sx, sy = first[x].sentence, first[y].sentence
        if exp == "E1" and sx != sy:
            rep.error("e1_same_sentence",
                      f"A1·A2 문장이 글자까지 같아야 함 ({x} ≠ {y}): {sx!r} / {sy!r}",
                      set_id=sid, cond=f"{x}/{y}")
        elif exp == "E3" and not only_last_differs(sx, sy):
            rep.error("e3_ending",
                      f"{x}·{y}는 마지막 어절(종결 부분)만 달라야 함: {sx!r} / {sy!r}",
                      set_id=sid, cond=f"{x}/{y}")

    # B contrast: exactly one eojeol differs, and it is the critical region
    reported: set[tuple[str, str]] = set()
    for x, y in (("a", "b"), ("c", "d")):
        if not have(x, y):
            continue
        rx, ry = first[x], first[y]
        if rx.context != ry.context:
            rep.warn("context_pair",
                     f"B1·B2 짝 {x}·{y}의 context가 다름 — B 조작은 -시- 하나만 바꿈",
                     set_id=sid, cond=f"{x}/{y}")
        n, dx, dy = eojeol_diff(rx.sentence, ry.sentence)
        if n != 1:
            key = (rx.sentence, ry.sentence)
            if key not in reported:
                reported.add(key)
                rep.error("eojeol_diff",
                          f"B1·B2 문장의 어절 차이 {n}개 — 정확히 1개여야 함: "
                          f"{rx.sentence!r} / {ry.sentence!r}",
                          set_id=sid, cond=f"{x}/{y}")
            continue
        for r in (rx, ry):
            cr = r.cr.strip()
            if cr and not critical_region_hits(cr, dx + dy):
                msg = (f"critical_region {cr!r}가 B1·B2 사이에 달라지는 어절 "
                       f"({'/'.join(dx) or '∅'} ↔ {'/'.join(dy) or '∅'})과 맞지 않음")
                if exp == "E1":
                    rep.error("critical_region", msg, r)
                else:
                    rep.warn("critical_region", msg, r)


def check_latin_balance(rep: Report, rows: list[Row], n_present: int) -> None:
    # perfectly equal counts are possible only when the set count is a multiple of 4
    tolerance = 0 if n_present % N_LISTS == 0 else 1
    per_list: dict[int, Counter] = {n: Counter() for n in range(1, N_LISTS + 1)}
    for r in rows:
        if r.set_no is not None and r.cond_ok and r.list in LIST_VALUES:
            per_list[int(r.list)][r.cond] += 1
    for n, counts in per_list.items():
        values = [counts.get(c, 0) for c in CONDS]
        if max(values) - min(values) > tolerance:
            detail = " ".join(f"{c}={counts.get(c, 0)}" for c in CONDS)
            rep.error("latin_balance", f"목록 {n}의 조건별 문항 수가 같지 않음: {detail}")


def cond_by_list_table(rows: list[Row]) -> dict:
    table = {c: {**{v: 0 for v in LIST_VALUES}, "total": 0} for c in CONDS}
    for r in rows:
        if r.cond_ok:
            table[r.cond]["total"] += 1
            if r.list in LIST_VALUES:
                table[r.cond][r.list] += 1
    return table


def check_e4_sets(rep: Report, rows: list[Row], design: Design) -> None:
    sets = group_sets(rows)
    rep.sets = len(sets)
    check_set_count(rep, sets, design)

    kinds: Counter = Counter()
    for s, members in sets.items():
        sid = f"{s:02d}"
        by_role: dict[str, list[Row]] = defaultdict(list)
        for r in members:
            if r.role in E4_ROLES:
                by_role[r.role].append(r)
        for role in E4_ROLES:
            if len(by_role[role]) != 1:
                rep.error("set_roles", f"{role} 행 {len(by_role[role])}개 — 세트마다 한 행",
                          set_id=sid)
        conds = sorted({r.cond for r in members if r.cond_ok})
        if len(conds) > 1:
            rep.error("set_cond_mismatch", f"한 세트 안에서 cond가 다름: {', '.join(conds)}",
                      set_id=sid)
        elif conds:
            kinds[conds[0]] += 1

        if by_role["violation"] and by_role["control"]:
            v, c = by_role["violation"][0], by_role["control"][0]
            if not (v.sentence.strip() and c.sentence.strip()):
                continue
            if v.context != c.context:
                rep.warn("context_pair", "violation·control의 context가 다름 — 위반 요소 "
                         "하나만 바꿈", set_id=sid)
            n, dv, dc = eojeol_diff(v.sentence, c.sentence)
            lo, hi = E4_DIFF_RANGE
            if not lo <= n <= hi:
                rep.error("eojeol_diff",
                          f"violation·control 어절 차이 {n}개 — {lo}–{hi}개여야 함: "
                          f"{v.sentence!r} / {c.sentence!r}", set_id=sid)
                continue
            for r in (v, c):
                cr = r.cr.strip()
                if cr and not critical_region_hits(cr, dv + dc):
                    rep.warn("critical_region",
                             f"critical_region {cr!r}가 violation·control 사이에 달라지는 "
                             f"어절({'/'.join(dv) or '∅'} ↔ {'/'.join(dc) or '∅'})과 맞지 않음",
                             r)

    if kinds["b1"] != kinds["b2"]:
        rep.error("e4_balance", f"B1 세트 {kinds['b1']}개 ≠ B2 세트 {kinds['b2']}개")

    table = {c: {role: 0 for role in E4_ROLES} for c in E4_CONDS}
    for r in rows:
        if r.cond_ok and r.role in E4_ROLES:
            table[r.cond][r.role] += 1
    rep.tables["cond_by_role"] = table


# --------------------------------------------------------------------------
# file-level checks
# --------------------------------------------------------------------------

def sentence_index(exp: str, records: list[tuple[int, dict]]) -> dict[str, list[str]]:
    """{normalised sentence: [row ids]} for the cross-experiment duplicate check."""
    index: dict[str, list[str]] = defaultdict(list)
    for line, rec in records:
        row = Row(exp, line, rec)
        if row.sentence.strip():
            index[norm_text(row.sentence)].append(row.short)
    return dict(index)


def check_duplicates(rep: Report, exp: str, rows: list[Row],
                     others: dict[str, dict[str, list[str]]]) -> None:
    pairs: dict[tuple[str, str], list[Row]] = defaultdict(list)
    sentences: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        if not r.sentence.strip():
            continue
        key = norm_text(r.sentence)
        pairs[(norm_text(r.context), key)].append(r)
        sentences[key].append(r)

    for (_, sentence), rs in pairs.items():
        if len(rs) > 1:
            rep.error("duplicate_pair",
                      f"같은 (context, sentence) 쌍이 {len(rs)}번: {_labels(rs)} — {sentence!r}")

    for sentence, rs in sentences.items():
        set_ids = {r.set_id for r in rs}
        contexts = {norm_text(r.context) for r in rs}
        if len(set_ids) > 1 and len(contexts) > 1:
            rep.warn("duplicate_sentence",
                     f"같은 sentence가 여러 세트에 나옴 ({_labels(rs)}): {sentence!r}")
        hits = []
        for other, index in sorted(others.items()):
            if other != exp and sentence in index:
                locs = index[sentence]
                hits.append(f"{other} {', '.join(locs[:LABEL_LIMIT])}")
        if hits:
            rep.error("cross_duplicate",
                      f"다른 실험에 같은 sentence가 있음: {sentence!r} — "
                      f"{exp} {_labels(rs)} / {'; '.join(hits)}")


def check_stems(rep: Report, rows: list[Row]) -> None:
    sets_by_stem: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        stem = predicate_stem(r.sentence)
        if stem:
            sets_by_stem[stem].add(r.set_id or "?")
    for stem, sids in sorted(sets_by_stem.items()):
        if len(sids) >= STEM_REPEAT_MIN:
            rep.warn("predicate_repeat",
                     f"서술어 어간 {stem!r}(마지막 어절 첫 {STEM_CHARS}글자, 근사)이 "
                     f"{len(sids)}개 세트에 쓰임: {', '.join(sorted(sids))}")


def check_review_notes(rep: Report, rows: list[Row]) -> None:
    by_set: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        if r.note.lstrip().startswith(REVIEW_PREFIX):
            by_set[r.set_id or "?"].append(r)
    for sid in sorted(by_set):
        rs = by_set[sid]
        reason = rs[0].note.strip()[len(REVIEW_PREFIX):].strip()
        tags = ", ".join(r.tag for r in rs)
        rep.warn("review_needed", f"검토 필요 ({tags}): {shorten(reason)}", set_id=sid)
        rep.review_sets.append({
            "set": sid,
            "conds": [r.tag for r in rs],
            "notes": [r.note.strip() for r in rs],
        })


def check_answer_positions(rep: Report, rows: list[Row]) -> None:
    positions = [r.answer_pos for r in rows if r.answer_pos is not None]
    dist = {str(i + 1): 0 for i in range(N_OPTIONS)}
    for p in positions:
        dist[str(p + 1)] += 1
    rep.tables["cq_answer_position"] = dist
    if len(positions) >= SKEW_MIN_ITEMS:
        top = max(dist.values())
        if top / len(positions) > SKEW_MAX_SHARE:
            detail = " ".join(f"{POS_MARKS[i]}={dist[str(i + 1)]}" for i in range(N_OPTIONS))
            rep.warn("cq_position_skew",
                     f"이해 문항 정답 위치가 한쪽에 쏠림: {detail} (n={len(positions)}) — "
                     f"실행 단계에서 선택지 순서를 무선화")


def validate_file(exp: str, loaded: tuple, design: Design,
                  others: dict[str, dict[str, list[str]]], shown_path: str) -> Report:
    header, records, has_bom = loaded
    rep = Report(exp, shown_path, design.n_sets)

    if has_bom:
        rep.warn("bom", "UTF-8 BOM이 있음 — 규격은 BOM 없음")
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        rep.error("columns", f"필수 열 누락: {', '.join(missing)} — 나머지 검사 생략")
        return rep
    extra = [h for h in header if h not in REQUIRED_COLUMNS]
    if extra:
        rep.warn("columns", f"규격에 없는 열: {', '.join(extra)}")

    rows = [Row(exp, line, rec) for line, rec in records]
    rep.rows = len(rows)
    agg: dict[str, list[Row]] = defaultdict(list)
    for row, (_, rec) in zip(rows, records):
        check_row(rep, exp, row, rec, design, agg)
    emit_row_aggregates(rep, exp, design, agg)

    if exp in FACTORIAL:
        check_factorial_sets(rep, exp, rows, design)
    else:
        check_e4_sets(rep, rows, design)

    check_duplicates(rep, exp, rows, others)
    check_stems(rep, rows)
    check_review_notes(rep, rows)
    if exp in FACTORIAL:
        check_answer_positions(rep, rows)
    return rep


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def validate(root: Path, ids: list[str] | None = None) -> dict:
    root = Path(root)
    stim_dir = root / "content" / "stimuli"
    present = {p.stem: p for p in sorted(stim_dir.glob("E?.csv")) if EXP_RE.match(p.stem)}
    input_errors: list[str] = []
    missing: list[str] = []

    if ids:
        wanted = list(dict.fromkeys(ids))
        for exp in wanted:
            if exp not in present:
                missing.append(exp)
                input_errors.append(f"{exp}: content/stimuli/{exp}.csv 없음")
        targets = [e for e in wanted if e in present]
    else:
        targets = sorted(present)
        if not targets:
            input_errors.append("content/stimuli/에 E1–E4 CSV가 없음")

    # every present CSV is read once: targets are validated, the rest feed the
    # cross-experiment duplicate check
    loaded: dict[str, tuple] = {}
    unreadable: dict[str, str] = {}
    for exp, path in present.items():
        try:
            loaded[exp] = read_csv(path)
        except InputError as exc:
            unreadable[exp] = str(exc)
    for exp in targets:
        if exp in unreadable:
            input_errors.append(unreadable[exp])
    others = {exp: sentence_index(exp, recs) for exp, (_, recs, _) in loaded.items()}

    reports: list[Report] = []
    for exp in targets:
        if exp not in loaded:
            continue
        try:
            design = load_design(root, exp)
        except InputError as exc:
            input_errors.append(str(exc))
            continue
        path = present[exp]
        try:
            shown = str(path.relative_to(root))
        except ValueError:
            shown = str(path)
        reports.append(validate_file(exp, loaded[exp], design, others, shown))

    files = [r.as_dict() for r in reports]
    errors = sum(f["error_count"] for f in files)
    warnings = sum(f["warning_count"] for f in files)
    exit_code = 2 if input_errors else (1 if errors else 0)
    return {
        "root": str(root),
        "files": files,
        "missing": missing,
        "input_errors": input_errors,
        "cross_checked": sorted(loaded),
        "cross_check_skipped": sorted(e for e in unreadable if e not in targets),
        "totals": {
            "files": len(files),
            "errors": errors,
            "warnings": warnings,
            "input_errors": len(input_errors),
        },
        "ok": exit_code == 0,
        "exit_code": exit_code,
    }


def format_issue(issue: dict) -> str:
    where = " ".join(p for p in (
        f"세트 {issue['set']}" if issue.get("set") else "",
        str(issue["cond"]) if issue.get("cond") else "",
    ) if p)
    if issue.get("line"):
        where = f"{where} (line {issue['line']})" if where else f"line {issue['line']}"
    head = f"[{issue['check']}]"
    return f"{head} {where}: {issue['msg']}" if where else f"{head} {issue['msg']}"


def print_tables(f: dict) -> None:
    tables = f["tables"]
    if "cond_by_list" in tables:
        t = tables["cond_by_list"]
        print("       조건 × 목록 문항 수")
        print("         cond " + "".join(f"{'L' + v:>6}" for v in LIST_VALUES) + f"{'계':>6}")
        for c in CONDS:
            row = t[c]
            print(f"         {c:<4} " + "".join(f"{row[v]:>6}" for v in LIST_VALUES)
                  + f"{row['total']:>7}")
        col = [sum(t[c][v] for c in CONDS) for v in LIST_VALUES]
        print("         계   " + "".join(f"{n:>6}" for n in col)
              + f"{sum(t[c]['total'] for c in CONDS):>7}")
    if "cond_by_role" in tables:
        t = tables["cond_by_role"]
        print("       조건 × 역할 문항 수")
        print("         cond " + "".join(f"{role:>11}" for role in E4_ROLES))
        for c in E4_CONDS:
            print(f"         {c:<4} " + "".join(f"{t[c][role]:>11}" for role in E4_ROLES))
    if "cq_answer_position" in tables:
        d = tables["cq_answer_position"]
        detail = " ".join(f"{POS_MARKS[i]}={d[str(i + 1)]}" for i in range(N_OPTIONS))
        print(f"       이해 문항 정답 위치: {detail}")


def print_human(result: dict) -> None:
    for msg in result["input_errors"]:
        print(f"INPUT  {msg}")
    for f in result["files"]:
        status = "OK  " if f["error_count"] == 0 else "FAIL"
        print(f"{status} {f['id']}  rows={f['rows']} sets={f['sets']}/{f['n_sets']}  "
              f"errors={f['error_count']} warnings={f['warning_count']}")
        for issue in f["errors"]:
            print(f"       ERROR    {format_issue(issue)}")
        for issue in f["warnings"]:
            print(f"       WARNING  {format_issue(issue)}")
        print_tables(f)
    if result["cross_check_skipped"]:
        print(f"note: 실험 간 중복 검사에서 읽지 못해 뺀 파일: "
              f"{', '.join(result['cross_check_skipped'])}")
    t = result["totals"]
    print("-" * 60)
    line = f"{t['files']} file(s): {t['errors']} error(s), {t['warnings']} warning(s)"
    if t["input_errors"]:
        line += f", {t['input_errors']} input problem(s)"
    print(line)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="experiment ids, e.g. E1 E3 (default: all)")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="dump the full result as JSON to stdout")
    args = ap.parse_args(argv)

    ids = []
    for raw in args.ids:
        exp = Path(raw).stem.upper()
        if not EXP_RE.match(exp):
            print(f"ERROR: {raw!r} is not an experiment id like E1", file=sys.stderr)
            return 2
        ids.append(exp)

    result = validate(Path(args.root), ids or None)

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
