#!/usr/bin/env python3
"""Build the single-file research dashboard `dashboard/index.html`.

Everything shown on the dashboard comes from `content/` and `인수인계서.md`
(docs/03_산출물-설계.md §1).  This script only

  1. loads those files (a missing stimulus CSV is skipped, never fatal),
  2. checks cross references and collects warnings (it never edits the data),
  3. writes the page shell -- header, the 10 tab buttons, every tab panel with
     its section skeleton (ids from docs/03_산출물-설계.md §2.3) --
  4. embeds the data as `<script type="application/json" id="data-...">`
     blocks and inlines the CSS/JS from `build/dashboard_template/`.

Rendering of the section bodies is done by the inlined vanilla JS.  No
external resource (CDN, web font, remote script/stylesheet) is referenced.

Standard library only (Python 3.13).

Usage:
    python3 build/build_dashboard.py                 # -> dashboard/index.html
    python3 build/build_dashboard.py --out /tmp/x.html
    python3 build/build_dashboard.py --root <repo>   # other checkout (tests)
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parent
TEMPLATE_DIR = HERE / "dashboard_template"

HANDOFF_NAME = "인수인계서.md"

# --------------------------------------------------------------------------
# page structure (docs/03_산출물-설계.md §2.2, §2.3) -- UI labels, not content
# --------------------------------------------------------------------------

TABS: list[dict] = [
    {
        "id": "home", "label": "홈", "en": "HOME",
        "question": "이 연구를 한눈에",
        "sections": [
            ("home-question", "연구 질문과 대표 주장",
             "무엇을 가르려는 연구인가 — 두 가설과 조건문으로 적은 대표 주장"),
            ("home-numbers", "핵심 숫자", "산출물 규모를 한 줄로"),
            ("home-matrix", "6하원칙 × 5영역 매트릭스",
             "칸을 누르면 해당 탭의 해당 섹션으로 이동한다"),
            ("home-axis", "허가자 거리 축",
             "세 핵심 실험을 하나의 축 위에 놓는 연구의 뼈대"),
            ("home-guide", "탭 안내", "각 탭이 답하는 질문"),
        ],
    },
    {
        "id": "why", "label": "왜", "en": "WHY",
        "question": "왜 이 연구가 필요한가, 무엇을 알게 되는가",
        "sections": [
            ("why-problem", "문제의식",
             "선행 연구 10편이 보여 준 것과 보여 주지 못한 것"),
            ("why-agreements", "합의", "여러 논문이 같은 방향을 가리키는 사실"),
            ("why-conflicts", "충돌", "논문끼리 입장이나 결과가 갈리는 지점"),
            ("why-gaps", "공백",
             "아직 검증되지 않은 곳 — 우선순위와 근거 계승 지점(칩을 누르면 논문 서가로)"),
            ("why-implications", "국어학적 함의",
             "결과를 보기 전에 적어 둔 조건문 — 인간 결과별·모델 결과별"),
            ("why-corrections", "기존 초안에서 바로잡은 사실",
             "원문 확인으로 뒤집힌 전제(인수인계서 §5.1)"),
        ],
    },
    {
        "id": "what", "label": "무엇을", "en": "WHAT",
        "question": "무엇을 검정하는가",
        "sections": [
            ("what-hypotheses", "공통 가설",
             "표면 공기 대 허가 조건 — 그리고 왜 2×2가 필요한가"),
            ("what-experiments", "실험 E1–E4",
             "요인·수준, 2×2 조건 표, 예측 표, 핵심 상호작용 대비"),
            ("what-candidates", "후보 8개와 채점",
             "어떤 후보가 왜 선정·탈락했는가"),
            ("what-stimuli", "자극 브라우저",
             "실험·조건·세트로 걸러 맥락 단락과 목표 문장을 본다"),
        ],
    },
    {
        "id": "who", "label": "누가", "en": "WHO",
        "question": "누구를(어떤 모델·사람을) 실험하는가",
        "sections": [
            ("who-models", "모델 라인업", "핵심 6개와 선택 2개의 호출 설정·비용"),
            ("who-rationale", "선정 이유와 설계 제약",
             "왜 이 모델들인가, 모델 특성이 설계에 준 제약"),
            ("who-excluded", "제외한 모델", "검토했지만 뺀 모델과 이유"),
            ("who-humans", "인간 참여자", "모집 대상·인원·세션·제외 기준"),
            ("who-prior", "선행 연구는 누구를 실험했나",
             "논문별 6하원칙 카드의 ‘누가’"),
        ],
    },
    {
        "id": "when", "label": "언제", "en": "WHEN",
        "question": "언제, 어떤 순서로 하는가",
        "sections": [
            ("when-roadmap", "로드맵", "착수 후 주차(W) 기준 단계 R1–R9"),
            ("when-order", "실행 순서", "E4를 먼저 — 판정어 확정 뒤 사전등록과 본실험"),
            ("when-versioning", "모델 버전 고정",
             "상용 모델은 바뀐다 — 스냅샷과 실행 시점 규칙"),
            ("when-prior", "선행 연구 연표",
             "발표 연도와 실험한 모델의 세대(논문별 ‘언제’)"),
        ],
    },
    {
        "id": "where", "label": "어디서", "en": "WHERE",
        "question": "어디서(어떤 환경·경로로) 하는가",
        "sections": [
            ("where-api", "API 실험 환경", "제공사별 모델 ID·공식 문서·호출 조건"),
            ("where-platform", "인간 실험 플랫폼과 IRB", "참여자 실험을 어디서 어떻게"),
            ("where-prereg", "사전등록", "OSF에 무엇을 언제 등록하는가"),
            ("where-publication", "투고 계획", "논문 1–3과 후보 학술지"),
            ("where-materials", "선행 연구 공개 자료",
             "논문별 공개 자극·코드·데이터 위치"),
        ],
    },
    {
        "id": "how", "label": "어떻게", "en": "HOW",
        "question": "어떻게 측정하고 분석하는가",
        "sections": [
            ("how-measures", "척도와 문구", "수용성·공손성·이해 문항"),
            ("how-prompt", "모델 호출 규칙과 프롬프트", "템플릿 전문과 출력 형식·표집"),
            ("how-controls", "통제", "라틴 방격·단독 제시·순서 무선화·채움 문장"),
            ("how-analysis", "분석 모형과 정렬 지표",
             "누적 링크 혼합 모형·3원 상호작용·TOST"),
            ("how-failure", "실패 처리와 로그 필드", "재시도·거부·제외 규칙"),
        ],
    },
    {
        "id": "papers", "label": "논문 서가", "en": "PAPERS",
        "question": "선행 논문 10편을 같은 틀로",
        "sections": [],
    },
    {
        "id": "track", "label": "진행 추적", "en": "TRACK",
        "question": "어디까지 됐는가",
        "sections": [
            ("track-ledger", "작업 대장", "인수인계서 §4"),
            ("track-decisions", "의사결정 기록", "인수인계서 §6"),
            ("track-verification", "검증·정정 기록", "인수인계서 §7"),
        ],
    },
    {
        "id": "refs", "label": "참고문헌", "en": "REFS",
        "question": "근거",
        "sections": [],
    },
]

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"

# Every section id docs/03_산출물-설계.md §2.3 requires (paper-/hook-/ref-
# anchors are generated from data and checked separately).
SPEC_SECTION_IDS = [
    sid for tab in TABS if tab["id"] not in ("home",)
    for sid, _title, _lead in tab["sections"]
]


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

class Build:
    """Collects loaded data and warnings for one build."""

    def __init__(self, root: Path):
        self.root = root
        self.content = root / "content"
        self.warnings: list[str] = []

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    def load_json(self, path: Path, default=None):
        if not path.exists():
            self.warn(f"파일 없음: {self.rel(path)}")
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self.warn(f"JSON 읽기 실패: {self.rel(path)} — {exc}")
            return default


def load_papers(b: Build) -> list[dict]:
    papers = []
    for path in sorted((b.content / "papers").glob("P*.json")):
        card = b.load_json(path)
        if isinstance(card, dict) and card.get("id"):
            papers.append(card)
    return papers


def load_experiments(b: Build) -> list[dict]:
    exps = []
    for path in sorted((b.content / "experiments").glob("E*.json")):
        e = b.load_json(path)
        if isinstance(e, dict) and e.get("id"):
            exps.append(e)
    return exps


def load_stimuli(b: Build, experiments: list[dict]) -> tuple[dict, list[str]]:
    """Every CSV under content/stimuli.  Returns ({name: block}, missing)."""
    out: dict[str, dict] = {}
    folder = b.content / "stimuli"
    for path in sorted(folder.glob("*.csv")) if folder.exists() else []:
        name = path.stem
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            b.warn(f"CSV 인코딩 오류(건너뜀): {b.rel(path)} — {exc}")
            continue
        try:
            rows = list(csv.DictReader(text.splitlines()))
        except csv.Error as exc:
            b.warn(f"CSV 읽기 실패(건너뜀): {b.rel(path)} — {exc}")
            continue
        clean = []
        for r in rows:
            clean.append({(k or "").strip(): (v or "").strip()
                          for k, v in r.items() if k is not None})
        out[name] = {
            "name": name,
            "file": b.rel(path),
            "label": "채움 문장" if name.lower().startswith("filler") else name,
            "columns": list(clean[0].keys()) if clean else [],
            "rows": clean,
        }
    expected = [e["id"] for e in experiments] + ["fillers"]
    missing = [n for n in expected if n not in out]
    return out, missing


# --------------------------------------------------------------------------
# 인수인계서.md -- markdown tables
# --------------------------------------------------------------------------

_HEADING = re.compile(r"^(#{2,3})\s+(.*?)\s*$")


def split_row(line: str) -> list[str]:
    """Split a markdown table row on unescaped pipes outside code spans."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, cur, in_code, i = [], [], False, 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            cur.append("|")
            i += 2
            continue
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    cells.append("".join(cur).strip())
    return cells


