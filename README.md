# 한국어 경어법 × LLM — 후속 연구 설계

선행 논문 10편을 단어·문장·문단·맥락 단위로 분석하고, 그 논문들을 계승하는 **2×2 요인설계 후속 연구**를 설계한 자료다. 평가는 7점 Likert와 이해 문항, 실험 환경은 상용 LLM API를 전제한다.

## 먼저 볼 것

| 목적 | 파일 |
|---|---|
| 지금 어디까지 됐고 다음에 무엇을 하나 | [`인수인계서.md`](인수인계서.md) |
| 연구 설계를 한눈에 (6하원칙 탭) | `dashboard/index.html` (배포: https://korean-honorific-llm.vercel.app/) |
| A4 2쪽 요약 ① 6하원칙 순 | `dashboard/summary-2p.html` (배포: https://korean-honorific-llm.vercel.app/summary) |
| A4 2쪽 요약 ② 의뢰 5개 항목별 | `dashboard/summary-requirements.html` (배포: https://korean-honorific-llm.vercel.app/summary2) |
| 무엇을 왜 이렇게 만들었나 | [`docs/00_전략서.md`](docs/00_전략서.md) |
| 작업 절차 | [`docs/01_실행계획.md`](docs/01_실행계획.md) |

## 구조

```
content/    단일 원천 데이터 — 논문 카드, 횡단 분석, 실험, 자극, 평가, 모델, 함의, 참고문헌
build/      content/ → 대시보드·요약 HTML 빌드 스크립트, 검사 스크립트, 테스트
dashboard/  index.html(대시보드), summary-2p.html(A4 2쪽 요약) — Vercel은 이 폴더만 배포(vercel.json)
docs/       전략서 · 실행계획 · 스키마 · 검증 기록
```

`papers/`(논문 원문·추출 텍스트)와 `reference/`(이전 초안)는 저작권과 참고 전용이라는 이유로 저장소에 올리지 않는다.
