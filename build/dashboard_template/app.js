/* 경어법 × LLM 연구 설계 대시보드 — 렌더러 (vanilla JS, 외부 의존 없음).
   데이터는 <script type="application/json" id="data-*">에서 읽는다.
   모든 텍스트는 esc()를 거쳐 HTML에 들어간다. */
(function () {
  'use strict';

  // ------------------------------------------------------------------ data
  const D = {};
  document.querySelectorAll('script[type="application/json"][id^="data-"]').forEach(function (s) {
    try { D[s.id.slice(5)] = JSON.parse(s.textContent); } catch (e) { D[s.id.slice(5)] = null; }
  });
  const META = D.meta || { tabs: [] };
  const PAPERS = D.papers || [];
  const PAPER = Object.fromEntries(PAPERS.map(p => [p.id, p]));
  const SYN = D.synthesis || {};
  const CAND = D.candidates || {};
  const EXPS = D.experiments || [];
  const EXP = Object.fromEntries(EXPS.map(e => [e.id, e]));
  const EVAL = D.evaluation || {};
  const MODELS = D.models || {};
  const IMP = D.implications || {};
  const ROAD = D.roadmap || {};
  const REFS = (D.references && D.references.references) || [];
  const REF_BY_KEY = Object.fromEntries(REFS.map(r => [r.key, r]));
  const MATRIX = D.matrix || {};
  const TRACK = D.tracker || {};
  const STIM = D.stimuli || {};
  const TAB_IDS = (META.tabs || []).map(t => t.id);
  const SECTION_TITLE = {};
  (META.tabs || []).forEach(t => (t.sections || []).forEach(s => { SECTION_TITLE[s.id] = { tab: t, title: s.title }; }));

  const HOOK = {};
  PAPERS.forEach(p => (p.successor_hooks || []).forEach(h => { HOOK[h.id] = Object.assign({ paper: p.id }, h); }));
  const GAP = Object.fromEntries((SYN.gaps || []).map(g => [g.id, g]));
  const CONFLICT = Object.fromEntries((SYN.conflicts || []).map(c => [c.id, c]));
  const HOOK_USE = {};
  const addUse = (h, kind, id) => { (HOOK_USE[h] = HOOK_USE[h] || []).push({ kind, id }); };
  (SYN.gaps || []).forEach(g => (g.basis_hooks || []).forEach(h => addUse(h, 'gap', g.id)));
  EXPS.forEach(e => {
    ((e.inherits || {}).hooks || []).forEach(h => addUse(h, 'exp', e.id));
    const x = e.extension_model_only;
    if (x) (x.inherits || []).forEach(h => addUse(h, 'exp', x.id || (e.id + '-X')));
  });
  const GAP_EXPS = {};
  EXPS.forEach(e => ((e.inherits || {}).gaps || []).forEach(g => { (GAP_EXPS[g] = GAP_EXPS[g] || []).push(e.id); }));

  // ------------------------------------------------------------- helpers
  const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  const esc = s => String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, c => ESC[c]);
  const isObj = v => v && typeof v === 'object' && !Array.isArray(v);
  const arr = v => Array.isArray(v) ? v : (v === null || v === undefined || v === '' ? [] : [v]);
  const safeUrl = u => /^https?:\/\//i.test(String(u || '')) ? String(u) : '';

  // author–year patterns for method references (e.g. "Brysbaert & Stevens, 2018")
  const AUTHOR_YEAR = [];
  REFS.forEach(r => {
    const m = String(r.apa || '').match(/^([A-Z][A-Za-zÀ-ÿ'\-]+),/);
    const y = String(r.apa || '').match(/\((\d{4})\)/);
    if (m && y && !/^P\d\d$/.test(r.key || '')) {
      AUTHOR_YEAR.push({ n: r.n, re: m[1].replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '[^()\\n]{0,40}?' + y[1] });
    }
  });
  const LINK_PARTS = [
    '(https?:\\/\\/[^\\s<>()\\[\\]{}"\\u3131-\\u318E\\uAC00-\\uD7A3]+)',
    '\\b(P(?:0[1-9]|10)-H\\d{1,2})\\b',
    '\\b(P(?:0[1-9]|10))\\b',
    '\\b(G(?:1[01]|[1-9]))\\b',
    '\\b(C[1-9])\\b',
    '\\b(E[1-4](?:-X)?)\\b'
  ].concat(AUTHOR_YEAR.map(a => '(' + a.re + ')'));
  const LINK_RE = new RegExp(LINK_PARTS.join('|'), 'g');

  function linkify(escaped) {
    return escaped.replace(LINK_RE, function (m) {
      const g = Array.prototype.slice.call(arguments, 1, 1 + LINK_PARTS.length);
      if (g[0]) {
        let url = g[0], tail = '';
        const t = url.match(/[.,;:]+$/);
        if (t) { tail = t[0]; url = url.slice(0, -tail.length); }
        return '<a href="' + url + '" target="_blank" rel="noopener">' + url + '</a>' + tail;
      }
      if (g[1]) return HOOK[g[1]] ? '<a class="xref" href="#hook-' + g[1] + '">' + g[1] + '</a>' : m;
      if (g[2]) return PAPER[g[2]] ? '<a class="xref" href="#paper-' + g[2] + '">' + g[2] + '</a>' : m;
      if (g[3]) return GAP[g[3]] ? '<a class="xref" href="#gap-' + g[3] + '">' + g[3] + '</a>' : m;
      if (g[4]) return CONFLICT[g[4]] ? '<a class="xref" href="#conflict-' + g[4] + '">' + g[4] + '</a>' : m;
      if (g[5]) { const e = g[5].slice(0, 2); return EXP[e] ? '<a class="xref" href="#exp-' + e + '">' + g[5] + '</a>' : m; }
      for (let i = 0; i < AUTHOR_YEAR.length; i++) {
        if (g[6 + i]) return m + '<a class="refn" href="#ref-' + AUTHOR_YEAR[i].n + '" title="참고문헌 [' + AUTHOR_YEAR[i].n + ']">[' + AUTHOR_YEAR[i].n + ']</a>';
      }
      return m;
    });
  }
  // plain text -> safe HTML with cross links and line breaks
  const rich = s => linkify(esc(s)).replace(/\n/g, '<br>');
  // minimal inline markdown for 인수인계서 cells: `code`, **bold**, ~~strike~~
  function md(s) {
    return String(s || '').split(/(`[^`]+`)/).map(function (part) {
      if (/^`[^`]+`$/.test(part)) return '<code>' + esc(part.slice(1, -1)) + '</code>';
      return linkify(esc(part))
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/~~([^~]+)~~/g, '<del>$1</del>');
    }).join('');
  }
  const src = (s, pid) => s ? '<span class="src" title="원문 PDF 쪽 번호">' + (pid ? esc(pid) + ' ' : '') + esc(s) + '</span>' : '';
  const badge = (t, c) => '<span class="badge ' + (c || '') + '">' + esc(t) + '</span>';
  const paperChip = pid => PAPER[pid]
    ? '<a class="chip" href="#paper-' + esc(pid) + '" title="' + esc(PAPER[pid].short) + '">' + esc(pid) + '</a>'
    : '<span class="chip">' + esc(pid) + '</span>';
  const hookChip = hid => HOOK[hid]
    ? '<a class="chip" href="#hook-' + esc(hid) + '" title="' + esc(String(HOOK[hid].hook_ko || '').slice(0, 140)) + '">' + esc(hid) + '</a>'
    : '<span class="chip">' + esc(hid) + '</span>';
  const expChip = eid => { const e = EXP[String(eid).slice(0, 2)]; return e ? '<a class="chip" href="#exp-' + esc(e.id) + '" title="' + esc(e.title_ko) + '">' + esc(eid) + '</a>' : '<span class="chip">' + esc(eid) + '</span>'; };
  const gapChip = gid => GAP[gid] ? '<a class="chip" href="#gap-' + esc(gid) + '" title="' + esc(GAP[gid].gap_ko) + '">' + esc(gid) + '</a>' : '<span class="chip">' + esc(gid) + '</span>';
  const conflictChip = cid => CONFLICT[cid] ? '<a class="chip" href="#conflict-' + esc(cid) + '" title="' + esc(CONFLICT[cid].issue_ko) + '">' + esc(cid) + '</a>' : '<span class="chip">' + esc(cid) + '</span>';
  const refChip = r => r ? '<a class="chip" href="#ref-' + esc(r.n) + '" title="' + esc(String(r.apa || '').slice(0, 160)) + '">[' + esc(r.n) + ']</a>' : '';
  const chips = list => '<span class="chips">' + list.join('') + '</span>';
  const details = (summary, body, open, cls) => '<details class="' + (cls || 'more') + '"' + (open ? ' open' : '') + '><summary>' + summary + '</summary><div class="' + ((cls || 'more') === 'panel' ? 'panel-body' : 'more-body') + '">' + body + '</div></details>';
  const kv = pairs => '<dl class="kv">' + pairs.filter(p => p && p[1] !== undefined && p[1] !== null && p[1] !== '').map(p => '<dt>' + esc(p[0]) + '</dt><dd>' + p[1] + '</dd>').join('') + '</dl>';
  const ul = (items, cls) => items.length ? '<ul' + (cls ? ' class="' + cls + '"' : '') + '>' + items.map(i => '<li>' + i + '</li>').join('') + '</ul>' : '';
  const table = (headers, rows, cls, caption) => '<div class="table-wrap" tabindex="0"><table class="' + (cls || '') + '">' + (caption ? '<caption>' + caption + '</caption>' : '') + '<thead><tr>' + headers.map(h => '<th scope="col">' + h + '</th>').join('') + '</tr></thead><tbody>' + rows.map(r => '<tr>' + r.map(c => '<td>' + c + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>';
  const empty = msg => '<p class="empty">' + esc(msg) + '</p>';
  const nameOf = s => String(s || '').split(' — ')[0];
  const bodyOf = s => String(s || '').split(' — ').slice(1).join(' — ') || String(s || '');
  // 받침에 따라 (으)로
  function ro(word) {
    const ch = String(word).trim().slice(-1).charCodeAt(0);
    if (ch < 0xAC00 || ch > 0xD7A3) return '로';
    const jong = (ch - 0xAC00) % 28;
    return (jong === 0 || jong === 8) ? '로' : '으로';
  }
  // generic value renderer for heterogeneous card fields (string | list | object)
  const LABELS = {
    old: '기존 분석', prior: '기존 분석', new: '원문 확인', paper: '원문', resolution: '처리', basis_src: '근거',
    item: '항목', experiment: '실험', label: '라벨', desc_ko: '설명', description: '설명', acceptability: '수용성',
    control_type: '통제 유형', np1: 'NP1', np2: 'NP2', licit_subject: '적법 주어', other_np: '다른 명사구', grammatical: '문법성',
    name: '이름', type: '유형', params: '규모', korean_training: '한국어 학습', note: '비고'
  };
  function val(v) {
    if (v === null || v === undefined || v === '') return '<span class="faint">—</span>';
    if (Array.isArray(v)) return v.length ? ul(v.map(val)) : '<span class="faint">—</span>';
    if (isObj(v)) return kv(Object.keys(v).map(k => [LABELS[k] || k, val(v[k])]));
    return rich(v);
  }

  const ROLE = { core: ['핵심 계승', 'b-blue'], adjacent: ['인접·방법', 'b-teal'], subdata: ['하위 데이터', 'b-violet'] };
  const roleBadge = r => badge((ROLE[r] || [r])[0], (ROLE[r] || [0, 'b-gray'])[1]);
  const VER = { verified: ['검증 완료', 'b-green'], corrected: ['검증·정정 완료', 'b-green'], draft: ['검증 대기', 'b-amber'] };
  const verBadge = s => badge((VER[s] || [s || '상태 없음'])[0], (VER[s] || [0, 'b-gray'])[1]);
  const KIND = {
    author_future_work: ['저자 후속 과제', 'b-blue'],
    unresolved_confound: ['미분리 교란', 'b-red'],
    untested_condition: ['미검증 조건', 'b-amber'],
    method_gap: ['방법 공백', 'b-violet'],
    model_generation: ['모델 세대', 'b-teal']
  };
  const kindBadge = k => badge((KIND[k] || [k])[0], (KIND[k] || [0, 'b-gray'])[1]);
  function priorityBadge(p) {
    const s = String(p || '');
    const c = s.startsWith('최우선') ? 'b-red' : s.startsWith('높음') ? 'b-amber' : s.startsWith('중간') ? 'b-blue' : 'b-gray';
    return badge(s, c);
  }
  function normBadge(s) {
    const t = String(s || '');
    const c = /부적격/.test(t) ? 'b-red' : /덜 선호/.test(t) ? 'b-amber' : /비표준/.test(t) ? 'b-violet' : /적격/.test(t) ? 'b-green' : 'b-gray';
    const short = t.split(/[:(（—]/)[0].trim() || t;
    return '<span class="badge ' + c + '" title="' + esc(t) + '">' + esc(short) + '</span>';
  }
  const W5 = [
    ['who', '누가', 'WHO', '저자·소속 / 누구를 실험했나'],
    ['when', '언제', 'WHEN', '발표 시점 / 실험 모델의 세대'],
    ['where', '어디서', 'WHERE', '발표처 / 데이터 출처 / 공개 자료'],
    ['what', '무엇을', 'WHAT', '연구 질문 / 핵심 주장 / 결과'],
    ['how', '어떻게', 'HOW', '자극 설계 / 측정 / 통계'],
    ['why', '왜', 'WHY', '문제의식 / 의의·한계 / 우리가 이어받을 것']
  ];
  const ROW_EN = { '누가': 'WHO', '언제': 'WHEN', '어디서': 'WHERE', '무엇을': 'WHAT', '어떻게': 'HOW', '왜': 'WHY' };

  // ------------------------------------------------------------ renderers
  const R = {};   // section id -> function returning HTML
  const INTRO = {
    why: '선행 연구 10편의 횡단 분석(합의·충돌·공백)에서 출발해, 결과가 나오기 전에 국어학적 함의를 조건문으로 적어 둔다. 출처: <code>content/synthesis.json</code>, <code>content/implications.json</code>',
    what: '두 가설이 갈리는 곳은 상호작용항뿐이다. 그래서 모든 실험은 2×2이고, 목표 문장은 조건 사이에서 고정한다. 출처: <code>content/experiments/</code>, <code>content/stimuli/</code>',
    who: '상용 API 모델과 한국어 모어 화자에게 문자 그대로 같은 과제를 준다. 출처: <code>content/models.json</code>, <code>content/evaluation.json</code>',
    when: '로드맵과 실행 순서, 모델 버전을 고정하는 규칙, 그리고 선행 연구가 어느 모델 세대를 실험했는지. 출처: <code>content/roadmap.json</code>, <code>content/evaluation.json</code>',
    where: '모델 호출·인간 실험·사전등록·투고가 이뤄지는 곳. 출처: <code>content/models.json</code>, <code>content/evaluation.json</code>, <code>content/implications.json</code>',
    how: '인간과 모델이 같은 맥락·문장·문구·척도로 답한다. 다른 것은 응답 형식(클릭 대 JSON)뿐이다. 출처: <code>content/evaluation.json</code>',
    papers: '논문 10편을 같은 틀(6하원칙 카드 · 단어·문장·문단·맥락 4층 · 계승 지점)로 정리했다. 회색 작은 칩은 <strong>원문 PDF 쪽 번호</strong>다. 출처: <code>content/papers/P01–P10.json</code>',
    track: '<code>인수인계서.md</code>의 표를 빌드 때 그대로 읽어 온다. 상태를 바꾸려면 인수인계서를 고치고 다시 빌드한다.',
    refs: 'APA 7, [n] 번호. DOI가 있으면 <code>https://doi.org/</code> 링크로 원문에 간다. 출처: <code>content/references.json</code>'
  };

  // ---- HOME ----------------------------------------------------------
  R['home-question'] = function () {
    const H = (CAND.meta || {}).common_hypotheses || {};
    const a = nameOf(H.H_surface).replace(/\s*가설$/, '') || '표면 공기';
    const b = nameOf(H.H_licensing).replace(/\s*가설$/, '') || '허가 조건';
    return '<div class="card hero">' +
      '<p class="eyebrow">연구 질문</p>' +
      '<p class="hero-q">LLM은 한국어 경어(-시-)의 적절성을 <em>‘' + esc(a) + '’</em>' + ro(a) + ' 판단하는가, <em>‘' + esc(b) + '’</em>' + ro(b) + ' 판단하는가?</p>' +
      '<div class="grid grid-2">' +
      '<div class="hyp surface"><p class="hyp-name">' + esc(nameOf(H.H_surface)) + '</p><p class="small muted">' + rich(bodyOf(H.H_surface)) + '</p></div>' +
      '<div class="hyp licensing"><p class="hyp-name">' + esc(nameOf(H.H_licensing)) + '</p><p class="small muted">' + rich(bodyOf(H.H_licensing)) + '</p></div>' +
      '</div>' +
      (H.why_2x2 ? '<p class="small" style="margin-top:12px"><strong>왜 2×2인가</strong> — ' + rich(H.why_2x2) + ' <a href="#what-hypotheses">가설 자세히 →</a></p>' : '') +
      '</div>' +
      (IMP.summary_claim_ko ? '<div class="callout claim prose"><span class="label">대표 주장 (조건문)</span>' + rich(IMP.summary_claim_ko) + ' <a href="#why-implications">함의 L1–L5 →</a></div>' : '');
  };

  function costTotals(onlyCore) {
    const tot = {};
    (MODELS.models || []).forEach(m => {
      if (onlyCore && !String(m.include || '').startsWith('핵심')) return;
      const cur = String(m.cur || '').split(/[\s(]/)[0] || '?';
      tot[cur] = (tot[cur] || 0) + (Number(m.cost_main) || 0);
    });
    return Object.keys(tot).map(c => c === 'USD' ? '$' + tot[c].toFixed(2) : c === 'KRW' ? '₩' + Math.round(tot[c]).toLocaleString('ko-KR') : tot[c] + ' ' + c).join(' + ');
  }

  R['home-numbers'] = function () {
    const roles = {};
    PAPERS.forEach(p => { roles[p.role] = (roles[p.role] || 0) + 1; });
    const roleNote = ['core', 'adjacent', 'subdata'].filter(r => roles[r]).map(r => ROLE[r][0] + ' ' + roles[r]).join(' · ');
    const gaps = SYN.gaps || [];
    const top = gaps.filter(g => String(g.priority || '').startsWith('최우선')).length;
    const core = EXPS.filter(e => e.licenser_distance !== null && e.licenser_distance !== undefined).length;
    const ctrl = EXPS.length - core;
    const rows = META.stimuli_rows || {};
    const nStim = Object.values(rows).reduce((a, b) => a + b, 0);
    const stimNote = Object.keys(rows).map(k => (STIM[k] ? STIM[k].label : k) + ' ' + rows[k]).join(' · ') +
      ((META.stimuli_missing || []).length ? ' · 작성 중: ' + META.stimuli_missing.join(', ') : '');
    const models = MODELS.models || [];
    const nCore = models.filter(m => String(m.include || '').startsWith('핵심')).length;
    const nOpt = models.length - nCore;
    const stat = (href, label, value, note, sm) => '<a class="stat" href="' + href + '"><div class="stat-label">' + esc(label) + '</div><div class="stat-value' + (sm ? ' sm' : '') + '">' + esc(value) + '</div><div class="stat-note">' + esc(note) + '</div></a>';
    return '<div class="stats">' +
      stat('#papers', '선행 논문', PAPERS.length + '편', roleNote) +
      stat('#why-gaps', '공백', gaps.length + '개', '최우선 ' + top + '개') +
      stat('#what-experiments', '실험', EXPS.length + '개', '핵심 ' + core + ' · 통제 ' + ctrl + ' (2×2)') +
      stat('#what-stimuli', '자극 문장', nStim + '행', stimNote) +
      stat('#who-models', '추천 모델', nCore + '개', '핵심 ' + nCore + ' · 선택 ' + nOpt) +
      stat('#who-models', '추정 비용(핵심·본실험)', costTotals(true), '모델별 단가 × 호출 예산, VAT 별도', true) +
      '</div>';
  };

  R['home-matrix'] = function () {
    const m = MATRIX.meta || {};
    const rows = m.rows || [], cols = m.cols || [];
    const cells = MATRIX.cells || [];
    if (!cells.length) return empty('dashboard_matrix.json이 비어 있다.');
    let h = '<div class="matrix" role="table" aria-label="6하원칙 × 5영역">';
    h += '<div class="mx-corner" role="columnheader"></div>' + cols.map(c => '<div class="mx-colhead" role="columnheader">' + esc(c) + '</div>').join('');
    rows.forEach(r => {
      h += '<div class="mx-rowhead" role="rowheader">' + esc(r) + ' <span class="en">' + esc(ROW_EN[r] || '') + '</span></div>';
      cols.forEach(c => {
        const cell = cells.find(x => x.row === r && x.col === c);
        if (!cell) { h += '<div class="mx-cell faint">—</div>'; return; }
        const dest = SECTION_TITLE[cell.anchor];
        const destTxt = dest ? dest.tab.label + ' · ' + dest.title : '#' + cell.anchor;
        h += '<a class="mx-cell" role="cell" href="#' + esc(cell.anchor) + '"><span class="mx-col">' + esc(c) + '</span>' + esc(cell.text_ko) + '<span class="mx-dest">→ ' + esc(destTxt) + '</span></a>';
      });
    });
    return h + '</div>';
  };

  R['home-axis'] = function () {
    const ax = IMP.axis || {};
    const onAxis = EXPS.filter(e => typeof e.licenser_distance === 'number').sort((a, b) => a.licenser_distance - b.licenser_distance);
    const off = EXPS.filter(e => typeof e.licenser_distance !== 'number');
    const lic = e => { const p = String(e.phenomenon || '').split('·').map(s => s.trim()).find(s => s.indexOf('허가자') === 0); return p || e.phenomenon || ''; };
    let h = '<p class="prose">' + (ax.name_ko ? '<strong>' + esc(ax.name_ko) + '</strong> — ' : '') + rich(ax.definition_ko || '') + '</p>';
    h += '<div class="axis">' + onAxis.map(e =>
      '<div class="axis-node"><span class="axis-dot" aria-hidden="true">' + esc(e.licenser_distance) + '</span><div class="card">' +
      '<div class="card-head"><span class="axis-dist">거리 ' + esc(e.licenser_distance) + '</span>' + expChip(e.id) + '</div>' +
      '<p class="axis-lic">' + esc(lic(e)) + '</p>' +
      '<p class="small muted" style="margin:0">' + esc(e.title_ko) + '</p></div></div>').join('') + '</div>';
    if (off.length) h += '<p class="small muted" style="margin-top:12px">축 밖의 통제 실험: ' + off.map(e => expChip(e.id) + ' ' + esc(e.title_ko)).join(' · ') + '</p>';
    if (ax.why_ko) h += '<div class="callout neutral prose small" style="margin-top:10px">' + rich(ax.why_ko) + '</div>';
    return h;
  };

  R['home-guide'] = function () {
    return '<div class="grid grid-3 guide">' + (META.tabs || []).filter(t => t.id !== 'home').map(t =>
      '<a class="card" href="#' + esc(t.id) + '"><span class="g-name">' + esc(t.label) + '</span>' + (t.en ? '<span class="g-en">' + esc(t.en) + '</span>' : '') +
      '<p class="small muted" style="margin:4px 0 0">' + esc(t.question) + '</p>' +
      (t.sections.length ? '<p class="xsmall faint" style="margin:6px 0 0">' + t.sections.map(s => esc(s.title)).join(' · ') + '</p>' : '') +
      '</a>').join('') + '</div>';
  };

  // ---- WHY -----------------------------------------------------------
  R['why-problem'] = function () {
    const w = ((TRACK.project_w5h1 || {}).rows || []).find(r => /왜/.test(r[0] || ''));
    const cm = SYN.coverage_matrix || {};
    let h = '';
    if (w) h += '<div class="callout prose"><span class="label">출발점</span>' + md(w[1]) + '</div>';
    h += '<div class="grid grid-2" style="margin-top:14px">';
    h += '<div class="card"><p class="col-h">선행 연구가 보여 준 것 (합의)</p><ul class="items">' + (SYN.agreements || []).map(a =>
      '<li><a class="chip" href="#agree-' + esc(a.id) + '">' + esc(a.id) + '</a> ' + rich(a.statement_ko) + '</li>').join('') + '</ul></div>';
    const tops = (SYN.gaps || []).filter(g => /^최우선/.test(g.priority || ''));
    h += '<div class="card"><p class="col-h">보여 주지 못한 것 (공백)</p>' +
      (cm.empty_cells_ko ? '<p>' + rich(cm.empty_cells_ko) + '</p>' : '') +
      '<ul class="items">' + tops.map(g => '<li>' + gapChip(g.id) + ' ' + rich(g.gap_ko) + '</li>').join('') + '</ul>' +
      '<p class="small" style="margin-top:6px"><a href="#why-gaps">공백 ' + (SYN.gaps || []).length + '개 전체 보기 →</a></p></div>';
    h += '</div>';

    // coverage matrix
    const dims = cm.dimensions || [];
    const cells = cm.cells || [];
    if (cells.length) {
      const map = { '측정': 'measure', '인간 자료': 'humans', '요인설계': 'factorial', '맥락(화자·청자 관계) 조작': 'context', '모델 세대': 'models' };
      const heads = ['논문', '다룬 현상'].concat(dims.map(esc));
      const rows = cells.map(c => [paperChip(c.paper) + '<div class="xsmall faint">' + esc((PAPER[c.paper] || {}).short || '') + '</div>', ul(arr(c.phenomena).map(esc))]
        .concat(dims.map(d => rich(c[map[d]] || c[d] || '—'))));
      h += details('범위 매트릭스 <span class="hint">논문 ' + cells.length + '편 × 현상·측정·인간 자료·요인설계·맥락·모델</span>',
        table(heads, rows, 't-wide'), false, 'panel');
    }
    // terminology
    if ((SYN.terminology || []).length) {
      h += details('용어 대조 <span class="hint">같은 말, 다른 뜻 — ' + SYN.terminology.length + '개</span>',
        SYN.terminology.map(t => '<div class="card" style="margin-top:10px"><p class="card-title">' + esc(t.term) + '</p>' +
          table(['논문', '이 논문에서의 뜻'], (t.usages || []).map(u => [paperChip(u.paper), rich(u.usage_ko) + src(u.src, u.paper)]), '') +
          '<div class="callout neutral small" style="margin-top:10px"><span class="label">쟁점</span>' + rich(t.issue_ko) + '</div></div>').join(''), false, 'panel');
    }
    if ((SYN.lineage || []).length) {
      h += details('인용 계보 <span class="hint">' + SYN.lineage.length + '개 연결</span>',
        table(['출발', '도착', '설명'], SYN.lineage.map(l => [esc(l.from), rich(l.to), rich(l.note)]), 't-mid'), false, 'panel');
    }
    return h;
  };

  R['why-agreements'] = function () {
    return '<div class="cards">' + (SYN.agreements || []).map(a =>
      '<article class="card" id="agree-' + esc(a.id) + '"><div class="card-head"><span class="card-id">' + esc(a.id) + '</span><span class="faint xsmall">근거 ' + arr(a.evidence).length + '건</span></div>' +
      '<p class="card-title">' + rich(a.statement_ko) + '</p>' +
      '<ul class="evid">' + arr(a.evidence).map(ev => '<li>' + paperChip(ev.paper) + ' ' + rich(ev.note) + src(ev.src, ev.paper) + '</li>').join('') + '</ul></article>').join('') + '</div>';
  };

  R['why-conflicts'] = function () {
    return '<div class="cards">' + (SYN.conflicts || []).map(c =>
      '<article class="card" id="conflict-' + esc(c.id) + '"><div class="card-head"><span class="card-id">' + esc(c.id) + '</span><span class="faint xsmall">입장 ' + arr(c.positions).length + '개</span></div>' +
      '<p class="card-title">' + rich(c.issue_ko) + '</p>' +
      '<ul class="evid">' + arr(c.positions).map(p => '<li>' + chips(arr(p.papers).map(paperChip)) + ' ' + rich(p.stance_ko) + src(p.src) + '</li>').join('') + '</ul>' +
      (c.why_it_matters_ko ? '<div class="callout small" style="margin-top:10px"><span class="label">우리 설계에 왜 중요한가</span>' + rich(c.why_it_matters_ko) + '</div>' : '') +
      '</article>').join('') + '</div>';
  };

  R['why-gaps'] = function () {
    const gaps = SYN.gaps || [];
    let h = '<div class="cards">' + gaps.map(g => {
      const exps = GAP_EXPS[g.id] || [];
      return '<article class="card" id="gap-' + esc(g.id) + '"><div class="card-head"><span class="card-id">' + esc(g.id) + '</span>' + priorityBadge(g.priority) + kindBadge(g.kind) +
        (exps.length ? '<span class="xsmall faint">→ 실험</span>' + chips(exps.map(expChip)) : '') + '</div>' +
        '<p class="card-title">' + rich(g.gap_ko) + '</p>' +
        (g.rationale_ko ? details('왜 공백인가', '<p class="prose">' + rich(g.rationale_ko) + '</p>') : '') +
        '<div class="card-foot"><span class="label">근거 계승 지점 ' + arr(g.basis_hooks).length + '개 — 누르면 논문 서가로</span>' + chips(arr(g.basis_hooks).map(hookChip)) + '</div></article>';
    }).join('') + '</div>';
    if ((SYN.design_implications || []).length) {
      h += '<h3 class="sub-h">공백에서 나온 설계 원칙 <span class="hint">synthesis.design_implications</span></h3>' +
        '<ol class="prose">' + SYN.design_implications.map(d => '<li>' + rich(d) + '</li>').join('') + '</ol>';
    }
    return h;
  };

  R['why-implications'] = function () {
    const meta = IMP.meta || {};
    let h = meta.principle_ko ? '<div class="callout prose"><span class="label">원칙</span>' + rich(meta.principle_ko) + '</div>' : '';
    h += '<div class="cards" style="margin-top:14px">' + (IMP.implications || []).map(L =>
      '<article class="card" id="impl-' + esc(L.id) + '"><div class="card-head"><span class="card-id">' + esc(L.id) + '</span>' +
      chips(arr(L.experiments).map(expChip)) + (arr(L.related_conflicts).length ? '<span class="xsmall faint">관련 충돌</span>' + chips(arr(L.related_conflicts).map(conflictChip)) : '') + '</div>' +
      '<p class="card-title">' + rich(L.title_ko) + '</p>' +
      '<div class="grid grid-2" style="margin-top:8px">' +
      '<div><p class="col-h">인간 결과가 이렇다면 → 지지하는 입장</p><ul class="ifs">' + arr(L.if_human).map(x => '<li><p class="if-cond">' + rich(x.result_ko) + '</p><p class="if-then">' + rich(x.supports_ko) + '</p></li>').join('') + '</ul></div>' +
      '<div><p class="col-h">모델 결과가 이렇다면 → 뜻하는 바</p><ul class="ifs">' + arr(L.if_model).map(x => '<li><p class="if-cond">' + rich(x.result_ko) + '</p><p class="if-then">' + rich(x.means_ko) + '</p></li>').join('') + '</ul></div>' +
      '</div>' +
      (arr(L.literature_needed).length ? details('보강할 국어학 문헌 ' + arr(L.literature_needed).length + '건', ul(arr(L.literature_needed).map(rich))) : '') +
      '</article>').join('') + '</div>';
    if (IMP.summary_claim_ko) h += '<div class="callout prose" style="margin-top:14px"><span class="label">대표 주장</span>' + rich(IMP.summary_claim_ko) + '</div>';
    if ((IMP.risks_to_claims || []).length) h += details('주장을 흔들 수 있는 위험 ' + IMP.risks_to_claims.length + '개', ul(IMP.risks_to_claims.map(rich)), false, 'panel');
    if (meta.caution_ko) h += '<p class="xsmall faint prose" style="margin-top:10px">' + rich(meta.caution_ko) + '</p>';
    return h;
  };

  R['why-corrections'] = function () {
    const t = TRACK.corrections || {};
    if (!(t.rows || []).length) return empty('인수인계서 §5.1 표를 찾지 못했다.');
    const hd = t.headers || [];
    return '<div class="cards">' + t.rows.map((r, i) =>
      '<article class="card" id="corr-' + (i + 1) + '"><div class="grid grid-3">' +
      r.map((c, j) => '<div><span class="label">' + esc(hd[j] || '') + '</span><div class="' + (j === 0 ? 'muted' : '') + '">' + (c ? md(c) : '<span class="faint">—</span>') + '</div></div>').join('') +
      '</div></article>').join('') + '</div>';
  };

  // ---- WHAT ----------------------------------------------------------
  const exFmt = s => esc(s).replace(/\[([^\]]{1,8})\]/g, '<span class="ex-l">$1</span>');
  function levelDesc(e, code) {
    for (const f of (e.factors || [])) {
      for (const l of arr(f.levels)) { if (String(l).indexOf(code + ' ') === 0 || l === code) return String(l).slice(code.length).trim(); }
    }
    return '';
  }
  const FIXED_LABEL = { addressee: '청자', speaker: '화자', subject_form: '주어 형태', scene: '장면', subject: '주어', subject_vs_addressee: '주어와 청자의 관계' };
  const ON_AXIS = EXPS.filter(e => typeof e.licenser_distance === 'number').sort((a, b) => a.licenser_distance - b.licenser_distance);
  const CONTROL_EXPS = EXPS.filter(e => typeof e.licenser_distance !== 'number');

  R['what-hypotheses'] = function () {
    const H = (CAND.meta || {}).common_hypotheses || {};
    let h = '<div class="grid grid-2">' +
      '<div class="card hyp-card surface"><p class="hyp-name">' + esc(nameOf(H.H_surface)) + '</p><p>' + rich(bodyOf(H.H_surface)) + '</p></div>' +
      '<div class="card hyp-card licensing"><p class="hyp-name">' + esc(nameOf(H.H_licensing)) + '</p><p>' + rich(bodyOf(H.H_licensing)) + '</p></div></div>';
    if (H.why_2x2) h += '<div class="callout prose" style="margin-top:12px"><span class="label">왜 2×2가 필요한가</span>' + rich(H.why_2x2) + '</div>';
    const rows = EXPS.filter(e => e.hypotheses).map(e => [expChip(e.id) + '<div class="xsmall faint">' + esc(bodyOf(e.title_ko)) + '</div>',
      rich((e.hypotheses || {}).licensing_condition), rich((e.hypotheses || {}).surface_cooccurrence), rich((e.hypotheses || {}).human_expected)]);
    if (rows.length) {
      h += '<h3 class="sub-h">실험별로 두 가설이 갈리는 곳</h3>' +
        table(['실험', '허가 조건 가설의 예측', '표면 공기 가설의 예측', '인간 예상'], rows, 't-wide');
    }
    return h;
  };

  function x22(e) {
    const conds = arr(e.conditions);
    const A = ['A1', 'A2'], B = ['B1', 'B2'];
    const cell = (a, b) => {
      const c = conds.find(x => x.A === a && x.B === b);
      if (!c) return '<div class="x22-cell faint">—</div>';
      return '<div class="x22-cell"><div class="x22-tag"><span class="code">' + esc(c.code) + '</span><span class="xsmall faint">' + esc(a) + '·' + esc(b) + '</span>' + normBadge(c.norm_status) + '</div>' +
        '<p class="x22-ex">' + exFmt(c.example_ko) + '</p><p class="xsmall faint" style="margin:0">' + esc(c.norm_status) + '</p></div>';
    };
    let h = '<div class="x22"><div class="x22-corner"></div>';
    B.forEach(b => { h += '<div class="x22-colhead"><strong>' + esc(b) + '</strong> ' + esc(levelDesc(e, b)) + '</div>'; });
    A.forEach(a => {
      h += '<div class="x22-rowhead"><strong>' + esc(a) + '</strong> ' + esc(levelDesc(e, a)) + '</div>';
      B.forEach(b => { h += cell(a, b); });
    });
    return h + '</div>';
  }

  function expArticle(e) {
    const dist = typeof e.licenser_distance === 'number' ? badge('허가자 거리 ' + e.licenser_distance, 'b-blue') : badge('통제 실험', 'b-gray');
    let h = '<div class="card-head">' + dist + badge(e.n_sets + '세트', 'outline') + '<span class="small muted">' + esc(e.phenomenon) + '</span></div>' +
      '<h3 class="exp-title">' + esc(e.id) + ' · ' + esc(e.title_ko) + '</h3>';
    if (e.research_question_ko) h += '<div class="callout prose"><span class="label">연구 질문</span>' + rich(e.research_question_ko) + '</div>';

    h += '<h4 class="sub-h">요인과 수준</h4><div class="grid grid-2">' + arr(e.factors).map(f =>
      '<div class="card"><p class="card-title">' + esc(f.name) + '</p><div class="chips" style="margin-bottom:6px">' + arr(f.levels).map(l => badge(l, 'outline')).join('') + '</div>' +
      '<p class="small muted" style="margin:0">' + rich(f.manipulation_ko) + '</p></div>').join('') + '</div>';
    const fixed = e.fixed || {};
    if (Object.keys(fixed).length || e.dv_definition_ko) {
      h += '<div class="card" style="margin-top:10px"><span class="label">고정한 것</span>' +
        kv(Object.keys(fixed).map(k => [FIXED_LABEL[k] || k, rich(fixed[k])]).concat(e.dv_definition_ko ? [['종속변수 정의', rich(e.dv_definition_ko)]] : [])) + '</div>';
    }

    h += '<h4 class="sub-h">2×2 조건 표 <span class="hint">행 = A, 열 = B · 예문은 설계 파일의 대표 예</span></h4>' + x22(e);

    const pt = (e.predictions || {}).table || [];
    if (pt.length) {
      h += '<h4 class="sub-h">예측 표 <span class="hint">표면 공기 가설이 인간과 다르게 예측하는 칸은 굵게</span></h4>' +
        table(['조건', '인간', '허가 조건 가설', '표면 공기 가설'], pt.map(r => [
          '<strong>' + esc(r.cond) + '</strong>', esc(r.human), esc(r.licensing),
          r.surface !== r.human ? '<strong class="diff">' + esc(r.surface) + '</strong>' : esc(r.surface)]), 't-mid');
    }
    if ((e.predictions || {}).interaction_ko) h += '<div class="callout" style="margin-top:10px"><span class="label">핵심 검정 — 상호작용 대비</span><span class="interaction">' + rich(e.predictions.interaction_ko) + '</span></div>';

    const dv = arr(e.dv);
    if (dv.length) {
      h += '<h4 class="sub-h">측정</h4><ul class="items card">' + dv.map(d =>
        '<li><span class="it-label">' + esc(d.name) + ' · ' + esc(d.scale) + '</span>' + rich(d.prompt_ko) + (d.note ? '<div class="xsmall faint">' + rich(d.note) + '</div>' : '') + '</li>').join('') + '</ul>';
    }
    const cq = e.comprehension_question || {};
    if (cq.role || cq.template) {
      h += details('이해 문항 설계', kv([['역할', rich(cq.role)], ['질문', cq.template ? rich(cq.template) : ''], ['선택지 규칙', cq.options_rule ? rich(cq.options_rule) : ''], ['정답 규칙', cq.answer_rule ? rich(cq.answer_rule) : '']]));
    }
    const inh = e.inherits || {};
    h += '<h4 class="sub-h">무엇을 계승하는가</h4><div class="card">' +
      kv([['공백', arr(inh.gaps).length ? chips(arr(inh.gaps).map(gapChip)) : ''],
        ['계승 지점', arr(inh.hooks).length ? chips(arr(inh.hooks).map(hookChip)) : ''],
        ['문장 근거', arr(inh.sentences).length ? ul(arr(inh.sentences).map(rich)) : '']]) + '</div>';
    if (e.linguistic_stake_ko) h += '<div class="callout neutral prose" style="margin-top:10px"><span class="label">국어학적으로 걸린 것</span>' + rich(e.linguistic_stake_ko) + '</div>';

    const norms = REFS.filter(r => r.group === '규범 자료');
    h += details('문항 제작 규칙 ' + arr(e.item_rules).length + '개', '<ol>' + arr(e.item_rules).map(x => '<li>' + rich(x) + '</li>').join('') + '</ol>');
    h += details('통제 ' + arr(e.controls).length + '개', ul(arr(e.controls).map(rich)));
    h += details('규범 근거 ' + arr(e.norm_basis).length + '개', ul(arr(e.norm_basis).map(rich)) + (norms.length ? '<p class="small">관련 참고문헌 ' + chips(norms.map(refChip)) + '</p>' : ''));
    h += details('위험과 대응 ' + arr(e.risks).length + '개', ul(arr(e.risks).map(rich)));
    const x = e.extension_model_only;
    if (x) {
      h += '<div class="card ext" style="margin-top:14px"><div class="card-head"><span class="card-id">' + esc(x.id) + '</span>' + badge('모델 전용 확장', 'b-teal') + '</div>' +
        '<p class="card-title">' + esc(x.title_ko) + '</p>' +
        kv([['요인', ul(arr(x.factors).map(rich))], ['종속변수', rich(x.dv_ko)], ['통제', rich(x.control_ko)], ['계승 지점', chips(arr(x.inherits).map(hookChip))]]) + '</div>';
    }
    if (STIM[e.id]) h += '<p style="margin-top:14px"><a class="chip" href="#what-stimuli" data-stim-exp="' + esc(e.id) + '">이 실험의 자극 ' + STIM[e.id].rows.length + '행 보기 →</a></p>';
    else h += '<p class="small faint" style="margin-top:14px">자극 파일 <code>content/stimuli/' + esc(e.id) + '.csv</code>가 아직 없다(작성 중).</p>';
    return h;
  }

  R['what-experiments'] = function () {
    if (!EXPS.length) return empty('실험 설계 파일이 없다.');
    return '<div class="sub-tabs" role="tablist" aria-label="실험 선택">' + EXPS.map((e, i) =>
      '<button type="button" role="tab" class="sub-tab" data-exp="' + esc(e.id) + '" aria-selected="' + (i === 0) + '">' + esc(e.id) + '<span class="cnt">' + esc(bodyOf(e.title_ko)) + '</span></button>').join('') + '</div>' +
      EXPS.map((e, i) => '<article class="exp" id="exp-' + esc(e.id) + '" data-exp-panel="' + esc(e.id) + '"' + (i ? ' hidden' : '') + '>' + expArticle(e) + '</article>').join('');
  };
  R['what-experiments'].after = function (el) {
    el.addEventListener('click', function (ev) {
      const b = ev.target.closest('[data-exp]');
      if (!b) return;
      selectExp(b.dataset.exp);
      try { history.replaceState(null, '', '#exp-' + b.dataset.exp); } catch (e) { /* file:// may refuse */ }
    });
  };
  function selectExp(eid) {
    renderPanel('what');
    document.querySelectorAll('[data-exp]').forEach(b => b.setAttribute('aria-selected', String(b.dataset.exp === eid)));
    document.querySelectorAll('[data-exp-panel]').forEach(p => { p.hidden = p.dataset.expPanel !== eid; });
  }

  R['what-candidates'] = function () {
    const meta = CAND.meta || {};
    const crit = ((meta.scoring || {}).criteria) || [];
    const rec = CAND.recommendation || {};
    const decision = {};
    arr(rec.core).forEach((k, i) => { decision[k] = ['선정 → ' + (ON_AXIS[i] ? ON_AXIS[i].id : '핵심'), 'b-green', ON_AXIS[i] && ON_AXIS[i].id]; });
    if (rec.control) decision[rec.control] = ['통제 → ' + (CONTROL_EXPS[0] ? CONTROL_EXPS[0].id : ''), 'b-blue', CONTROL_EXPS[0] && CONTROL_EXPS[0].id];
    const extExp = EXPS.find(e => e.extension_model_only);
    const extKey = String(rec.extension || '').split(/\s/)[0];
    if (extKey) decision[extKey] = ['확장 → ' + (extExp ? extExp.extension_model_only.id : ''), 'b-teal', extExp && extExp.id];
    Object.keys(rec.rejected || {}).forEach(k => { decision[k] = ['탈락', 'b-gray', null, rec.rejected[k]]; });
    let h = '';
    if (meta.status) h += '<div class="callout prose"><span class="label">결정</span>' + rich(meta.status) + '</div>';
    const shortCrit = c => String(c).split('(')[0].trim();
    const rows = (CAND.candidates || []).map(c => {
      const d = decision[c.id] || ['—', 'b-gray'];
      return ['<a class="chip" href="#cand-' + esc(c.id) + '">' + esc(c.id) + '</a>', rich(c.title_ko)]
        .concat(arr(c.score).map(s => '<span class="score-cell s' + esc(s) + '">' + esc(s) + '</span>'))
        .concat(['<strong class="tnum">' + esc(c.total) + '</strong>', badge(d[0], d[1]) + (d[3] ? '<div class="xsmall faint">' + rich(d[3]) + '</div>' : '')]);
    });
    h += '<h3 class="sub-h">채점표 <span class="hint">' + esc((meta.scoring || {}).scale || '') + '</span></h3>' +
      '<div class="table-wrap" tabindex="0"><table class="cand-table"><thead><tr><th scope="col">후보</th><th scope="col">설계</th>' +
      crit.map(c => '<th scope="col" class="c" title="' + esc(c) + '">' + esc(shortCrit(c)) + '</th>').join('') + '<th scope="col" class="c">합계</th><th scope="col">결정</th></tr></thead><tbody>' +
      rows.map(r => '<tr>' + r.map((c, i) => '<td' + (i >= 2 && i < 2 + crit.length + 1 ? ' class="c"' : '') + '>' + c + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>';
    if (rec.rationale_ko) h += '<div class="callout neutral prose" style="margin-top:12px"><span class="label">선정 이유</span>' + rich(rec.rationale_ko) + '</div>';
    h += details('후보 8개 상세 <span class="hint">요인·예문·예측·계승·메모</span>', (CAND.candidates || []).map(c => {
      const d = decision[c.id] || ['—', 'b-gray'];
      const f = c.factors || {};
      const pr = c.predictions || {};
      const inh = c.inherits || {};
      return '<article class="card" id="cand-' + esc(c.id) + '" style="margin-top:10px"><div class="card-head"><span class="card-id">' + esc(c.id) + '</span>' + badge(d[0], d[1]) + badge('합계 ' + c.total, 'outline') + '</div>' +
        '<p class="card-title">' + rich(c.title_ko) + '</p><p class="small muted">' + rich(c.phenomenon) + '</p>' +
        kv([['요인 A', rich(f.A)], ['요인 B', rich(f.B)], ['예문', '<span class="small">' + exFmt(c.example_ko) + '</span>'], ['종속변수', esc(arr(c.dv).join(' · '))],
          ['인간 예측', rich(pr.human)], ['허가 조건 가설', rich(pr.H_licensing)], ['표면 공기 가설', rich(pr.H_surface)],
          ['계승', chips(arr(inh.gaps).map(gapChip).concat(arr(inh.hooks).map(hookChip)).concat(arr(inh.conflicts).map(conflictChip)))],
          ['메모', rich(c.note_ko)]]) + '</article>';
    }).join(''), false, 'panel');
    return h;
  };

  // ---- stimulus browser ------------------------------------------------
  const STIM_KEYS = Object.keys(STIM);
  const ST = { exp: STIM_KEYS[0] || '', cond: 'all', set: 'all', list: 'all', role: 'all', norm: 'all', q: '', answers: false };
  const normCat = s => { const m = String(s || '').match(/^(적격|덜 선호|부적격|비표준)/); return m ? m[1] : '기타'; };
  const uniq = xs => Array.from(new Set(xs));
  function markCrit(sentence, crit) {
    const s = String(sentence || ''), c = String(crit || '').trim();
    if (!c) return esc(s);
    let ranges = [];
    const whole = s.indexOf(c);
    if (whole >= 0) ranges.push([whole, whole + c.length]);
    else {
      let from = 0;
      c.split(/\s+/).forEach(tok => { const i = s.indexOf(tok, from); if (i >= 0) { ranges.push([i, i + tok.length]); from = i + tok.length; } });
    }
    if (!ranges.length) return esc(s);
    let out = '', pos = 0;
    ranges.forEach(r => { out += esc(s.slice(pos, r[0])) + '<mark class="crit">' + esc(s.slice(r[0], r[1])) + '</mark>'; pos = r[1]; });
    return out + esc(s.slice(pos));
  }
  function stimRows() {
    const block = STIM[ST.exp];
    if (!block) return [];
    const q = ST.q.trim().toLowerCase();
    return block.rows.filter(r =>
      (ST.cond === 'all' || r.cond === ST.cond) &&
      (ST.set === 'all' || r.set_id === ST.set) &&
      (ST.list === 'all' || r.list === ST.list) &&
      (ST.role === 'all' || r.role === ST.role) &&
      (ST.norm === 'all' || normCat(r.norm_status) === ST.norm) &&
      (!q || [r.context, r.sentence, r.note, r.cq_question, r.cq_options].join(' ').toLowerCase().indexOf(q) >= 0));
  }
  function segHTML(key, label, options) {
    // a filter that cannot narrow anything ("전체" + one value) is hidden; the experiment picker always shows
    if (key !== 'exp' && options.filter(o => o[0] !== 'all').length < 2) return '';
    return '<div class="fgroup"><span class="flabel" id="fl-' + key + '">' + esc(label) + '</span><div class="seg" role="group" aria-labelledby="fl-' + key + '">' +
      options.map(o => '<button type="button" data-f="' + key + '" data-v="' + esc(o[0]) + '" aria-pressed="' + String(ST[key] === o[0]) + '"' + (o[2] ? ' title="' + esc(o[2]) + '"' : '') + (o[3] ? ' disabled' : '') + '>' + esc(o[1]) + '</button>').join('') + '</div></div>';
  }
  function stimControls() {
    const block = STIM[ST.exp] || { rows: [] };
    const rows = block.rows;
    const e = EXP[ST.exp];
    const expOpts = STIM_KEYS.map(k => [k, (STIM[k].label || k) + ' ' + STIM[k].rows.length, STIM[k].file])
      .concat((META.stimuli_missing || []).map(k => [k, k + ' 작성 중', 'content/stimuli/' + k + '.csv 없음', true]));
    const conds = uniq(rows.map(r => r.cond)).sort();
    const condOpts = [['all', '전체']].concat(conds.map(c => {
      const r = rows.find(x => x.cond === c) || {};
      const lv = [r.A_level, r.B_level].filter(Boolean);
      const desc = e ? lv.map(l => l + ' ' + levelDesc(e, l)).join(' × ') : '';
      return [c, c + (lv.length ? ' ' + lv.join('·') : ''), desc];
    }));
    const lists = uniq(rows.map(r => r.list).filter(Boolean)).sort();
    const roles = uniq(rows.map(r => r.role).filter(Boolean));
    const ROLE_KO = { target: '목표', violation: '위반', control: '적격 짝', filler: '채움' };
    const norms = uniq(rows.map(r => normCat(r.norm_status)));
    const sets = uniq(rows.map(r => r.set_id)).sort();
    return segHTML('exp', '실험', expOpts) +
      segHTML('cond', '조건', condOpts) +
      '<div class="fgroup"><label class="flabel" for="st-set">세트</label><select id="st-set" data-f="set"><option value="all">전체 ' + sets.length + '개</option>' +
      sets.map(s => '<option value="' + esc(s) + '"' + (ST.set === s ? ' selected' : '') + '>세트 ' + esc(s) + '</option>').join('') + '</select></div>' +
      segHTML('list', '라틴 방격 목록', [['all', '전체']].concat(lists.map(l => [l, l]))) +
      segHTML('role', '역할', [['all', '전체']].concat(roles.map(r => [r, ROLE_KO[r] || r]))) +
      segHTML('norm', '규범 판정', [['all', '전체']].concat(norms.map(n => [n, n]))) +
      '<div class="fgroup"><label class="flabel" for="st-q">검색</label><input id="st-q" type="search" data-f="q" placeholder="맥락·문장·메모" value="' + esc(ST.q) + '"></div>' +
      '<div class="fgroup"><span class="flabel">이해 문항</span><label class="toggle"><input type="checkbox" data-f="answers"' + (ST.answers ? ' checked' : '') + '> 정답 표시</label></div>';
  }
  function stimCard(r) {
    const e = EXP[r.exp] || EXP[ST.exp];
    const lv = [r.A_level, r.B_level].filter(Boolean);
    const lvDesc = e ? lv.map(l => l + ' ' + levelDesc(e, l)).join(' · ') : '';
    const opts = String(r.cq_options || '').split('|').filter(Boolean);
    const id = 'stim-' + ST.exp + '-' + r.set_id + '-' + r.cond + (r.role && r.role !== 'target' ? '-' + r.role : '');
    return '<article class="card stim" id="' + esc(id) + '"><div class="card-head">' +
      '<span class="card-id">' + esc(r.exp || ST.exp) + '</span>' +
      '<button type="button" class="linkish" data-set="' + esc(r.set_id) + '" title="이 세트만 보기">세트 ' + esc(r.set_id) + '</button>' +
      (r.cond ? badge('조건 ' + r.cond, 'b-blue') : '') +
      (r.role && r.role !== 'target' ? badge({ violation: '위반', control: '적격 짝', filler: '채움' }[r.role] || r.role, 'outline') : '') +
      (r.list ? badge('목록 ' + r.list, 'outline') : '') + normBadge(r.norm_status) + '</div>' +
      (lvDesc ? '<p class="xsmall faint" style="margin:0 0 6px">' + esc(lvDesc) + '</p>' : '') +
      '<p class="stim-ctx"><span class="label">맥락</span>' + esc(r.context) + '</p>' +
      '<p class="stim-sent">' + markCrit(r.sentence, r.critical_region) + '</p>' +
      (r.critical_region ? '<p class="stim-crit">조작 어절: <mark class="crit">' + esc(r.critical_region) + '</mark></p>' : '') +
      (r.cq_question ? '<div class="cq"><p class="cq-q">' + esc(r.cq_question) + '</p><ol class="cq-options">' +
        opts.map(o => '<li' + (o === r.cq_answer ? ' class="correct"' : '') + '>' + esc(o) + '</li>').join('') + '</ol></div>' : '') +
      '<p class="xsmall faint" style="margin:8px 0 0">규범 판정: ' + esc(r.norm_status || '—') + '</p>' +
      (r.note ? details('제작 메모', '<p class="small muted">' + esc(r.note) + '</p>') : '') +
      '</article>';
  }
  function renderStimList(root) {
    const list = root.querySelector('.stims');
    const line = root.querySelector('.result-line');
    const rows = stimRows();
    const block = STIM[ST.exp] || { rows: [], file: '' };
    line.innerHTML = '<strong>' + rows.length + '</strong>행 표시 · ' + esc(block.label || ST.exp) + ' 전체 <strong>' + block.rows.length + '</strong>행 <span class="faint">(' + esc(block.file) + ')</span>';
    list.classList.toggle('show-answers', ST.answers);
    list.innerHTML = rows.length ? rows.map(stimCard).join('') : '<p class="empty">조건에 맞는 문항이 없다.</p>';
  }
  function renderStimControls(root) {
    root.querySelector('.filters').innerHTML = stimControls();
  }
  R['what-stimuli'] = function () {
    if (!STIM_KEYS.length) return empty('자극 CSV가 아직 없다.');
    return '<p class="small muted prose">목표 문장에서 <mark class="crit">조작 어절</mark>을 강조했다. 인간은 라틴 방격 목록 하나(세트당 1조건)만 보고, 모델은 모든 조건을 단독으로 받는다. 세트 번호를 누르면 그 세트의 조건들만 모아 본다.</p>' +
      '<div class="filters" role="search" aria-label="자극 필터"></div><p class="result-line" aria-live="polite"></p><div class="stims"></div>';
  };
  R['what-stimuli'].after = function (el) {
    if (!STIM_KEYS.length) return;
    renderStimControls(el); renderStimList(el);
    let timer = null;
    el.addEventListener('click', function (ev) {
      const b = ev.target.closest('button[data-f]');
      if (b && !b.disabled) {
        const k = b.dataset.f;
        ST[k] = b.dataset.v;
        if (k === 'exp') { ST.cond = 'all'; ST.set = 'all'; ST.list = 'all'; ST.role = 'all'; ST.norm = 'all'; }
        renderStimControls(el); renderStimList(el);
        return;
      }
      const s = ev.target.closest('button[data-set]');
      if (s) {
        ST.set = ST.set === s.dataset.set ? 'all' : s.dataset.set;
        ST.cond = 'all'; ST.list = 'all';
        renderStimControls(el); renderStimList(el);
        el.scrollIntoView({ block: 'start' });
      }
    });
    el.addEventListener('change', function (ev) {
      const t = ev.target;
      if (t.dataset.f === 'set') { ST.set = t.value; renderStimList(el); }
      if (t.dataset.f === 'answers') { ST.answers = t.checked; el.querySelector('.stims').classList.toggle('show-answers', ST.answers); }
    });
    el.addEventListener('input', function (ev) {
      if (ev.target.dataset.f !== 'q') return;
      clearTimeout(timer);
      const v = ev.target.value;
      timer = setTimeout(function () { ST.q = v; renderStimList(el); }, 150);
    });
  };
  // "이 실험의 자극 보기" links
  document.addEventListener('click', function (ev) {
    const a = ev.target.closest('[data-stim-exp]');
    if (!a || !STIM[a.dataset.stimExp]) return;
    Object.assign(ST, { exp: a.dataset.stimExp, cond: 'all', set: 'all', list: 'all', role: 'all', norm: 'all', q: '' });
    const el = document.querySelector('[data-render="what-stimuli"]');
    if (el && rendered['what-stimuli']) { renderStimControls(el); renderStimList(el); }
  }, true);

  // ---- WHO -----------------------------------------------------------
  const MODEL_COLS = [['reasoning', '추론'], ['temperature', 'temperature'], ['seed', 'seed'], ['json', 'JSON'], ['logprobs', 'logprobs'], ['snapshot', '스냅샷']];
  const money = (v, cur) => {
    const c = String(cur || '');
    if (typeof v !== 'number') return esc(v);
    if (c.indexOf('USD') === 0) return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (c.indexOf('KRW') === 0) return '₩' + Math.round(v).toLocaleString('ko-KR');
    return esc(v) + ' ' + esc(c);
  };
  R['who-models'] = function () {
    const ms = MODELS.models || [];
    if (!ms.length) return empty('models.json이 비어 있다.');
    const incBadge = m => badge(m.include, String(m.include).indexOf('핵심') === 0 ? 'b-blue' : 'b-gray');
    let h = '<div class="table-wrap" tabindex="0"><table class="t-wide model-table"><thead><tr><th scope="col">모델</th><th scope="col">계층</th>' +
      MODEL_COLS.map(c => '<th scope="col">' + esc(c[1]) + '</th>').join('') + '<th scope="col" class="r">본실험 비용</th></tr></thead><tbody>' +
      ms.map(m => '<tr><th scope="row"><a href="#model-' + esc(m.key) + '">' + esc(m.model_id) + '</a><div class="xsmall faint">' + esc(m.provider) + '</div>' + incBadge(m) + '</th>' +
        '<td>' + esc(m.tier) + '</td>' + MODEL_COLS.map(c => '<td>' + rich(m[c[0]]) + '</td>').join('') +
        '<td class="r"><strong>' + money(m.cost_main, m.cur) + '</strong><div class="xsmall faint">' + esc(String(m.cur || '').replace(/^(USD|KRW)/, '').replace(/^\(|\)$/g, '')) + '</div></td></tr>').join('') +
      '</tbody></table></div>';
    h += '<p class="small muted" style="margin-top:8px">핵심 모델 합계: <strong>' + esc(costTotals(true)) + '</strong> · 선택 포함 합계: ' + esc(costTotals(false)) + '</p>';
    if (MODELS.total_estimate_ko) h += '<div class="callout prose small"><span class="label">비용 추정</span>' + rich(MODELS.total_estimate_ko) + '</div>';
    const cb = MODELS.call_budget || {};
    if (Object.keys(cb).length) {
      h += details('호출 예산과 토큰 가정', kv([
        ['본실험(모델당)', '<strong class="tnum">' + esc((cb.main_calls_per_model || 0).toLocaleString('ko-KR')) + '회</strong> — ' + rich(cb.main_breakdown_ko)],
        ['확장(모델당)', '<strong class="tnum">' + esc((cb.extension_calls_per_model || 0).toLocaleString('ko-KR')) + '회</strong> — ' + rich(cb.extension_breakdown_ko)],
        ['토큰 가정', rich(cb.token_assumption_ko)]]), false, 'panel');
    }
    h += '<h3 class="sub-h">모델별 역할과 근거</h3><div class="grid grid-2">' + ms.map(m =>
      '<article class="card model" id="model-' + esc(m.key) + '"><div class="card-head">' + incBadge(m) + badge(m.tier, 'outline') + '</div>' +
      '<p class="card-title">' + esc(m.model_id) + '</p><p class="xsmall faint" style="margin:0 0 8px">' + esc(m.provider) + '</p>' +
      '<p class="small">' + rich(m.role_ko) + '</p>' +
      kv([['단가(1M 토큰)', '입력 ' + money(m.pin, m.cur) + ' · 출력 ' + money(m.pout, m.cur)],
        ['본실험 비용', '<span class="cost">' + money(m.cost_main, m.cur) + '</span><div class="xsmall faint">' + rich(m.cost_main_note) + '</div>'],
        ['한국어 근거', rich(m.korean_evidence)],
        ['공식 문서', ul(arr(m.docs).map(u => safeUrl(u) ? '<a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(u) + '</a>' : esc(u)))]]) +
      '</article>').join('') + '</div>';
    return h;
  };
  R['who-rationale'] = function () {
    let h = MODELS.selection_rationale_ko ? '<div class="prose"><p>' + rich(MODELS.selection_rationale_ko) + '</p></div>' : '';
    const dc = MODELS.design_constraints_ko || [];
    if (dc.length) h += '<h3 class="sub-h">모델 특성이 설계에 준 제약 <span class="hint">' + dc.length + '개</span></h3><ol class="prose">' + dc.map(d => '<li>' + rich(d) + '</li>').join('') + '</ol>';
    return h || empty('선정 이유가 없다.');
  };
  R['who-excluded'] = function () {
    const ex = MODELS.excluded || [];
    return ex.length ? '<div class="grid grid-2">' + ex.map(x => '<div class="card"><p class="card-title">' + esc(x.name) + '</p><p class="small muted" style="margin:0">' + rich(x.reason_ko) + '</p></div>').join('') + '</div>' : empty('제외 모델이 없다.');
  };
  R['who-humans'] = function () {
    const hs = EVAL.human_study || {};
    const p = hs.participants || {};
    let h = '<div class="card">' + kv([
      ['모집 대상', rich(p.population_ko)],
      ['제외 기준', rich(p.exclusion_ko)],
      ['잠정 인원', rich(p.n_provisional)],
      ['인원 근거', rich(p.n_rationale_ko)],
      ['공변인', arr(p.covariates).length ? chips(arr(p.covariates).map(c => badge(c, 'outline'))) : '']]) + '</div>';
    const ss = arr(hs.sessions);
    if (ss.length) h += '<h3 class="sub-h">세션</h3><div class="grid grid-2">' + ss.map(s =>
      '<div class="card"><div class="card-head"><span class="card-id">세션 ' + esc(s.id) + '</span>' + (s.duration_min ? badge('약 ' + s.duration_min + '분', 'outline') : '') + '</div><p class="small" style="margin:0">' + rich(s.content_ko) + '</p></div>').join('') + '</div>';
    h += '<p class="small muted" style="margin-top:10px">주의 점검·채움 문장·연습 문항은 <a href="#how-controls">어떻게 → 통제</a>, 플랫폼과 IRB는 <a href="#where-platform">어디서 → 플랫폼</a>에 있다.</p>';
    return h;
  };
  function priorList(key, extra) {
    return '<div class="cards">' + PAPERS.map(p => {
      const c = (p.w5h1 || {})[key] || {};
      return '<article class="card"><div class="card-head">' + paperChip(p.id) + '<strong>' + esc(p.short) + '</strong>' + roleBadge(p.role) + (extra ? extra(p) : '') + '</div>' +
        '<p style="margin:0">' + rich(c.headline) + '</p>' +
        (arr(c.items).length ? details('근거 ' + arr(c.items).length + '개', itemsList(c.items, p.id)) : '') + '</article>';
    }).join('') + '</div>';
  }
  const itemsList = (items, pid) => '<ul class="items">' + arr(items).map(it => '<li><span class="it-label">' + esc(it.label) + '</span>' + rich(it.text) + src(it.src, pid) + '</li>').join('') + '</ul>';
  R['who-prior'] = () => priorList('who');

  // ---- WHEN ----------------------------------------------------------
  function weeks(s) {
    const m = String(s || '').match(/W(\d+)(?:\s*[–-]\s*W?(\d+))?/);
    return m ? [Number(m[1]), Number(m[2] || m[1])] : null;
  }
  R['when-roadmap'] = function () {
    const ph = ROAD.phases || [];
    if (!ph.length) return empty('roadmap.json이 비어 있다.');
    const max = Math.max.apply(null, ph.map(p => (weeks(p.weeks) || [0, 0])[1]).concat([1]));
    let h = (ROAD.meta && ROAD.meta.unit ? '<p class="small muted prose">' + esc(ROAD.meta.unit) + '</p>' : '') +
      '<div class="gantt" style="--weeks:' + max + '"><div class="g-head"><span class="g-spacer"></span><div class="g-scale" aria-hidden="true">' +
      Array.from({ length: max }, (_, i) => '<span>' + (i + 1) + '</span>').join('') + '</div></div>';
    h += ph.map(p => {
      const w = weeks(p.weeks);
      const cells = Array.from({ length: max }, (_, i) => '<span class="g-cell" style="grid-column:' + (i + 1) + '"></span>').join('');
      const bar = w ? '<span class="g-bar" style="grid-column:' + w[0] + ' / ' + (w[1] + 1) + '" title="' + esc(p.weeks) + '"></span>' : '';
      return '<div class="g-row" id="phase-' + esc(p.id) + '"><div class="g-label"><span class="card-id">' + esc(p.id) + '</span><span class="g-weeks">' + esc(p.weeks) + '</span> ' + esc(nameOf(p.what_ko)) +
        details('자세히', kv([['내용', rich(p.what_ko)], ['누가', rich(p.who_ko)], ['산출물', rich(p.output)],
          ['선행 조건', arr(p.depends).length ? chips(arr(p.depends).map(d => /^R\d+$/.test(d) ? '<a class="chip" href="#phase-' + esc(d) + '">' + esc(d) + '</a>' : badge(d, 'outline'))) : '없음']])) +
        '</div><div class="g-track" role="img" aria-label="' + esc(p.id + ' ' + p.weeks) + '">' + cells + bar + '</div></div>';
    }).join('');
    return h + '</div>';
  };
  R['when-order'] = function () {
    const st = EVAL.order_of_execution || [];
    return st.length ? '<ol class="steps prose">' + st.map(s => '<li>' + rich(String(s).replace(/^\d+\.\s*/, '')) + '</li>').join('') + '</ol>' : empty('실행 순서가 없다.');
  };
  R['when-versioning'] = function () {
    let h = '';
    if (ROAD.model_version_rule_ko) h += '<div class="callout prose"><span class="label">규칙</span>' + rich(ROAD.model_version_rule_ko) + '</div>';
    if ((EVAL.model_study || {}).versioning_ko) h += '<p class="prose" style="margin-top:12px">' + rich(EVAL.model_study.versioning_ko) + '</p>';
    const ms = MODELS.models || [];
    if (ms.length) h += table(['모델', '스냅샷·폐기 정책'], ms.map(m => ['<strong>' + esc(m.model_id) + '</strong><div class="xsmall faint">' + esc(m.provider) + '</div>', rich(m.snapshot)]), 't-mid');
    if ((MODELS.meta || {}).caution_ko) h += '<p class="small muted prose" style="margin-top:10px">' + rich(MODELS.meta.caution_ko) + '</p>';
    return h;
  };
  R['when-prior'] = function () {
    const by = {};
    PAPERS.forEach(p => { const y = (p.citation || {}).year || '연도 미상'; (by[y] = by[y] || []).push(p); });
    const years = Object.keys(by).sort();
    const ST_KO = { published: '출판', in_press: '인쇄 중', preprint: '프리프린트', proceedings: '학술대회 논문집' };
    return '<ol class="timeline">' + years.map(y => '<li><div class="tl-year">' + esc(y) + '</div>' + by[y].map(p => {
      const c = (p.w5h1 || {}).when || {};
      return '<div class="card" style="margin-top:8px"><div class="card-head">' + paperChip(p.id) + '<strong>' + esc(p.short) + '</strong>' + badge(ST_KO[(p.citation || {}).status] || (p.citation || {}).status || '', 'outline') + '</div>' +
        '<p style="margin:0">' + rich(c.headline) + '</p>' + (arr(c.items).length ? details('근거 ' + arr(c.items).length + '개', itemsList(c.items, p.id)) : '') + '</div>';
    }).join('') + '</li>').join('') + '</ol>';
  };

  // ---- WHERE ---------------------------------------------------------
  R['where-api'] = function () {
    const ms = MODELS.models || [];
    const byProv = {};
    ms.forEach(m => { (byProv[m.provider] = byProv[m.provider] || []).push(m); });
    let h = '<div class="grid grid-2">' + Object.keys(byProv).map(pv => '<div class="card"><p class="card-title">' + esc(pv) + '</p>' +
      byProv[pv].map(m => '<div style="margin-top:6px"><code>' + esc(m.model_id) + '</code> ' + badge(m.include, String(m.include).indexOf('핵심') === 0 ? 'b-blue' : 'b-gray') +
        ul(arr(m.docs).map(u => safeUrl(u) ? '<a class="small" href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(u) + '</a>' : esc(u)), 'small') + '</div>').join('') + '</div>').join('') + '</div>';
    const ms2 = EVAL.model_study || {};
    const env = (MODELS.design_constraints_ko || []).filter(d => /유료|한도|QPM|Tier|무료|배치/.test(d));
    h += '<h3 class="sub-h">호출 환경 규칙</h3><ul class="prose">' +
      (ms2.presentation_ko ? '<li>' + rich(ms2.presentation_ko) + '</li>' : '') + env.map(d => '<li>' + rich(d) + '</li>').join('') + '</ul>';
    h += '<p class="xsmall faint prose">제공사별 엔드포인트·요청 한도의 상세 표는 <code>models.json</code>에 따로 없다. 위 공식 문서 링크(조사일 ' + esc(((MODELS.meta || {}).date) || '') + ')와 <code>content/_research/models_raw.md</code>를 본다.</p>';
    return h;
  };
  R['where-platform'] = function () {
    const hs = EVAL.human_study || {};
    return '<div class="card">' + kv([['실험 플랫폼', rich(hs.platform_ko)], ['연구윤리(IRB)', rich(hs.ethics_ko)], ['연습 문항', rich(hs.practice_ko)]]) + '</div>' +
      (REF_BY_KEY.Zehr2018 ? '<p class="small muted" style="margin-top:8px">PCIbex 참고문헌 ' + refChip(REF_BY_KEY.Zehr2018) + '</p>' : '');
  };
  R['where-prereg'] = function () {
    const an = EVAL.analysis || {};
    const ph = (ROAD.phases || []).filter(p => /OSF|사전등록/.test(p.what_ko || ''));
    const steps = (EVAL.order_of_execution || []).filter(s => /사전등록/.test(s));
    return '<div class="callout prose"><span class="label">무엇을</span>' + rich(an.preregistration || '—') + '</div>' +
      (ph.length ? '<h3 class="sub-h">언제</h3><ul class="prose">' + ph.map(p => '<li><a class="chip" href="#phase-' + esc(p.id) + '">' + esc(p.id) + '</a> ' + esc(p.weeks) + ' — ' + rich(p.what_ko) + '</li>').join('') + '</ul>' : '') +
      (steps.length ? '<p class="small muted">실행 순서에서: ' + steps.map(rich).join(' / ') + '</p>' : '');
  };
  R['where-publication'] = function () {
    const pp = IMP.publication_plan || [];
    return pp.length ? '<div class="grid grid-3">' + pp.map(p => '<article class="card"><p class="card-title">' + esc(p.paper) + '</p>' +
      kv([['내용', rich(p.content_ko)], ['후보', rich(p.venue_candidates_ko)], ['이유', rich(p.why_ko)]]) + '</article>').join('') + '</div>' +
      '<p class="small muted" style="margin-top:8px">일정은 <a href="#phase-R9">로드맵 R9</a>.</p>' : empty('투고 계획이 없다.');
  };
  R['where-materials'] = function () {
    return '<div class="cards">' + PAPERS.map(p => {
      const om = arr(p.open_materials);
      return '<article class="card"><div class="card-head">' + paperChip(p.id) + '<strong>' + esc(p.short) + '</strong>' + badge(om.filter(o => o.url).length + '개 공개 위치', om.some(o => o.url) ? 'b-green' : 'b-gray') + '</div>' +
        '<p class="small muted">' + rich(((p.w5h1 || {}).where || {}).headline) + '</p>' +
        (om.length ? '<ul class="items">' + om.map(o => '<li>' + rich(o.what) + (safeUrl(o.url) ? '<div><a class="small" href="' + esc(o.url) + '" target="_blank" rel="noopener">' + esc(o.url) + '</a></div>' : '<div class="xsmall faint">URL 없음</div>') + '</li>').join('') + '</ul>' : '<p class="small faint">공개 자료 없음</p>') +
        '</article>';
    }).join('') + '</div>';
  };

  // ---- HOW -----------------------------------------------------------
  const anchors = a => a ? '<div class="anchors">' + Object.keys(a).map(k => '<span><strong class="tnum">' + esc(k) + '</strong> ' + esc(a[k]) + '</span>').join('') + '</div>' : '';
  R['how-measures'] = function () {
    const m = EVAL.measures || {};
    let h = (EVAL.meta || {}).principle_ko ? '<div class="callout prose"><span class="label">원칙</span>' + rich(EVAL.meta.principle_ko) + '</div>' : '';
    h += '<div class="grid grid-2" style="margin-top:12px">';
    if (m.acceptability) {
      const a = m.acceptability;
      h += '<article class="card"><div class="card-head"><strong>수용성</strong>' + badge(a.scale, 'outline') + '</div><p class="q">“' + esc(a.wording_ko) + '”</p>' + anchors(a.anchors_ko) +
        (a.note_ko ? '<p class="small muted" style="margin-top:8px">' + rich(a.note_ko) + '</p>' : '') + '</article>';
    }
    if (m.politeness) {
      const p = m.politeness;
      const w = isObj(p.wording_ko) ? Object.keys(p.wording_ko).map(k => '<li>' + expChip(k) + ' “' + esc(p.wording_ko[k]) + '”</li>').join('') : '<li>“' + esc(p.wording_ko) + '”</li>';
      h += '<article class="card"><div class="card-head"><strong>공손성</strong>' + badge(p.scale, 'outline') + '</div><ul class="plain">' + w + '</ul>' + anchors(p.anchors_ko) +
        (p.why_ko ? '<p class="small muted" style="margin-top:8px">' + rich(p.why_ko) + '</p>' : '') + '</article>';
    }
    h += '</div>';
    if (m.comprehension) {
      const c = m.comprehension;
      h += '<article class="card" style="margin-top:12px"><div class="card-head"><strong>이해 문항</strong>' + badge(c.format, 'outline') + '</div>' +
        kv(Object.keys(c.per_experiment || {}).map(k => [k, rich(c.per_experiment[k])]).concat([['선택지 순서', rich(c.option_order)]])) + '</article>';
    }
    if (m.reason_coding_model_only) {
      const r = m.reason_coding_model_only;
      h += '<article class="card" style="margin-top:12px"><div class="card-head"><strong>이유 코딩</strong>' + badge('모델 전용', 'b-teal') + chips(arr(r.applies_to).map(expChip)) + '</div><p class="small" style="margin:0">' + rich(r.procedure_ko) + '</p></article>';
    }
    return h;
  };
  R['how-prompt'] = function () {
    const ms = EVAL.model_study || {};
    const of = ms.output_format || {};
    const sm = ms.sampling || {};
    return '<p class="prose">' + rich(ms.presentation_ko) + '</p>' +
      '<h3 class="sub-h">시스템 프롬프트</h3><pre><code>' + esc(ms.system_prompt_ko) + '</code></pre>' +
      (ms.system_prompt_note_ko ? '<p class="small muted prose">' + rich(ms.system_prompt_note_ko) + '</p>' : '') +
      '<h3 class="sub-h">사용자 프롬프트 템플릿 <span class="hint">중괄호는 자극·문구로 채워진다</span></h3><pre><code>' + esc(ms.user_prompt_template_ko) + '</code></pre>' +
      '<div class="grid grid-2" style="margin-top:12px"><div class="card"><span class="label">출력 형식</span><p class="small">' + rich(of.type) + '</p>' +
      kv(Object.keys(of.schema || {}).map(k => [k, '<code>' + esc(of.schema[k]) + '</code>'])) + '</div>' +
      '<div class="card"><span class="label">표집</span>' + kv([['주 조건', rich(sm.primary_ko)], ['민감도', rich(sm.sensitivity_ko)], ['추론 모델', rich(sm.reasoning_models_ko)]]) + '</div></div>';
  };
  R['how-controls'] = function () {
    const hs = EVAL.human_study || {};
    let h = '<div class="grid grid-2">' + EXPS.map(e => '<div class="card"><div class="card-head">' + expChip(e.id) + '<span class="small muted">' + esc(bodyOf(e.title_ko)) + '</span></div>' + ul(arr(e.controls).map(rich)) + '</div>').join('') + '</div>';
    // Latin square illustration from E1 data (sets 01–04)
    const ls = STIM.E1 ? STIM.E1.rows : null;
    if (ls) {
      const sets = uniq(ls.map(r => r.set_id)).sort().slice(0, 4);
      const conds = uniq(ls.map(r => r.cond)).sort();
      h += '<h3 class="sub-h">라틴 방격 <span class="hint">E1 세트 01–04의 실제 목록 배정 — 각 목록은 세트마다 조건 하나만 본다</span></h3>' +
        table(['세트'].concat(conds.map(c => '조건 ' + esc(c))), sets.map(s => ['세트 ' + esc(s)].concat(conds.map(c => {
          const r = ls.find(x => x.set_id === s && x.cond === c);
          return r && r.list ? '목록 <strong>' + esc(r.list) + '</strong>' : '—';
        }))), 't-mid ls');
    }
    h += '<h3 class="sub-h">인간 세션의 통제</h3><div class="card">' + kv([['채움 문장', rich(hs.fillers_ko)], ['주의 점검', rich(hs.attention_checks_ko)], ['연습 문항', rich(hs.practice_ko)]]) + '</div>';
    const ms = EVAL.model_study || {};
    h += '<h3 class="sub-h">모델 호출의 통제</h3><div class="card">' + kv([['단독 제시', rich(ms.presentation_ko)], ['호출 순서', rich(ms.order_ko)], ['선택지 순서', rich(((EVAL.measures || {}).comprehension || {}).option_order)]]) + '</div>';
    return h;
  };
  R['how-analysis'] = function () {
    const an = EVAL.analysis || {};
    const L = { coding: '코딩', rating_model: '평정 모형(인간)', model_rating_model: '평정 모형(모델)', human_model_comparison: '인간–모델 비교', comprehension_model: '이해 문항 모형', equivalence_E3: 'E3 동등성 검정', multiplicity: '다중 비교', preregistration: '사전등록' };
    let h = '<div class="card">' + kv(Object.keys(L).filter(k => an[k]).map(k => [L[k], rich(an[k])])) + '</div>';
    if (arr(an.alignment_metrics).length) h += '<h3 class="sub-h">인간–모델 정렬 지표</h3><ol class="prose">' + an.alignment_metrics.map(x => '<li>' + rich(x) + '</li>').join('') + '</ol>';
    const inter = EXPS.filter(e => (e.predictions || {}).interaction_ko);
    if (inter.length) h += '<h3 class="sub-h">실험별 핵심 대비</h3><ul class="items card">' + inter.map(e => '<li>' + expChip(e.id) + ' ' + rich(e.predictions.interaction_ko) + '</li>').join('') + '</ul>';
    const meth = REFS.filter(r => r.group === '방법론');
    if (meth.length) h += '<h3 class="sub-h">방법론 참고문헌</h3><ul class="items card">' + meth.map(r => '<li>' + refChip(r) + ' ' + esc(r.note || '') + ' <span class="xsmall faint">' + esc(String(r.apa || '').split('(')[0].trim()) + '</span></li>').join('') + '</ul>';
    return h;
  };
  R['how-failure'] = function () {
    const ms = EVAL.model_study || {};
    return '<div class="callout prose"><span class="label">실패 처리</span>' + rich(ms.failure_handling_ko || '—') + '</div>' +
      '<h3 class="sub-h">로그 필드 <span class="hint">' + arr(ms.logging_fields).length + '개 — 모든 호출에 기록</span></h3><div class="chips">' + arr(ms.logging_fields).map(f => '<code>' + esc(f) + '</code>').join('') + '</div>';
  };

  // ---- PAPER SHELF -----------------------------------------------------
  R['shelf-list'] = function () {
    const groups = ['core', 'adjacent', 'subdata'];
    const others = PAPERS.filter(p => groups.indexOf(p.role) < 0);
    return groups.concat(others.length ? ['other'] : []).map(g => {
      const ps = g === 'other' ? others : PAPERS.filter(p => p.role === g);
      if (!ps.length) return '';
      return '<p class="shelf-group">' + esc(g === 'other' ? '기타' : ROLE[g][0]) + ' ' + ps.length + '</p>' + ps.map(p =>
        '<a class="shelf-item" href="#paper-' + esc(p.id) + '" data-pid="' + esc(p.id) + '" aria-current="false"><span class="si-id">' + esc(p.id) + '</span>' +
        '<span class="si-short">' + esc(p.short) + '</span><span class="si-badges">' + verBadge((p.verification || {}).status) + '</span></a>').join('');
    }).join('');
  };
  const paperDone = {};
  function selectPaper(pid) {
    if (!pid || !PAPER[pid]) return;
    currentPaper = pid;
    renderPanel('papers');
    document.querySelectorAll('.shelf-item').forEach(a => {
      const on = a.dataset.pid === pid;
      a.setAttribute('aria-current', String(on));
      // narrow screens: bring the chosen paper into view inside the horizontal strip (after layout)
      if (on) requestAnimationFrame(() => {
        const strip = a.parentElement;
        if (strip && strip.scrollWidth > strip.clientWidth + 4 && getComputedStyle(strip).display === 'flex') {
          strip.scrollLeft = Math.max(0, a.offsetLeft - strip.offsetLeft - 8);
        }
      });
    });
    document.querySelectorAll('article.paper').forEach(a => {
      const on = a.dataset.paper === pid;
      if (on && !paperDone[pid]) {
        try { a.innerHTML = paperHTML(PAPER[pid]); } catch (e) { a.innerHTML = '<p class="empty">이 논문을 그리지 못했다: ' + esc(e && e.message) + '</p>'; }
        paperDone[pid] = true;
      }
      a.hidden = !on;
    });
  }
  const KIND_S = { claim: ['주장', 'b-blue'], hypothesis: ['가설', 'b-violet'], result: ['결과', 'b-green'], method: ['방법', 'b-gray'], limitation: ['한계', 'b-red'], future_work: ['후속 과제', 'b-amber'] };
  const MOVE = { background: ['배경', 'b-gray'], gap: ['공백', 'b-amber'], claim: ['주장', 'b-blue'], method: ['방법', 'b-gray'], evidence: ['근거', 'b-green'], interpretation: ['해석', 'b-violet'], limitation: ['한계', 'b-red'], future_work: ['후속 과제', 'b-amber'] };
  const AXIS = { lineage: ['인용 계보', 'b-gray'], theory: ['이론적 입장', 'b-violet'], model_generation: ['모델 세대', 'b-teal'], agreement: ['합의', 'b-green'], conflict: ['불일치', 'b-red'], field: ['분야·독자', 'b-blue'] };
  const mapBadge = (M, k) => badge((M[k] || [k])[0], (M[k] || [0, 'b-gray'])[1]);
  function filterBar(key, label, items, M, field) {
    const counts = {};
    items.forEach(x => { counts[x[field]] = (counts[x[field]] || 0) + 1; });
    const ks = Object.keys(counts);
    if (ks.length < 2) return '';
    return '<div class="seg kind-filter" role="group" aria-label="' + esc(label) + '"><button type="button" data-lf="' + key + '" data-v="all" aria-pressed="true">전체 ' + items.length + '</button>' +
      ks.map(k => '<button type="button" data-lf="' + key + '" data-v="' + esc(k) + '" aria-pressed="false">' + esc((M[k] || [k])[0]) + ' ' + counts[k] + '</button>').join('') + '</div>';
  }
  function layerPane(p, key) {
    const L = (p.layers || {})[key] || [];
    const pid = p.id;
    if (!L.length) return empty('이 층의 항목이 없다.');
    if (key === 'word') return '<div class="layer-list">' + L.map(w => '<div class="card"><p style="margin:0 0 4px"><span class="term">' + esc(w.term) + '</span><span class="gloss">' + esc(w.gloss_ko) + '</span>' + src(w.src, pid) + '</p>' +
      '<p style="margin:0">' + rich(w.definition) + '</p>' + (w.note ? '<p class="small muted" style="margin:6px 0 0">' + rich(w.note) + '</p>' : '') + '</div>').join('') + '</div>';
    if (key === 'sentence') return filterBar('sentence', '문장 종류', L, KIND_S, 'kind') + '<div class="layer-list">' + L.map(s => '<div class="card" data-lv="' + esc(s.kind) + '"><div class="card-head">' + mapBadge(KIND_S, s.kind) + src(s.src, pid) + '</div>' +
      (s.quote ? '<p class="quote">' + esc(s.quote) + '</p>' : '') + '<p style="margin:0">' + rich(s.paraphrase_ko) + '</p>' +
      (arr(s.numbers).length ? '<div class="chips" style="margin-top:6px">' + arr(s.numbers).map(n => '<span class="badge outline tnum">' + esc(n) + '</span>').join('') + '</div>' : '') + '</div>').join('') + '</div>';
    if (key === 'paragraph') return filterBar('paragraph', '논증 단계', L, MOVE, 'move') + '<div class="layer-list">' + L.map(s => '<div class="card" data-lv="' + esc(s.move) + '"><div class="card-head">' + mapBadge(MOVE, s.move) + '<span class="small muted">' + esc(s.section) + '</span>' + src(s.src, pid) + '</div>' +
      '<p style="margin:0">' + rich(s.summary_ko) + '</p></div>').join('') + '</div>';
    return filterBar('context', '맥락 축', L, AXIS, 'axis') + '<div class="layer-list">' + L.map(c => '<div class="card" data-lv="' + esc(c.axis) + '"><div class="card-head">' + mapBadge(AXIS, c.axis) + (arr(c.related).length ? chips(arr(c.related).map(paperChip)) : '') + src(c.src, pid) + '</div>' +
      '<p style="margin:0">' + rich(c.text_ko) + '</p></div>').join('') + '</div>';
  }
  function pblock(p, key, num, title, hint, body) {
    return '<section class="pblock" id="paper-' + esc(p.id) + '-' + key + '"><h3>' + (num ? '<span class="sec-num">' + num + '</span>' : '') + esc(title) + (hint ? ' <span class="hint">' + hint + '</span>' : '') + '</h3>' + body + '</section>';
  }
  function paperHTML(p) {
    const c = p.citation || {};
    const ref = REF_BY_KEY[p.id];
    const hooks = arr(p.successor_hooks);
    const used = hooks.filter(h => HOOK_USE[h.id]).length;
    const ST_KO = { published: '출판', in_press: '인쇄 중', preprint: '프리프린트', proceedings: '학술대회 논문집' };
    const blocks = [['bib', '서지'], ['w5h1', '6하원칙'], ['layers', '4층 분석'], ['design', '설계·예문'], ['numbers', '핵심 수치'], ['hooks', '계승 지점'], ['limits', '한계'], ['prior', '기존 분석 대조'], ['verify', '검증 기록']];
    let h = '<header class="paper-head"><div class="card-head"><span class="card-id">' + esc(p.id) + '</span>' + roleBadge(p.role) + verBadge((p.verification || {}).status) +
      (c.status ? badge(ST_KO[c.status] || c.status, 'outline') : '') + (ref ? refChip(ref) : '') + '</div>' +
      '<h2 class="paper-title">' + esc(p.title) + '</h2><p class="paper-title-ko">' + (p.title_ko && p.title_ko !== p.title ? esc(p.title_ko) + ' — ' : '') + '<strong>' + esc(p.short) + '</strong></p>' +
      '<p class="one-line">' + rich(p.one_line) + '</p>' +
      '<p class="small muted">계승 지점 ' + hooks.length + '개 중 <strong>' + used + '개</strong>가 공백·실험 설계에 쓰였다.</p>' +
      '<nav class="chips paper-nav" aria-label="논문 안 이동">' + blocks.map(b => '<a class="chip" href="#paper-' + esc(p.id) + '-' + b[0] + '">' + esc(b[1]) + '</a>').join('') + '</nav></header>';

    // ① bibliography
    const doi = c.doi ? 'https://doi.org/' + c.doi : '';
    h += pblock(p, 'bib', '①', '서지', '', '<div class="card">' + kv([
      ['APA', rich(c.apa)], ['발표처', rich(c.venue)], ['연도', esc(c.year)], ['게재 상태', esc(ST_KO[c.status] || c.status)],
      ['DOI', doi ? '<a href="' + esc(doi) + '" target="_blank" rel="noopener">' + esc(doi) + '</a>' : '<span class="faint">없음</span>'],
      ['원문 URL', safeUrl(c.url) ? '<a href="' + esc(c.url) + '" target="_blank" rel="noopener">' + esc(c.url) + '</a>' : '<span class="faint">없음</span>'],
      ['참고문헌', ref ? refChip(ref) + ' <span class="small muted">참고문헌 탭 항목</span>' : '<span class="faint">목록에 없음</span>'],
      ['서지 메모', c.bib_notes ? '<span class="small">' + rich(c.bib_notes) + '</span>' : '']]) + '</div>');

    // ② 5W1H
    const w = p.w5h1 || {};
    h += pblock(p, 'w5h1', '②', '6하원칙', '<button type="button" class="linkish" data-expand="w5">근거 모두 펼치기</button>', '<div class="w5h1">' + W5.map(x => {
      const cell = w[x[0]] || {};
      return '<div class="card w5-cell"><div><span class="w5-k">' + esc(x[1]) + '</span><span class="w5-en">' + esc(x[2]) + '</span></div><p class="w5-q">' + esc(x[3]) + '</p>' +
        '<p class="w5-head">' + rich(cell.headline || '—') + '</p>' + (arr(cell.items).length ? details('근거 ' + arr(cell.items).length + '개', itemsList(cell.items, p.id)) : '') + '</div>';
    }).join('') + '</div>');

    // ③ layers
    const L = p.layers || {};
    const LAY = [['word', '단어', '핵심 용어의 조작적 정의'], ['sentence', '문장', '가설·결과·방법 문장'], ['paragraph', '문단', '절별 논증 단계'], ['context', '맥락', '계보·이론·모델 세대']];
    h += pblock(p, 'layers', '③', '4층 분석', '단어 → 문장 → 문단 → 맥락',
      '<div class="sub-tabs" role="tablist" aria-label="분석 층">' + LAY.map((l, i) => '<button type="button" role="tab" class="sub-tab" data-layer="' + l[0] + '" aria-selected="' + (i === 0) + '" title="' + esc(l[2]) + '">' + esc(l[1]) + '<span class="cnt">' + arr(L[l[0]]).length + '</span></button>').join('') + '</div>' +
      LAY.map((l, i) => '<div class="layer-pane" data-layer-pane="' + l[0] + '"' + (i ? ' hidden' : '') + '>' + layerPane(p, l[0]) + '</div>').join(''));

    // design & examples (unnumbered support block)
    const d = p.design || {};
    h += pblock(p, 'design', '', '설계 요약과 자극 예문', '', details('실험 설계 요약', kv([
      ['현상', rich(d.phenomenon)], ['자극', rich(d.stimuli)], ['조건', val(d.conditions)], ['문항 수', rich(d.n_items)], ['측정', val(d.measures)],
      ['모델', val(d.models)], ['인간', rich(d.humans || '—')], ['통계', rich(d.stats)], ['요인설계', rich(d.is_factorial)]]), false, 'panel') +
      (arr(p.stimulus_examples).length ? details('논문이 제시한 자극 예문 ' + p.stimulus_examples.length + '개', '<div class="layer-list">' + p.stimulus_examples.map(x =>
        '<div class="card"><p class="stim-sent" style="margin-top:0">' + esc(x.ko) + '</p><p class="xsmall faint" style="margin:0 0 4px">' + esc(x.gloss) + '</p><p class="small" style="margin:0">' + rich(x.condition) + src(x.src, p.id) + '</p></div>').join('') + '</div>', false, 'panel') : ''));

    // ④ key numbers
    const kn = arr(p.key_numbers);
    h += pblock(p, 'numbers', '④', '핵심 수치', kn.length + '개 · 원문 표기 그대로', kn.length ? table(['무엇', '값', '쪽'], kn.map(k => {
      const v = String(k.value || '');
      const flag = (/\(재계산\)/.test(v) ? badge('재계산', 'b-amber') : '') + (/\(그림 판독\)/.test(v) ? badge('그림 판독', 'b-violet') : '');
      return [rich(k.what), '<strong class="tnum">' + esc(v.replace(/\s*\((재계산|그림 판독)\)/g, '')) + '</strong><span class="kn-flag">' + flag + '</span>', src(k.src)];
    }), 't-mid kn-table') : empty('핵심 수치 없음'));

    // ⑤ hooks
    h += pblock(p, 'hooks', '⑤', '계승 지점', hooks.length + '개 · 왼쪽 띠 색 = 종류', filterBar('hooks', '계승 지점 종류', hooks, KIND, 'kind') + '<div class="layer-list">' + hooks.map(hk => {
      const uses = HOOK_USE[hk.id] || [];
      return '<article class="card hook k-' + esc(hk.kind) + '" id="hook-' + esc(hk.id) + '" data-lv="' + esc(hk.kind) + '"><div class="card-head"><span class="card-id">' + esc(hk.id) + '</span>' + kindBadge(hk.kind) + src(hk.src, p.id) + '</div>' +
        '<p class="card-title" style="font-weight:600">' + rich(hk.hook_ko) + '</p>' +
        (hk.basis_ko ? details('근거', '<p class="small">' + rich(hk.basis_ko) + '</p>') : '') +
        (uses.length ? '<div class="used-by">이 지점을 쓰는 곳 ' + chips(uses.map(u => u.kind === 'gap' ? gapChip(u.id) : expChip(u.id))) + '</div>' : '<div class="used-by">아직 공백·실험에 연결되지 않음</div>') +
        '</article>';
    }).join('') + '</div>');

    // ⑥ limitations
    const lim = arr(p.limitations);
    const BY = { author: ['저자 명시', 'b-blue'], us: ['우리 판단', 'b-gray'] };
    h += pblock(p, 'limits', '⑥', '한계', lim.length + '개', filterBar('limits', '누가 밝혔나', lim, BY, 'stated_by') + '<ul class="items card">' + lim.map(l => '<li data-lv="' + esc(l.stated_by) + '">' + mapBadge(BY, l.stated_by) + ' ' + rich(l.text_ko) + src(l.src, p.id) + '</li>').join('') + '</ul>');

    // ⑦ prior analysis
    const pa = p.prior_analysis_check || {};
    const ag = arr(pa.agreements), ds = arr(pa.discrepancies);
    h += pblock(p, 'prior', '⑦', '기존 분석과의 대조', '기존 초안(2026-09-18) 대비', '<p class="small muted">대조한 자료: ' + rich(pa.source || '—') + '</p>' +
      '<div class="grid grid-2"><div class="card"><p class="col-h">일치 ' + ag.length + '</p>' + ul(ag.map(rich)) + '</div>' +
      '<div class="card disc"><p class="col-h">불일치·보완 ' + ds.length + '</p>' + ds.map(x => {
        if (!isObj(x)) return '<div class="d-item">' + rich(x) + '</div>';
        const oldV = x.old || x.prior, newV = x.new || x.paper;
        return '<div class="d-item"><p style="margin:0 0 4px"><strong>' + rich(x.item || '') + '</strong>' + src(x.basis_src, p.id) + '</p>' +
          (oldV ? '<p class="small old" style="margin:0"><span class="label">기존 분석</span>' + rich(oldV) + '</p>' : '') +
          (newV ? '<p class="small" style="margin:4px 0 0"><span class="label">원문 확인</span>' + rich(newV) + '</p>' : '') +
          (x.resolution ? '<p class="small" style="margin:4px 0 0"><span class="label">처리</span>' + rich(x.resolution) + '</p>' : '') + '</div>';
      }).join('') + '</div></div>');

    // ⑧ verification
    const v = p.verification || {};
    const notes = arr(v.notes);
    h += pblock(p, 'verify', '⑧', '검증 기록', '', '<div class="card"><div class="card-head">' + verBadge(v.status) + '<span class="small muted">검증자: ' + esc(v.by || '미지정') + '</span><span class="small muted">기록 ' + notes.length + '건</span></div>' +
      (notes.length ? details('정정·확인 내용 ' + notes.length + '건', '<ol class="small">' + notes.map(n => '<li>' + rich(n) + '</li>').join('') + '</ol>', notes.length <= 4) : '<p class="small faint" style="margin:0">기록 없음</p>') + '</div>');
    return h;
  }
  // shelf interactions: layer tabs, local filters, expand all
  document.addEventListener('click', function (ev) {
    const art = ev.target.closest('article.paper');
    if (!art) return;
    const lt = ev.target.closest('[data-layer]');
    if (lt) {
      art.querySelectorAll('[data-layer]').forEach(b => b.setAttribute('aria-selected', String(b === lt)));
      art.querySelectorAll('[data-layer-pane]').forEach(pn => { pn.hidden = pn.dataset.layerPane !== lt.dataset.layer; });
      return;
    }
    const lf = ev.target.closest('[data-lf]');
    if (lf) {
      const bar = lf.parentElement;
      bar.querySelectorAll('[data-lf]').forEach(b => b.setAttribute('aria-pressed', String(b === lf)));
      const scope = bar.parentElement;
      scope.querySelectorAll('[data-lv]').forEach(x => { x.hidden = !(lf.dataset.v === 'all' || x.dataset.lv === lf.dataset.v); });
      return;
    }
    const ex = ev.target.closest('[data-expand]');
    if (ex) {
      const ds = art.querySelectorAll('.w5h1 details');
      const open = !Array.prototype.every.call(ds, d => d.open);
      ds.forEach(d => { d.open = open; });
      ex.textContent = open ? '근거 모두 접기' : '근거 모두 펼치기';
    }
  });

  // ---- TRACK -----------------------------------------------------------
  const ST_ICON = { '☑': ['st-done', '완료'], '◐': ['st-doing', '진행·중단'], '☐': ['st-todo', '대기'], '✕': ['st-cancel', '취소'] };
  function mdTable(t, opts) {
    opts = opts || {};
    const hd = t.headers || [];
    const si = hd.indexOf('상태');
    const rows = (t.rows || []).map(r => r.map((c, i) => {
      if (i === si) {
        const ic = String(c).trim().slice(0, 1);
        const s = ST_ICON[ic];
        return s ? '<span class="st-icon ' + s[0] + '" title="' + esc(s[1]) + '" aria-label="' + esc(s[1]) + '">' + esc(ic) + '</span>' : md(c);
      }
      return md(c);
    }));
    const dataRows = (t.rows || []);
    return '<div class="table-wrap" tabindex="0"><table class="tracker-table ' + (opts.cls || 't-wide') + '"><thead><tr>' + hd.map(h => '<th scope="col">' + md(h) + '</th>').join('') + '</tr></thead><tbody>' +
      rows.map((r, i) => '<tr' + (si >= 0 ? ' data-st="' + esc(String(dataRows[i][si] || '').trim().slice(0, 1)) + '"' : '') + '>' + r.map(c => '<td>' + c + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>';
  }
  R['track-ledger'] = function () {
    const t = TRACK.ledger || {};
    if (!(t.rows || []).length) return empty('인수인계서 §4 표를 찾지 못했다.');
    const cnt = TRACK.ledger_counts || {};
    const total = t.rows.length;
    const done = cnt['☑'] || 0;
    let h = '';
    if (TRACK.status_title) h += '<div class="callout prose small"><span class="label">' + md(TRACK.status_title.replace(/^\d+\.\s*/, '')) + '</span>' + ul(arr(TRACK.status_bullets).map(md)) + '</div>';
    h += '<div class="progress" style="margin-top:14px"><div class="progress-bar"><span style="width:' + (total ? Math.round(done / total * 100) : 0) + '%"></span></div>' +
      '<div class="seg" role="group" aria-label="상태 필터"><button type="button" data-tf="all" aria-pressed="true">전체 ' + total + '</button>' +
      Object.keys(ST_ICON).filter(k => cnt[k]).map(k => '<button type="button" data-tf="' + k + '" aria-pressed="false">' + k + ' ' + ST_ICON[k][1] + ' ' + cnt[k] + '</button>').join('') + '</div></div>';
    if (TRACK.ledger_legend) h += '<p class="xsmall faint" style="margin:6px 0 10px">상태: ' + esc(TRACK.ledger_legend) + '</p>';
    h += mdTable(t);
    if (((TRACK.risks || {}).rows || []).length) h += details('미해결·위험 <span class="hint">인수인계서 §8 · ' + TRACK.risks.rows.length + '건</span>', mdTable(TRACK.risks, { cls: 't-mid' }), false, 'panel');
    return h;
  };
  R['track-ledger'].after = function (el) {
    el.addEventListener('click', function (ev) {
      const b = ev.target.closest('[data-tf]');
      if (!b) return;
      el.querySelectorAll('[data-tf]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
      el.querySelectorAll('.tracker-table tr[data-st]').forEach(tr => { tr.hidden = !(b.dataset.tf === 'all' || tr.dataset.st === b.dataset.tf); });
    });
  };
  R['track-decisions'] = function () {
    const t = TRACK.decisions || {};
    if (!(t.rows || []).length) return empty('인수인계서 §6 표를 찾지 못했다.');
    const num = s => Number((String(s).match(/\d+/) || [0])[0]);
    const sorted = { headers: t.headers, rows: t.rows.slice().sort((a, b) => num(a[0]) - num(b[0])) };
    return '<p class="xsmall faint">ID 순으로 정렬했다.</p>' + mdTable(sorted);
  };
  R['track-verification'] = function () {
    const t = TRACK.verification || {};
    let h = (t.rows || []).length ? mdTable(t) : empty('인수인계서 §7 표를 찾지 못했다.');
    const w = META.warnings || [];
    h += details('빌드 점검 결과 <span class="hint">' + (w.length ? w.length + '건 — 데이터는 고치지 않고 보고만 한다' : '문제 없음') + '</span>',
      w.length ? ul(w.map(esc), 'small') : '<p class="small">교차 참조·파일 점검에서 문제를 찾지 못했다.</p>', false, 'panel');
    h += '<p class="xsmall faint" style="margin-top:10px">빌드 ' + esc(META.built_at || '') + '</p>';
    return h;
  };

  // ---- REFERENCES ------------------------------------------------------
  R['refs-list'] = function () {
    const meta = (D.references || {}).meta || {};
    const groups = uniq(REFS.map(r => r.group || '기타'));
    const verified = REFS.filter(r => r.verified === true).length;
    let h = '<p class="small muted prose">' + esc(meta.style || '') + (meta.verification ? ' · ' + rich(meta.verification) : '') + '</p>' +
      '<p class="small"><strong class="tnum">' + REFS.length + '</strong>건 · 연결 확인 ' + verified + '건 · DOI ' + REFS.filter(r => r.doi).length + '건</p>';
    h += groups.map(g => '<section class="refs-group"><h2 class="sub-h" style="font-size:1.15rem">' + esc(g) + ' <span class="sec-count">' + REFS.filter(r => (r.group || '기타') === g).length + '</span></h2><ol class="refs">' +
      REFS.filter(r => (r.group || '기타') === g).map(r => {
        const doi = r.doi ? 'https://doi.org/' + r.doi : '';
        const link = safeUrl(r.url) || doi;
        const vb = r.verified === true ? badge('연결 확인' + (r.checked_on ? ' ' + r.checked_on : ''), 'b-green') : r.verified === false ? badge('연결 실패', 'b-red') : badge('연결 미확인', 'b-gray');
        return '<li id="ref-' + esc(r.n) + '"><span class="ref-n">[' + esc(r.n) + ']</span><div><p class="ref-apa">' + rich(r.apa) + '</p><div class="chips">' +
          (doi ? '<a class="chip" href="' + esc(doi) + '" target="_blank" rel="noopener">DOI ' + esc(r.doi) + '</a>' : '') +
          (!doi && link ? '<a class="chip" href="' + esc(link) + '" target="_blank" rel="noopener">원문 URL</a>' : '') +
          (!link ? badge('URL 없음', 'b-amber') : '') + vb +
          (PAPER[r.key] ? '<a class="chip" href="#paper-' + esc(r.key) + '">논문 서가 ' + esc(r.key) + ' →</a>' : '') + '</div>' +
          (r.note ? '<p class="xsmall faint" style="margin:6px 0 0">' + rich(r.note) + '</p>' : '') + '</div></li>';
      }).join('') + '</ol></section>').join('');
    return h;
  };

  // ------------------------------------------------------------- tabs
  const rendered = {};
  function renderSection(el) {
    const id = el.getAttribute('data-render');
    if (rendered[id]) return;
    rendered[id] = true;
    const fn = R[id];
    try {
      el.innerHTML = fn ? fn(el) : empty('준비 중');
      if (fn && fn.after) fn.after(el);
    } catch (e) {
      el.innerHTML = '<p class="empty">이 섹션을 그리지 못했다: ' + esc(e && e.message) + '</p>';
      if (window.console) console.warn('render failed', id, e);
    }
  }
  function renderPanel(tab) {
    const panel = document.getElementById('panel-' + tab);
    if (!panel) return;
    const intro = panel.querySelector('[data-intro]');
    if (intro && !intro.dataset.done) { intro.innerHTML = INTRO[tab] || ''; intro.dataset.done = '1'; }
    panel.querySelectorAll('[data-render]').forEach(renderSection);
    if (tab === 'papers' && !currentPaper) selectPaper(PAPERS.length ? PAPERS[0].id : null);
  }
  function renderAll() { TAB_IDS.forEach(renderPanel); }

  let currentTab = null;
  function showTab(id) {
    if (TAB_IDS.indexOf(id) < 0) id = 'home';
    if (currentTab === id) return;
    currentTab = id;
    document.querySelectorAll('.tab').forEach(b => {
      const on = b.dataset.tab === id;
      b.setAttribute('aria-selected', on ? 'true' : 'false');
      b.tabIndex = on ? 0 : -1;
    });
    document.querySelectorAll('.tab-panel').forEach(p => { p.hidden = p.dataset.tab !== id; });
    renderPanel(id);
    const btn = document.getElementById('tab-' + id);
    const bar = btn && btn.parentElement;
    if (bar && bar.scrollWidth > bar.clientWidth) bar.scrollLeft = btn.offsetLeft - (bar.clientWidth - btn.offsetWidth) / 2;
    const t = (META.tabs || []).find(x => x.id === id);
    document.title = (t && id !== 'home' ? t.label + ' — ' : '') + '경어법 LLM 연구 설계';
    observeToc(id);
  }

  function scrollToEl(el) {
    if (!el) return;
    if (el.hidden) el.hidden = false;
    let p = el.parentElement;
    while (p) { if (p.tagName === 'DETAILS') p.open = true; p = p.parentElement; }
    requestAnimationFrame(() => {
      el.scrollIntoView({ block: 'start' });
      // highlight small targets (a card, a hook, a reference); whole sections just scroll
      if (!el.matches('.sec, .tab-panel, article.paper, .pblock, .exp')) {
        el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash');
      }
    });
  }

  // paper shelf hooks (filled in by the shelf module)
  let currentPaper = null;

  function route() {
    const id = decodeURIComponent(location.hash.replace(/^#/, ''));
    if (!id) { showTab('home'); return; }
    if (TAB_IDS.indexOf(id) >= 0) { showTab(id); window.scrollTo(0, 0); return; }
    let m = id.match(/^paper-(P\d\d)(?:-[a-z0-9]+)?$/) || id.match(/^hook-(P\d\d)-H\d+$/);
    if (m && PAPER[m[1]]) {
      selectPaper(m[1]); showTab('papers');
      scrollToEl(document.getElementById(id));
      return;
    }
    m = id.match(/^exp-(E\d)$/);
    if (m && EXP[m[1]]) { selectExp(m[1]); showTab('what'); scrollToEl(document.getElementById('what-experiments')); return; }
    let el = document.getElementById(id);
    if (!el || !el.closest('.tab-panel')) { renderAll(); el = document.getElementById(id); }
    if (el) {
      const panel = el.closest('.tab-panel');
      if (panel) showTab(panel.dataset.tab);
      scrollToEl(el);
    } else {
      showTab('home');
    }
  }

  // in-tab TOC highlight
  let tocObserver = null;
  function observeToc(tab) {
    if (tocObserver) tocObserver.disconnect();
    const panel = document.getElementById('panel-' + tab);
    if (!panel || !('IntersectionObserver' in window)) return;
    const links = panel.querySelectorAll('.toc a[data-toc]');
    if (!links.length) return;
    tocObserver = new IntersectionObserver(entries => {
      entries.forEach(en => {
        if (en.isIntersecting) links.forEach(a => a.classList.toggle('active', a.dataset.toc === en.target.id));
      });
    }, { rootMargin: '-15% 0px -70% 0px' });
    panel.querySelectorAll('.sec').forEach(s => tocObserver.observe(s));
  }

  // ------------------------------------------------------------- theme
  const THEME_KEY = 'khl-dashboard-theme';
  function applyTheme(mode) {
    const root = document.documentElement;
    if (mode === 'light' || mode === 'dark') root.setAttribute('data-theme', mode); else root.removeAttribute('data-theme');
    document.querySelectorAll('[data-theme-set]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.themeSet === (mode || 'system'))));
    try {
      if (mode === 'light' || mode === 'dark') window.localStorage.setItem(THEME_KEY, mode);
      else window.localStorage.removeItem(THEME_KEY);
    } catch (e) { /* storage blocked: theme still applies for this visit */ }
  }

  // ------------------------------------------------------------- events
  document.addEventListener('click', function (ev) {
    const t = ev.target.closest('[data-theme-set]');
    if (t) { applyTheme(t.dataset.themeSet); return; }
    const tab = ev.target.closest('.tab[data-tab]');
    if (tab) {
      ev.preventDefault();
      if (location.hash === '#' + tab.dataset.tab) route(); else location.hash = tab.dataset.tab;
      return;
    }
    const a = ev.target.closest('a[href^="#"]');
    if (a && !ev.defaultPrevented && !ev.metaKey && !ev.ctrlKey && !ev.shiftKey) {
      const h = a.getAttribute('href');
      if (h === location.hash) { ev.preventDefault(); route(); }
    }
  });
  const tablist = document.querySelector('.tabs[role="tablist"]');
  if (tablist) tablist.addEventListener('keydown', function (ev) {
    if (ev.key !== 'ArrowRight' && ev.key !== 'ArrowLeft' && ev.key !== 'Home' && ev.key !== 'End') return;
    const tabs = Array.prototype.slice.call(tablist.querySelectorAll('.tab'));
    let i = tabs.indexOf(document.activeElement);
    if (i < 0) return;
    ev.preventDefault();
    i = ev.key === 'Home' ? 0 : ev.key === 'End' ? tabs.length - 1 : (i + (ev.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    tabs[i].focus();
    location.hash = tabs[i].dataset.tab;
  });
  window.addEventListener('hashchange', route);

  // ------------------------------------------------------------- init
  applyTheme(document.documentElement.getAttribute('data-theme') || 'system');
  route();
})();
