"""content/summary_req_2p.json → dashboard/summary-requirements.html (의뢰 5개 항목별 A4 두 쪽 요약).

디자인 토큰·공통 스타일은 build_summary_html.py(첫 번째 요약)와 같다. --fragment로 Artifact 게시용 조각도 만든다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_summary_html import CSS as BASE_CSS, FONT_LINK, e  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "content" / "summary_req_2p.json"
OUT = ROOT / "dashboard" / "summary-requirements.html"

NORM_TONE = {"적격": "ok", "덜 선호": "mid", "부적격": "bad", "비표준": "bad"}

EXTRA_CSS = """
.req { display: grid; gap: 1.5mm; }
.req-head { display: flex; align-items: baseline; gap: 2.4mm; border-bottom: 1.5px solid var(--ink); padding-bottom: 1mm; }
.req-no {
  font-size: 8pt; font-weight: 800; color: var(--paper); background: var(--ink);
  border-radius: 3px; padding: .2mm 1.8mm; white-space: nowrap;
}
.req-head h2 { font-size: 10.5pt; }
.ask { margin: 0; font-size: 7.8pt; color: var(--ink-3); }
.ask b { color: var(--accent); font-weight: 700; }
.lead { margin: 0; color: var(--ink-2); font-size: 8.4pt; }
.layers td:first-child { font-weight: 800; white-space: nowrap; }
.layers td.what { color: var(--ink-3); font-size: 7.6pt; width: 23%; }
.layers td.find { width: 58%; }
.layers td.to { color: var(--accent); font-weight: 600; }
.design {
  margin: 0; padding: 2mm 3mm; border-radius: 5px; font-size: 8.3pt;
  background: var(--accent-soft); border: 1px solid var(--accent-line); color: var(--ink);
}
.exps { display: grid; gap: 1.8mm; }
.exp { border: 1px solid var(--rule); border-radius: 6px; padding: 2mm 2.6mm; display: grid; gap: 1.2mm; }
.exp-top { display: flex; flex-wrap: wrap; align-items: baseline; gap: 1.8mm; }
.exp-top .t { font-weight: 800; }
.exp-top .f { color: var(--ink-2); font-size: 8pt; }
.exp-top .n { margin-left: auto; color: var(--ink-3); font-size: 7.4pt; }
.ctx { margin: 0; font-size: 7.8pt; color: var(--ink-3); }
.grid22 { display: grid; grid-template-columns: 17mm 1fr 1fr; border: 1px solid var(--rule); border-radius: 4px; overflow: hidden; font-size: 8pt; }
.grid22 > div { padding: 1.1mm 1.8mm; border-top: 1px solid var(--rule); border-left: 1px solid var(--rule); }
.grid22 > .h { background: var(--wash); color: var(--ink-3); font-size: 7.3pt; font-weight: 700; border-top: none; }
.grid22 > .h:first-child, .grid22 > .rh { border-left: none; }
.grid22 > .rh { font-weight: 700; font-size: 7.6pt; background: var(--wash); }
.cell { display: flex; justify-content: space-between; align-items: flex-start; gap: 1.6mm; }
.cell .s { color: var(--ink); }
.norm { font-size: 6.9pt; font-weight: 700; padding: 0 1.2mm; border-radius: 3px; white-space: nowrap; }
.norm.ok { background: var(--teal-bg); color: var(--teal-fg); }
.norm.mid { background: var(--amber-bg); color: var(--amber-fg); }
.norm.bad { background: #fbe2df; color: #922015; }
.predict { margin: 0; font-size: 7.8pt; color: var(--ink-2); }
.predict b { color: var(--ink); }
.e4 { display: grid; grid-template-columns: auto 1fr; gap: 2mm; align-items: baseline; font-size: 8pt; color: var(--ink-2); border: 1px solid var(--rule); border-radius: 6px; padding: 1.8mm 2.6mm; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; }
.lk { display: grid; gap: 1.2mm; }
.lk div { border: 1px solid var(--rule); border-radius: 5px; padding: 1.6mm 2.4mm; background: var(--wash); font-size: 8pt; color: var(--ink-2); }
.lk b { display: block; color: var(--ink); font-size: 8.2pt; }
.cq td:first-child { white-space: nowrap; font-weight: 700; }
.cq td.use { color: var(--ink-3); font-size: 7.6pt; width: 38%; }
.sub { margin: 0; padding: 2mm 3mm; border-left: 3px solid var(--accent); background: var(--wash); font-size: 8pt; color: var(--ink-2); }
.imp td:first-child { font-weight: 700; white-space: nowrap; }
.imp th:nth-child(2), .imp th:nth-child(3) { width: 40%; }
/* 두 쪽에 맞추는 밀도 조정(화면·인쇄 공통, 휴대폰 규칙보다 앞에 둔다) */
body { font-size: 8.6pt; line-height: 1.45; }
.sheet { padding: 11mm 13mm 9mm; gap: 2.6mm; }
table { font-size: 7.8pt; line-height: 1.38; }
th, td { padding: 1mm 1.6mm; }
.grid22 { font-size: 7.7pt; }
.grid22 > div { padding: .9mm 1.6mm; }
.lead, .design { font-size: 8.1pt; }
.exp { padding: 1.6mm 2.4mm; gap: 1mm; }
.req { gap: 1.3mm; }
h1 { font-size: 15pt; }
@media screen and (max-width: 820px) {
  body { font-size: 10pt; }
  .two { grid-template-columns: 1fr; }
  .grid22 { grid-template-columns: 64px 1fr 1fr; min-width: 520px; }
  .exp { overflow-x: auto; }
  .e4 { grid-template-columns: 1fr; }
}
@media print {
  .norm.bad { background: #fbe2df; color: #922015; }
}
"""
# 다크 모드에서도 '부적격' 배지를 읽히게: 토큰으로 바꾼다
EXTRA_CSS = EXTRA_CSS.replace(".norm.bad { background: #fbe2df; color: #922015; }\n.predict",
                              ".norm.bad { background: var(--red-bg); color: var(--red-fg); }\n.predict")
TOKENS_LIGHT = "  --red-bg: #fbe2df;     --red-fg: #922015;\n"
TOKENS_DARK = "    --red-bg: #401b17;     --red-fg: #f6aaa0;\n"


def css() -> str:
    c = BASE_CSS
    c = c.replace("  --gray-bg: #ebebe6;   --gray-fg: #45453f;\n  --sheet-shadow", "  --gray-bg: #ebebe6;   --gray-fg: #45453f;\n" + TOKENS_LIGHT + "  --sheet-shadow", 1)
    c = c.replace("    --gray-bg: #2b2b27;   --gray-fg: #c9c9c1;\n    --sheet-shadow", "    --gray-bg: #2b2b27;   --gray-fg: #c9c9c1;\n" + TOKENS_DARK + "    --sheet-shadow", 1)
    c = c.replace("  --gray-bg: #2b2b27;   --gray-fg: #c9c9c1;\n  --sheet-shadow", "  --gray-bg: #2b2b27;   --gray-fg: #c9c9c1;\n" + TOKENS_DARK.replace("    ", "  ", 1) + "  --sheet-shadow", 1)
    return c + EXTRA_CSS


def head(no: int, title: str, ask: str) -> str:
    return (f'<div class="req-head"><span class="req-no">요청 {no}</span><h2 id="h-req{no}">{e(title)}</h2></div>'
            f'<p class="ask"><b>의뢰</b> {e(ask)}</p>')


def table(headers, rows, cls="") -> str:
    th = "".join(f"<th>{e(h)}</th>" for h in headers)
    return f'<div class="table-wrap"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def exp_block(x: dict) -> str:
    c = x["cells"]
    def cell(i):
        s, n = c[i]
        return f'<div><span class="cell"><span class="s">{e(s)}</span><span class="norm {NORM_TONE[n]}">{e(n)}</span></span></div>'
    grid = (f'<div class="grid22" role="table" aria-label="{e(x["id"])} 네 조건">'
            f'<div class="h"></div><div class="h">B1 -시- 있음</div><div class="h">B2 -시- 없음</div>'
            f'<div class="rh">{e(x["rows"][0])}</div>{cell(0)}{cell(1)}'
            f'<div class="rh">{e(x["rows"][1])}</div>{cell(2)}{cell(3)}</div>')
    return (f'<div class="exp"><div class="exp-top"><span class="badge {x["tone"]}">{e(x["id"])}</span>'
            f'<span class="t">{e(x["title"])}</span><span class="f">{e(x["factors"])}</span><span class="n">{e(x["sets"])}</span></div>'
            f'<p class="ctx">{e(x["context"])}</p>{grid}<p class="predict"><b>예측</b> {e(x["predict"])}</p></div>')


def build_body(d: dict) -> str:
    r1, r2, r3, r4, r5 = (d[k] for k in ("req1", "req2", "req3", "req4", "req5"))
    layer_rows = [f'<tr><td>{e(a)}</td><td class="find">{e(c)}</td><td class="to">{e(t)}</td></tr>' for a, b, c, t in r1["layers"]]
    sec1 = (f'<section class="req" aria-labelledby="h-req1">{head(1, "논문 4층 분석 → 후속 연구 설계", r1["ask"])}'
            f'<p class="lead">{e(r1["lead"])}</p>'
            f'{table(["층", "대표 발견(쪽수)", "설계로 이어진 것"], layer_rows, "layers")}'
            f'<p class="design">{e(r1["design"])}</p></section>')
    exps = "".join(exp_block(x) for x in r2["experiments"])
    i, t, n, body = r2["e4"]
    e4 = f'<div class="e4"><span><span class="badge gray">{e(i)}</span> <b>{e(t)}</b> <span class="n">{e(n)}</span></span><span>{e(body)}</span></div>'
    sec2 = (f'<section class="req" aria-labelledby="h-req2">{head(2, "2×2 실험 설계와 실험 문장", r2["ask"])}'
            f'<p class="lead">{e(r2["lead"])}</p><div class="exps">{exps}</div><p class="note">{e(r2["note"])}</p></section>')
    sec2b = (f'<section class="req" aria-label="요청 2 이어서"><div class="req-head"><span class="req-no">요청 2</span><h2>이어서 — 통제 실험</h2></div>'
             f'{e4}</section>')

    lk = "".join(f'<div><b>{e(k)}</b>{e(v)}</div>' for k, v in r3["likert"])
    cq_rows = [f'<tr><td>{e(a)}</td><td>{e(b)}</td><td class="use">{e(c)}</td></tr>' for a, b, c in r3["cq"]]
    sec3 = (f'<section class="req" aria-labelledby="h-req3">{head(3, "평가 — Likert 척도와 이해 문항", r3["ask"])}'
            f'<div class="lk two">{lk}</div><p class="note strong">{e(r3["likert_why"])}</p>'
            f'{table(["이해 문항", "질문과 선택지", "쓰임"], cq_rows, "cq")}'
            f'<p class="note">{e(r3["ops"])}</p></section>')
    m_rows = [f'<tr><td class="tier">{e(a)}</td><td><span class="t">{e(b)}</span></td><td class="d">{e(c)}</td><td class="num">{e(x)}</td></tr>' for a, b, c, x in r4["models"]]
    sec4 = (f'<section class="req" aria-labelledby="h-req4">{head(4, "추천 언어모델", r4["ask"])}'
            f'<p class="sub">{e(r4["subscription"])}</p>'
            f'{table(["계층", "모델", "고른 이유", "본실험 비용"], m_rows)}<p class="note">{e(r4["note"])}</p></section>')
    axis = "".join(f"<div>{e(a)}</div>" for a in r5["axis"])
    imp_rows = [f'<tr><td>{e(a)}</td><td class="d">{e(b)}</td><td class="d">{e(c)}</td></tr>' for a, b, c in r5["rows"]]
    sec5 = (f'<section class="req" aria-labelledby="h-req5">{head(5, "국어학적 함의", r5["ask"])}'
            f'<div class="axis" role="list">{axis}</div><p class="axis-cap">{e(r5["axis_cap"])}</p>'
            f'{table(["쟁점", "인간 결과가 이렇게 나오면", "모델 결과가 이렇게 나오면"], imp_rows, "imp")}</section>')

    sheet1 = (f'<article class="sheet" aria-label="1쪽">'
              f'<header class="masthead"><span class="eyebrow">의뢰 5개 항목별 답 · A4 2쪽</span><h1>{e(d["title"])}</h1><p class="byline">{e(d["byline"])}</p></header>'
              f'{sec1}{sec2}'
              f'<footer class="sheet-foot"><span>한국어 경어법 × LLM 후속 연구 — 의뢰 항목별 요약</span><span>1 / 2</span></footer></article>')
    sheet2 = (f'<article class="sheet" aria-label="2쪽">{sec2b}{sec3}{sec4}{sec5}'
              f'<footer class="sheet-foot"><span>원천: content/*.json · 쪽수 근거와 참고문헌은 대시보드에 있다</span><span>2 / 2</span></footer></article>')
    return f'<main class="sheets">{sheet1}{sheet2}</main>'


def render(d: dict, fragment: bool) -> str:
    headpart = f'<title>경어법 LLM 의뢰 항목 요약</title>\n{FONT_LINK}\n<style>{css()}</style>\n'
    body = build_body(d)
    if fragment:
        return headpart + body + "\n"
    return ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'{headpart}</head>\n<body>\n{body}\n</body>\n</html>\n')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fragment", type=Path)
    a = ap.parse_args()
    d = json.loads(SRC.read_text(encoding="utf-8"))
    OUT.write_text(render(d, False), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
    if a.fragment:
        a.fragment.write_text(render(d, True), encoding="utf-8")
        print(f"wrote {a.fragment}")


if __name__ == "__main__":
    main()