def parse_markdown(md: str) -> list[dict]:
    """Return sections [{level, title, number, lines, tables, bullets}]."""
    sections: list[dict] = []
    cur = {"level": 1, "title": "", "number": "", "lines": []}
    sections.append(cur)
    in_fence = False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            cur["lines"].append(line)
            continue
        m = None if in_fence else _HEADING.match(line)
        if m:
            title = m.group(2)
            num = re.match(r"^(\d+(?:\.\d+)*)\.?\s", title)
            cur = {"level": len(m.group(1)), "title": title,
                   "number": num.group(1) if num else "", "lines": []}
            sections.append(cur)
        else:
            cur["lines"].append(line)
    for sec in sections:
        sec["tables"] = _tables(sec["lines"])
        sec["bullets"] = [ln.strip()[2:].strip() for ln in sec["lines"]
                          if ln.strip().startswith("- ")]
        sec["text"] = "\n".join(sec["lines"]).strip()
        del sec["lines"]
    return sections


def _tables(lines: list[str]) -> list[dict]:
    tables, block = [], []
    for ln in lines + [""]:
        if ln.strip().startswith("|"):
            block.append(ln)
            continue
        if len(block) >= 2 and re.match(r"^\|?\s*:?-{3,}", block[1].strip()):
            header = split_row(block[0])
            rows = []
            for raw in block[2:]:
                cells = split_row(raw)
                if len(cells) < len(header):
                    cells += [""] * (len(header) - len(cells))
                rows.append(cells[: len(header)] if len(cells) > len(header)
                            and all(c == "" for c in cells[len(header):])
                            else cells)
            tables.append({"headers": header, "rows": rows})
        block = []
    return tables


