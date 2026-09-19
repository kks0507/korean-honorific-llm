"""content/summary_2p.json → dashboard/summary-2p.html (A4 두 쪽 핵심 요약).

같은 본문으로 두 파일을 만든다.
- dashboard/summary-2p.html : 저장소용 완결 문서(<!doctype html> 포함). 브라우저에서 인쇄하면 A4 두 쪽.
- --fragment 경로          : Artifact 게시용 조각(doctype·html·head·body 없음).
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "content" / "summary_2p.json"
OUT = ROOT / "dashboard" / "summary-2p.html"

EXP_TONE = {"E1": "teal", "E2": "amber", "E3": "violet", "E4": "gray"}

CSS = """
:root {
  --ground: #ecece6;
  --paper: #ffffff;
  --ink: #1c1c19;
  --ink-2: #45453f;
  --ink-3: #61615a;
  --rule: #dcdcd4;
  --rule-strong: #bdbdb2;
  --wash: #f4f4f0;
  --accent: #2a55b0;
  --accent-soft: #eaf0fb;
  --accent-line: #bccbeb;
  --teal-bg: #d9f0ec;   --teal-fg: #0d5249;
  --amber-bg: #fbeed2;  --amber-fg: #714604;
  --violet-bg: #ebe5f9; --violet-fg: #4b3189;
  --gray-bg: #ebebe6;   --gray-fg: #45453f;
  --sheet-shadow: 0 1px 3px rgba(20, 20, 10, .08), 0 8px 24px rgba(20, 20, 10, .06);
  --font: "Noto Sans KR", -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground: #121211;
    --paper: #1b1b19;
    --ink: #ecece7;
    --ink-2: #c9c9c1;
    --ink-3: #a7a79e;
    --rule: #35352f;
    --rule-strong: #4f4f47;
    --wash: #232320;
    --accent: #8fb0ff;
    --accent-soft: #1d2842;
    --accent-line: #364a7a;
    --teal-bg: #133532;   --teal-fg: #93dccf;
    --amber-bg: #3a2c0e;  --amber-fg: #f1c979;
    --violet-bg: #2a2142; --violet-fg: #cbbaf6;
    --gray-bg: #2b2b27;   --gray-fg: #c9c9c1;
    --sheet-shadow: 0 1px 3px rgba(0, 0, 0, .4);
  }
}
:root[data-theme="dark"] {
  --ground: #121211;
  --paper: #1b1b19;
  --ink: #ecece7;
  --ink-2: #c9c9c1;
  --ink-3: #a7a79e;
  --rule: #35352f;
  --rule-strong: #4f4f47;
  --wash: #232320;
  --accent: #8fb0ff;
  --accent-soft: #1d2842;
  --accent-line: #364a7a;
  --teal-bg: #133532;   --teal-fg: #93dccf;
  --amber-bg: #3a2c0e;  --amber-fg: #f1c979;
  --violet-bg: #2a2142; --violet-fg: #cbbaf6;
  --gray-bg: #2b2b27;   --gray-fg: #c9c9c1;
  --sheet-shadow: 0 1px 3px rgba(0, 0, 0, .4);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: var(--font);
  font-size: 9pt;
  line-height: 1.5;
  padding-inline: 16px;
  padding-block: 24px;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.sheets { display: flex; flex-direction: column; align-items: center; gap: 24px; }
.sheet {
  width: 210mm;
  max-width: 100%;
  min-height: 297mm;
  background: var(--paper);
  box-shadow: var(--sheet-shadow);
  padding: 13mm 14mm 11mm;
  display: flex;
  flex-direction: column;
  gap: 3.2mm;
}
.sheet-foot {
  margin-top: auto;
  padding-top: 2mm;
  border-top: 1px solid var(--rule);
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: var(--ink-3);
  font-size: 7.4pt;
}
.masthead { display: grid; gap: 1.2mm; }
.eyebrow { font-size: 7.4pt; letter-spacing: .08em; color: var(--accent); font-weight: 700; }
h1 { margin: 0; font-size: 16pt; line-height: 1.3; font-weight: 800; letter-spacing: -.01em; text-wrap: balance; }
.byline { margin: 0; color: var(--ink-3); font-size: 7.6pt; }
.question {
  background: var(--accent-soft);
  border: 1px solid var(--accent-line);
  border-radius: 6px;
  padding: 3mm 4mm;
  display: grid;
  gap: 1.6mm;
}
.question .label { font-size: 7.4pt; font-weight: 700; color: var(--accent); letter-spacing: .04em; }
.question .q { margin: 0; font-size: 11pt; font-weight: 700; line-height: 1.45; text-wrap: balance; }
.question .claim { margin: 0; color: var(--ink-2); font-size: 8.4pt; }
section { display: grid; gap: 1.6mm; }
.sec-head { display: flex; align-items: baseline; gap: 2.4mm; border-bottom: 1.5px solid var(--ink); padding-bottom: 1mm; }
.sec-tag {
  font-size: 7.6pt; font-weight: 800; letter-spacing: .06em;
  color: var(--paper); background: var(--ink);
  padding: .2mm 1.8mm; border-radius: 3px; white-space: nowrap;
}
h2 { margin: 0; font-size: 10.5pt; font-weight: 800; }
.items { margin: 0; padding: 0; list-style: none; display: grid; gap: 1.2mm; }
.items li { display: grid; grid-template-columns: 24mm 1fr; gap: 2.4mm; }
.items .k { font-weight: 700; color: var(--ink); }
.items .v { color: var(--ink-2); }
.hyp { display: grid; grid-template-columns: 1fr 1fr; gap: 2.4mm; }
.hyp div { border: 1px solid var(--rule); border-radius: 5px; padding: 2mm 3mm; background: var(--wash); }
.hyp b { display: block; margin-bottom: .6mm; }
.hyp p { margin: 0; color: var(--ink-2); font-size: 8.3pt; }
.note { margin: 0; color: var(--ink-3); font-size: 7.8pt; }
.note.strong { color: var(--ink-2); font-size: 8.3pt; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 8.1pt; line-height: 1.42; }
th, td { text-align: left; vertical-align: top; padding: 1.3mm 1.8mm; border-bottom: 1px solid var(--rule); }
thead th { font-size: 7.4pt; color: var(--ink-3); font-weight: 700; border-bottom: 1px solid var(--rule-strong); letter-spacing: .02em; }
td.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
td .t { font-weight: 700; color: var(--ink); }
td .d { color: var(--ink-2); }
.ex { color: var(--ink-2); }
.badge {
  display: inline-block; font-size: 7.4pt; font-weight: 800; padding: 0 1.6mm; border-radius: 3px; white-space: nowrap;
}
.badge.teal { background: var(--teal-bg); color: var(--teal-fg); }
.badge.amber { background: var(--amber-bg); color: var(--amber-fg); }
.badge.violet { background: var(--violet-bg); color: var(--violet-fg); }
.badge.gray { background: var(--gray-bg); color: var(--gray-fg); }
.tier { color: var(--ink-3); white-space: nowrap; }
.axis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0; margin: .6mm 0 .4mm; }
.axis div {
  position: relative; padding: 1.6mm 2.6mm 1.6mm 3.6mm; font-size: 8.1pt; font-weight: 700;
  background: var(--accent-soft); color: var(--ink); border: 1px solid var(--accent-line);
}
.axis div + div { border-left: none; }
.axis div:first-child { border-radius: 5px 0 0 5px; }
.axis div:last-child { border-radius: 0 5px 5px 0; }
.axis-cap { margin: 0; font-size: 7.6pt; color: var(--ink-3); }
.open { border: 1px dashed var(--rule-strong); border-radius: 5px; padding: 2mm 3mm; color: var(--ink-2); font-size: 8pt; margin: 0; }
@media screen and (max-width: 820px) {
  body { font-size: 10pt; }
  .sheet { width: 100%; min-height: 0; padding: 20px 16px; gap: 14px; }
  .items li { grid-template-columns: 1fr; gap: 2px; }
  .hyp { grid-template-columns: 1fr; }
  .axis { grid-template-columns: 1fr; }
  .axis div, .axis div + div { border: 1px solid var(--accent-line); border-radius: 5px; }
  .axis { gap: 6px; }
  table { min-width: 560px; }
}
@page { size: A4; margin: 0; }
@media print {
  :root, :root:not([data-theme="light"]), :root[data-theme="dark"] {
    --ground: #ffffff; --paper: #ffffff; --ink: #1c1c19; --ink-2: #45453f; --ink-3: #61615a;
    --rule: #dcdcd4; --rule-strong: #bdbdb2; --wash: #f4f4f0; --accent: #2a55b0; --accent-soft: #eaf0fb; --accent-line: #bccbeb;
    --teal-bg: #d9f0ec; --teal-fg: #0d5249; --amber-bg: #fbeed2; --amber-fg: #714604;
    --violet-bg: #ebe5f9; --violet-fg: #4b3189; --gray-bg: #ebebe6; --gray-fg: #45453f;
  }
  body { padding: 0; background: #fff; font-size: 9pt; }
  .sheets { gap: 0; display: block; }
  .sheet { width: 210mm; height: 297mm; min-height: 0; box-shadow: none; break-after: page; overflow: hidden; }
  .sheet:last-child { break-after: auto; }
}
"""

FONT_LINK = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;800&display=swap">'


def e(s: str) -> str:
    return html.escape(s, quote=True)


def items(pairs) -> str:
    li = "".join(f'<li><span class="k">{e(k)}</span><span class="v">{e(v)}</span></li>' for k, v in pairs)
    return f'<ul class="items">{li}</ul>'


def sec(s: dict, body: str) -> str:
    return (f'<section id="sec-{e(s["id"])}" aria-labelledby="h-{e(s["id"])}">'
            f'<div class="sec-head"><span class="sec-tag">{e(s["tag"])}</span><h2 id="h-{e(s["id"])}">{e(s["title"])}</h2></div>'
            f'{body}</section>')


def build_body(d: dict) -> str:
    S = {s["id"]: s for s in d["sections"]}
    why, what, how, who, ww, imp = (S[k] for k in ("why", "what", "how", "who", "whenwhere", "implications"))

    hyp = "".join(f'<div><b>{e(k)}</b><p>{e(v)}</p></div>' for k, v in what["hypotheses"])
    exp_rows = "".join(
        f'<tr><td><span class="badge {EXP_TONE[i]}">{e(i)}</span></td>'
        f'<td><span class="t">{e(t)}</span><br><span class="d">{e(f)}</span></td>'
        f'<td class="ex">{e(x)}</td><td class="d">{e(p)}</td></tr>'
        for i, t, f, x, p in what["experiments"])
    what_body = (f'<div class="hyp">{hyp}</div><p class="note strong">{e(what["hypotheses_note"])}</p>'
                 f'<div class="table-wrap"><table><thead><tr><th>실험</th><th>설계(요인 A × 요인 B)</th><th>목표 문장 예</th><th>두 가설이 갈리는 지점</th></tr></thead>'
                 f'<tbody>{exp_rows}</tbody></table></div><p class="note">{e(what["stimuli_note"])}</p>')

    model_rows = "".join(
        f'<tr><td class="tier">{e(t)}</td><td><span class="t">{e(m)}</span></td><td class="d">{e(r)}</td><td class="num">{e(c)}</td></tr>'
        for t, m, r, c in who["models"])
    who_body = (f'<div class="table-wrap"><table><thead><tr><th>계층</th><th>모델</th><th>고른 이유</th><th>본실험 비용</th></tr></thead>'
                f'<tbody>{model_rows}</tbody></table></div><p class="note">{e(who["models_note"])}</p>')

    axis = "".join(f"<div>{e(a)}</div>" for a in imp["axis"])
    imp_body = (f'<div class="axis" role="list">{axis}</div>'
                f'<p class="axis-cap">-시-를 허가하는 인물이 서술어에서 멀어지는 순서. 인간과 모델의 일치도가 이 축에서 어떻게 변하는지가 연구의 대표 결과가 된다.</p>'
                f'{items(imp["bullets"])}')

    sheet1 = (f'<article class="sheet" aria-label="1쪽">'
              f'<header class="masthead"><span class="eyebrow">연구 설계 핵심 요약 · A4 2쪽</span><h1>{e(d["title"])}</h1><p class="byline">{e(d["byline"])}</p></header>'
              f'<div class="question"><span class="label">연구 질문</span><p class="q">{e(d["question"])}</p><p class="claim">{e(d["claim"])}</p></div>'
              f'{sec(why, items(why["bullets"]))}'
              f'{sec(what, what_body)}'
              f'<footer class="sheet-foot"><span>한국어 경어법 × LLM 후속 연구 설계</span><span>1 / 2</span></footer></article>')
    sheet2 = (f'<article class="sheet" aria-label="2쪽">'
              f'{sec(how, items(how["bullets"]))}'
              f'{sec(who, who_body)}'
              f'{sec(ww, items(ww["bullets"]))}'
              f'{sec(imp, imp_body)}'
              f'<p class="open">{e(d["open_items"])}</p>'
              f'<footer class="sheet-foot"><span>원천: content/*.json · 참고문헌과 쪽수 근거는 대시보드와 보고서에 있다</span><span>2 / 2</span></footer></article>')
    return f'<main class="sheets">{sheet1}{sheet2}</main>'


def render(d: dict, fragment: bool) -> str:
    head = f'<title>경어법 LLM 연구 요약</title>\n{FONT_LINK}\n<style>{CSS}</style>\n'
    body = build_body(d)
    if fragment:
        return head + body + "\n"
    return ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'{head}</head>\n<body>\n{body}\n</body>\n</html>\n')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fragment", type=Path, help="Artifact 게시용 조각 파일 경로")
    a = ap.parse_args()
    d = json.loads(SRC.read_text(encoding="utf-8"))
    OUT.write_text(render(d, fragment=False), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
    if a.fragment:
        a.fragment.write_text(render(d, fragment=True), encoding="utf-8")
        print(f"wrote {a.fragment}")


if __name__ == "__main__":
    main()