def load_tracker(b: Build) -> dict:
    path = b.root / HANDOFF_NAME
    if not path.exists():
        b.warn(f"파일 없음: {HANDOFF_NAME}")
        return {}
    sections = parse_markdown(path.read_text(encoding="utf-8"))

    def find(number: str) -> dict | None:
        for s in sections:
            if s["number"] == number:
                return s
        return None

    def first_table(number: str, label: str) -> dict:
        s = find(number)
        if not s or not s["tables"]:
            b.warn(f"{HANDOFF_NAME} §{number}({label}) 표를 찾지 못함")
            return {"headers": [], "rows": []}
        return s["tables"][0]

    ledger = first_table("4", "작업 대장")
    counts: dict[str, int] = {}
    if ledger["headers"]:
        try:
            si = ledger["headers"].index("상태")
        except ValueError:
            si = -1
            b.warn(f"{HANDOFF_NAME} §4 표에 '상태' 열이 없음")
        for row in ledger["rows"]:
            if 0 <= si < len(row):
                icon = row[si].strip()[:1]
                counts[icon] = counts.get(icon, 0) + 1
            if len(row) != len(ledger["headers"]):
                b.warn(f"{HANDOFF_NAME} §4 행의 칸 수 불일치: {row[:1]}")

    status = find("2")
    legend = ""
    s4 = find("4")
    if s4:
        m = re.search(r"상태:\s*(.+)", s4["text"])
        legend = m.group(1).strip() if m else ""
    return {
        "source": HANDOFF_NAME,
        "status_title": status["title"] if status else "",
        "status_bullets": status["bullets"] if status else [],
        "project_w5h1": first_table("1", "프로젝트 6하원칙"),
        "ledger": ledger,
        "ledger_counts": counts,
        "ledger_legend": legend,
        "decisions": first_table("6", "의사결정 기록"),
        "verification": first_table("7", "검증·정정 기록"),
        "corrections": first_table("5.1", "기존 초안 정정"),
        "risks": first_table("8", "미해결·위험"),
    }


# --------------------------------------------------------------------------
# checks (report only -- data is never modified)
# --------------------------------------------------------------------------

W5H1 = ("who", "when", "where", "what", "how", "why")
LAYERS = ("word", "sentence", "paragraph", "context")
PAPER_KEYS = ("id", "role", "short", "title", "citation", "one_line", "w5h1",
              "layers", "design", "key_numbers", "limitations",
              "successor_hooks", "open_materials", "prior_analysis_check",
              "verification")


def check_all(b: Build, data: dict) -> None:
    papers = data["papers"]
    hook_ids = set()
    for p in papers:
        pid = p.get("id", "?")
        for k in PAPER_KEYS:
            if k not in p:
                b.warn(f"{pid}: 최상위 키 누락 '{k}'")
        w = p.get("w5h1") or {}
        for k in W5H1:
            cell = w.get(k)
            if not isinstance(cell, dict) or not cell.get("headline"):
                b.warn(f"{pid}: w5h1.{k} headline 없음")
        lay = p.get("layers") or {}
        for k in LAYERS:
            if not lay.get(k):
                b.warn(f"{pid}: layers.{k} 비어 있음")
        for h in p.get("successor_hooks") or []:
            hid = h.get("id", "")
            if not re.fullmatch(rf"{pid}-H\d+", hid):
                b.warn(f"{pid}: 계승 지점 id 형식 이상 '{hid}'")
            hook_ids.add(hid)
        ver = p.get("verification") or {}
        if ver.get("status") == "draft":
            b.warn(f"{pid}: 독립 검증 전(verification.status = draft)")

    syn = data.get("synthesis") or {}
    for g in syn.get("gaps", []):
        for h in g.get("basis_hooks", []):
            if h not in hook_ids:
                b.warn(f"synthesis {g.get('id')}: 없는 계승 지점 {h}")
    for e in data["experiments"]:
        hs = list((e.get("inherits") or {}).get("hooks", []))
        hs += list((e.get("extension_model_only") or {}).get("inherits", []))
        for h in hs:
            if h not in hook_ids:
                b.warn(f"{e.get('id')}: 없는 계승 지점 {h}")

    valid_ids = set(SPEC_SECTION_IDS) | {t["id"] for t in TABS}
    matrix = data.get("matrix") or {}
    cells = matrix.get("cells", [])
    if len(cells) != 30:
        b.warn(f"dashboard_matrix: 칸 수 {len(cells)} (설계 30)")
    for c in cells:
        if c.get("anchor") not in valid_ids:
            b.warn(f"dashboard_matrix: 없는 섹션 id '{c.get('anchor')}'"
                   f" ({c.get('row')}×{c.get('col')})")
        if c.get("tab") not in {t["id"] for t in TABS}:
            b.warn(f"dashboard_matrix: 없는 탭 '{c.get('tab')}'")

    for r in (data.get("references") or {}).get("references", []):
        n = r.get("n")
        if r.get("doi") and not str(r.get("url") or "").startswith("https://doi.org/"):
            b.warn(f"참고문헌 [{n}]: DOI가 있으나 url이 https://doi.org/로 시작하지 않음")
        if not r.get("url"):
            b.warn(f"참고문헌 [{n}] {r.get('key')}: url 없음")

    exp_by_id = {e["id"]: e for e in data["experiments"]}
    for name, block in data["stimuli"].items():
        rows = block["rows"]
        e = exp_by_id.get(name)
        if e and e.get("n_sets"):
            per = 2 if name == "E4" else 4
            want = e["n_sets"] * per
            if len(rows) != want:
                b.warn(f"자극 {name}: 행 {len(rows)}개 (설계 n_sets×{per} = {want})")
        for r in rows:
            crit, sent = r.get("critical_region", ""), r.get("sentence", "")
            # a region may be non-contiguous ("동창을 나를"): every token must occur
            if crit and sent and crit not in sent and \
                    not all(tok in sent for tok in crit.split()):
                b.warn(f"자극 {name} 세트 {r.get('set_id')} {r.get('cond')}: "
                       f"조작 어절 '{crit}'이 문장에 없음")
            if r.get("cq_answer") and r.get("cq_options"):
                if r["cq_answer"] not in r["cq_options"].split("|"):
                    b.warn(f"자극 {name} 세트 {r.get('set_id')} {r.get('cond')}: "
                           f"정답이 선택지에 없음")
    for name in data["stimuli_missing"]:
        b.warn(f"자극 파일 없음(작성 중일 수 있음): content/stimuli/{name}.csv")


# --------------------------------------------------------------------------
# assembling
# --------------------------------------------------------------------------

def collect(root: Path) -> tuple[dict, Build]:
    b = Build(root)
    c = b.content
    papers = load_papers(b)
    experiments = load_experiments(b)
    stimuli, missing = load_stimuli(b, experiments)
    refs = b.load_json(c / "references.json", {"references": []}) or {"references": []}
    for r in refs.get("references", []):
        r["anchor"] = f"ref-{r.get('n')}"
    data = {
        "papers": papers,
        "synthesis": b.load_json(c / "synthesis.json", {}),
        "candidates": b.load_json(c / "experiments" / "_candidates.json", {}),
        "experiments": experiments,
        "stimuli": stimuli,
        "stimuli_missing": missing,
        "evaluation": b.load_json(c / "evaluation.json", {}),
        "models": b.load_json(c / "models.json", {}),
        "implications": b.load_json(c / "implications.json", {}),
        "roadmap": b.load_json(c / "roadmap.json", {}),
        "references": refs,
        "matrix": b.load_json(c / "dashboard_matrix.json", {}),
        "tracker": load_tracker(b),
    }
    check_all(b, data)
    return data, b


def json_block(name: str, obj) -> str:
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    # keep the HTML parser out of the JSON: no "</script", no comments
    text = (text.replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026"))
    return f'<script type="application/json" id="data-{name}">{text}</script>'


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def section_counts(data: dict) -> dict[str, str]:
    syn = data.get("synthesis") or {}
    cand = data.get("candidates") or {}
    models = (data.get("models") or {}).get("models", [])
    imp = (data.get("implications") or {}).get("implications", [])
    phases = (data.get("roadmap") or {}).get("phases", [])
    n_stim = sum(len(v["rows"]) for v in data["stimuli"].values())
    tr = data.get("tracker") or {}

    def rng(items, key="id"):
        ids = [x.get(key, "") for x in items]
        return f"{ids[0]}–{ids[-1]}" if len(ids) > 1 else (ids[0] if ids else "0")

    return {
        "why-agreements": rng(syn.get("agreements", [])),
        "why-conflicts": rng(syn.get("conflicts", [])),
        "why-gaps": rng(syn.get("gaps", [])),
        "why-implications": rng(imp),
        "why-corrections": f"{len((tr.get('corrections') or {}).get('rows', []))}건",
        "what-experiments": f"{len(data['experiments'])}개",
        "what-candidates": f"{len(cand.get('candidates', []))}개",
        "what-stimuli": f"{n_stim}행",
        "who-models": f"{len(models)}개",
        "who-excluded": f"{len((data.get('models') or {}).get('excluded', []))}개",
        "who-prior": f"{len(data['papers'])}편",
        "when-roadmap": rng(phases),
        "when-prior": f"{len(data['papers'])}편",
        "where-publication": f"{len((data.get('implications') or {}).get('publication_plan', []))}편",
        "where-materials": f"{len(data['papers'])}편",
        "track-ledger": f"{len((tr.get('ledger') or {}).get('rows', []))}건",
        "track-decisions": f"{len((tr.get('decisions') or {}).get('rows', []))}건",
        "track-verification": f"{len((tr.get('verification') or {}).get('rows', []))}건",
    }


def render_tabs() -> str:
    out = []
    for i, t in enumerate(TABS):
        en = f'<span class="tab-en">{esc(t["en"])}</span>' if t["en"] and t["id"] not in ("papers", "track", "refs", "home") else ""
        out.append(
            f'<button type="button" role="tab" class="tab{" sep" if t["id"] in ("why", "papers") else ""}" id="tab-{t["id"]}" '
            f'data-tab="{t["id"]}" aria-controls="panel-{t["id"]}" '
            f'aria-selected="{"true" if i == 0 else "false"}" '
            f'tabindex="{0 if i == 0 else -1}">'
            f'<span class="tab-ko">{esc(t["label"])}</span>{en}</button>')
    return "\n".join(out)


def render_panels(data: dict) -> str:
    counts = section_counts(data)
    out = []
    for t in TABS:
        tid = t["id"]
        head = (f'<header class="panel-head"><p class="panel-kicker">'
                f'{esc(t["label"])}{(" · " + esc(t["en"])) if t["en"] else ""}</p>'
                f'<h1 class="panel-title">{esc(t["question"])}</h1>'
                f'<div class="panel-intro" data-intro="{tid}"></div></header>')
        secs = []
        for i, (sid, title, lead) in enumerate(t["sections"]):
            num = CIRCLED[i] if i < len(CIRCLED) else str(i + 1)
            cnt = counts.get(sid)
            pill = f' <span class="sec-count">{esc(cnt)}</span>' if cnt else ""
            secs.append(
                f'<section class="sec" id="{sid}" aria-labelledby="{sid}-h">'
                f'<header class="sec-head"><h2 id="{sid}-h"><span class="sec-num">{num}</span>'
                f'<span class="sec-title">{esc(title)}</span>{pill}</h2>'
                f'<p class="sec-lead">{esc(lead)}</p></header>'
                f'<div class="sec-body" data-render="{sid}"><p class="loading">불러오는 중…</p></div>'
                f'</section>')
        toc = ""
        if len(t["sections"]) > 2 and tid != "home":
            items = "".join(
                f'<li><a href="#{sid}" data-toc="{sid}"><span class="toc-num">'
                f'{CIRCLED[i]}</span>{esc(title)}</a></li>'
                for i, (sid, title, _l) in enumerate(t["sections"]))
            toc = (f'<nav class="toc" aria-label="{esc(t["label"])} 탭 섹션">'
                   f'<p class="toc-label">이 탭의 섹션</p><ol>{items}</ol></nav>')
        if tid == "papers":
            body = ('<div class="shelf">'
                    '<nav class="shelf-list" aria-label="논문 목록" data-render="shelf-list"></nav>'
                    '<div class="shelf-detail">'
                    + "".join(
                        f'<article class="paper" id="paper-{esc(p["id"])}" '
                        f'data-paper="{esc(p["id"])}" hidden></article>'
                        for p in data["papers"])
                    + '</div></div>')
        elif tid == "refs":
            body = '<div class="sec-body" data-render="refs-list"></div>'
        else:
            body = "".join(secs)
        layout_cls = "panel-layout has-toc" if toc else "panel-layout"
        out.append(
            f'<section class="tab-panel" id="panel-{tid}" data-tab="{tid}" '
            f'role="tabpanel" aria-labelledby="tab-{tid}"{"" if tid == "home" else " hidden"}>'
            f'{head}<div class="{layout_cls}">{toc}<div class="panel-main">{body}</div></div>'
            f'</section>')
    return "\n".join(out)


def build(root: Path = DEFAULT_ROOT, out: Path | None = None) -> dict:
    """Build the dashboard.  Returns a summary dict (path, bytes, warnings)."""
    root = Path(root)
    out = Path(out) if out else root / "dashboard" / "index.html"
    data, b = collect(root)

    stim_rows = {k: len(v["rows"]) for k, v in data["stimuli"].items()}
    meta = {
        "built_at": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tabs": [{"id": t["id"], "label": t["label"], "en": t["en"],
                  "question": t["question"],
                  "sections": [{"id": s, "title": ti} for s, ti, _l in t["sections"]]}
                 for t in TABS],
        "stimuli_rows": stim_rows,
        "stimuli_missing": data["stimuli_missing"],
        "warnings": b.warnings,
    }
    blocks = {
        "meta": meta,
        "papers": data["papers"],
        "synthesis": data["synthesis"],
        "candidates": data["candidates"],
        "experiments": data["experiments"],
        "stimuli": data["stimuli"],
        "evaluation": data["evaluation"],
        "models": data["models"],
        "implications": data["implications"],
        "roadmap": data["roadmap"],
        "references": data["references"],
        "matrix": data["matrix"],
        "tracker": data["tracker"],
    }
    shell = (TEMPLATE_DIR / "shell.html").read_text(encoding="utf-8")
    css = (TEMPLATE_DIR / "style.css").read_text(encoding="utf-8")
    js = (TEMPLATE_DIR / "app.js").read_text(encoding="utf-8")
    head_js = (TEMPLATE_DIR / "theme-init.js").read_text(encoding="utf-8")
    for label, src in (("style.css", css), ("app.js", js), ("theme-init.js", head_js)):
        if re.search(r"</(script|style)", src, re.I):
            raise ValueError(f"{label} must not contain a closing </script> or </style>")
    page = (shell
            .replace("{{CSS}}", css)
            .replace("{{HEAD_JS}}", head_js)
            .replace("{{TABS}}", render_tabs())
            .replace("{{PANELS}}", render_panels(data))
            .replace("{{BUILT_AT}}", esc(meta["built_at"]))
            .replace("{{DATA}}", "\n".join(json_block(k, v) for k, v in blocks.items()))
            .replace("{{JS}}", js))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return {
        "path": str(out),
        "bytes": len(page.encode("utf-8")),
        "papers": [p["id"] for p in data["papers"]],
        "references": len(data["references"].get("references", [])),
        "stimuli_rows": stim_rows,
        "stimuli_missing": data["stimuli_missing"],
        "warnings": b.warnings,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                    help="repository root (default: this checkout)")
    ap.add_argument("--out", type=Path, default=None,
                    help="output HTML (default: <root>/dashboard/index.html)")
    ap.add_argument("--quiet", action="store_true", help="do not list warnings")
    args = ap.parse_args(argv)
    summary = build(args.root, args.out)
    kb = summary["bytes"] / 1024
    print(f"wrote {summary['path']} ({kb:,.0f} KB)")
    print(f"  papers {len(summary['papers'])} · references {summary['references']} · "
          f"stimuli {summary['stimuli_rows']}"
          + (f" · missing {summary['stimuli_missing']}" if summary["stimuli_missing"] else ""))
    if summary["warnings"]:
        print(f"  warnings {len(summary['warnings'])}")
        if not args.quiet:
            for w in summary["warnings"]:
                print(f"   - {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
