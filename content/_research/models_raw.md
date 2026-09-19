# 상용 API 모델 조사 원자료 (P6-01a)

- 조사일: 2026-09-19
- 조사 방법: 각 회사의 공식 문서(모델 개요·가격·API 레퍼런스·폐기 정책·요청 한도 페이지)를 WebFetch/WebSearch로 직접 열어 확인했다. 표의 모든 값은 아래 "출처 URL" 목록에 적은 페이지에서 확인한 것이며, 확인일은 모두 2026-09-19다. 공식 문서에서 확인하지 못한 값은 "미확인"으로 적었다. 가격은 원문 통화를 그대로 적었고, 단위는 별도 표기가 없으면 100만 토큰(MTok)당이다. 제3자 블로그·뉴스는 근거로 쓰지 않았고, 부득이하게 참고한 경우 그 사실을 적었다.
- 실험 맥락: 7점 Likert 평정 + 4지선다 이해 문항, 상용 API 종량제, GPU 없음, 스크립트로 수천 회 호출.

---

## 1. Anthropic (Claude)

| 모델 ID | 가격 (USD/MTok) | temperature · seed · JSON · logprobs · thinking | 스냅샷 · 폐기 정책 | 한국어 근거 |
|---|---|---|---|---|
| `claude-fable-5-1` | 입력 $10 / 출력 $50. 배치 50% 할인. 캐시 읽기 $0.25(기본 입력가의 2.5%) | temperature: 기본값(1.0) 외 값은 400 오류(4.7 이후 모델 공통). seed: 파라미터 없음. JSON: 구조화 출력 GA(`output_config.format`) 지원. logprobs: 파라미터 없음. thinking: **항상 켜짐(adaptive)**, `thinking: {type:"disabled"}`는 어떤 effort에서도 400 오류. effort `low`~`max` 조절만 가능 | 날짜 없는 ID지만 "모든 Claude 모델 ID는 고정 스냅샷"이라고 명시. Active, 폐기 "2027-09-01 이전은 아님". 30일 데이터 보존 필수(ZDR 불가) | 모델별 한국어 수치 미공개(공식 다국어 표는 Sonnet 4.5·Haiku 4.5만) |
| `claude-opus-5` | 입력 $5 / 출력 $25. 배치 50% 할인. 캐시 쓰기 5분 $6.25·1시간 $10, 캐시 읽기 $0.50 | temperature: 기본값 외 400 오류. seed: 없음. JSON: GA 지원. logprobs: 없음. thinking: **기본 켜짐(adaptive)**, effort `high` 이하에서만 `disabled` 허용(`xhigh`/`max`+disabled는 400). assistant prefill은 400 오류 | 고정 스냅샷(날짜 없는 ID). 출시 2026-07-24, 폐기 "2027-07-24 이전은 아님" | 모델별 한국어 수치 미공개 |
| `claude-sonnet-5` | 입력 $2 / 출력 $10. 배치 50% 할인, 캐시 읽기 기본 입력가의 10% | Opus 5와 API 표면 동일: temperature 기본값 외 400, seed·logprobs 없음, JSON GA, thinking 기본 켜짐·`high` 이하에서 disabled 가능, prefill 400 | 고정 스냅샷. 폐기 "2027-06-30 이전은 아님" | 모델별 한국어 수치 미공개 |
| `claude-haiku-4-5-20251001` (별칭 `claude-haiku-4-5`) | 입력 $1 / 출력 $5. 배치 50% 할인, 캐시 읽기 10% | temperature: **0.0~1.0 설정 가능**(4.7 이전 세대라 400 대상 아님). 단, Python SDK v1.0 이상은 `temperature` 인자를 아예 제거해 TypeError → 원시 HTTP나 `extra_body`로 보내야 함(추정: `extra_body` 방법은 공식 문서에서 미확인). seed·logprobs 없음. JSON GA 지원. thinking: 수동 extended thinking(`budget_tokens`) 방식, 기본 꺼짐. effort 미지원 | 날짜 박힌 스냅샷 ID. **폐기 "2026-10-15 이전은 아님"** — 조사일 기준 한 달 이내에 폐기 공지 가능 | 공식 다국어 표: 한국어 = 영어 대비 **93.3%**(extended thinking 켬, 인간 번역 MMLU, 0-shot CoT) |

공통 사항
- 폐기 통지: 공개 출시 모델은 폐기 최소 60일 전에 이메일·문서로 통지. 폐기 후 요청은 실패.
- 요청 한도(Start 등급, 신규 조직은 그보다 낮은 Evaluation 등급에서 시작 가능): Opus 5·Sonnet 5·Haiku 4.5 각 1,000 RPM / 2,000,000 ITPM / 400,000 OTPM, Fable 5.x 1,000 RPM / 500,000 ITPM / 100,000 OTPM. 월 지출 상한 Start $500, Build $1,000, Scale $200,000. 캐시 읽기 토큰은 ITPM에 산입되지 않음.
- Message Batches API: 배치당 최대 100,000 요청, 처리 대기열 Start 200,000. 가격 50% 할인.
- 구조화 출력: GA, `output_config.format`. JSON Schema의 `enum`(문자열·숫자) 지원, `minimum`/`maximum` 등 수치 제약은 미지원 → Likert 1~7은 `enum: [1,2,3,4,5,6,7]`로 표현해야 함.
- 비교용 공식 다국어 표(Sonnet 4.5, extended thinking): 한국어 96.7%.

출처 URL (모두 2026-09-19 확인)
- https://platform.claude.com/docs/en/docs/about-claude/models/overview → 현행 4개 모델 ID·별칭·가격·thinking 방식·컨텍스트·폐기 약속일, "모든 Claude 모델 ID는 고정 스냅샷" 문구, 배치 50%·캐시 읽기 10%(Fable 5.1은 2.5%)
- https://platform.claude.com/docs/en/models/opus-5/overview → Opus 5 캐시 쓰기/읽기 단가, 출시일 2026-07-24, 폐기 약속일
- https://platform.claude.com/docs/en/models/opus-5/whats-new-opus-5 → thinking 기본 켜짐, effort `high` 이하에서만 disabled 허용, effort 5단계(low~max)
- https://platform.claude.com/docs/en/models/opus-5/migration-guide → temperature/top_p/top_k 기본값 외 400(Opus 4.7 이후), prefill 400, Opus 5와 Sonnet 5의 API 표면 동일(thinking·샘플링·prefill 규칙 공통)
- https://platform.claude.com/docs/en/models/fable-5-1/migration-guide → Fable 5.1 thinking 항상 켜짐·disabled 400, 캐시 읽기 $0.25, 30일 보존 필수, 접근 승인 불필요
- https://platform.claude.com/docs/en/api/messages/create → 요청 파라미터 목록(`seed`·`logprobs` 없음), temperature 범위 0.0~1.0·"Opus 4.6 이후 출시 모델은 1.0 외 거부"
- https://platform.claude.com/docs/en/build-with-claude/structured-outputs → 구조화 출력 GA, 지원 모델 목록(4개 모두 포함), 스키마 제약(수치 제약 미지원, enum 지원)
- https://platform.claude.com/docs/en/api/rate-limits → 등급별 RPM/ITPM/OTPM, 월 지출 상한, 배치 한도, Evaluation 등급
- https://platform.claude.com/docs/en/about-claude/model-deprecations → 60일 사전 통지, 모델별 폐기 약속일, 파라미터 폐기표(Python SDK v1.0에서 temperature 제거)
- https://platform.claude.com/docs/en/build-with-claude/multilingual-support → 언어별 영어 대비 점수(한국어: Sonnet 4.5 96.7%, Haiku 4.5 93.3%), 방법(인간 번역 MMLU, 0-shot CoT)

---

## 2. OpenAI

| 모델 ID | 가격 (USD/MTok) | temperature · seed · JSON · logprobs · thinking | 스냅샷 · 폐기 정책 | 한국어 근거 |
|---|---|---|---|---|
| `gpt-6-astra` (최상위, 2026-09-03 출시) | 표준: 입력 $10.00 / 캐시 입력 $1.00 / 캐시 쓰기 $12.50 / 출력 $50.00. 배치·Flex: 입력 $5.00 / 출력 $25.00(50%). 272K 초과 장문맥은 입력 $20 / 출력 $75 | temperature·top_p: **사용자 지정 불가**(공식 changelog·모델 가이드에 "제거하라"). seed: Chat Completions에만 있고 "Deprecated(Beta, best effort)" 표기, Responses API에는 없음. JSON: Structured Outputs 지원. logprobs·top_logprobs: **미지원**. thinking: 추론 모델, `reasoning.effort` = `low`/`medium`/`high`/`xhigh`/`max`, **`none` 불가(400)**. 도구 호출은 Responses API만 | 스냅샷 목록에 `gpt-6-astra` 하나뿐(날짜 박힌 스냅샷 없음). GA 모델은 폐기 최소 6개월 전 통지 | 미확인(openai.com 발표문은 403으로 열람 불가, 개발자 문서에는 언어별 수치 없음) |
| `gpt-5.6-sol` (별칭 `gpt-5.6`) | 표준: 입력 $4.00 / 캐시 $0.40 / 출력 $20.00(프로모션가, "최소 2026-11-21까지"). 배치·Flex: 입력 $2.00 / 출력 $10.00 | temperature·logprobs: **공식 문서에서 GPT-5.6 기준 명시 미확인**(참고: 제3자 보고[inspect_ai PR #5242]는 effort를 지정하지 않으면 기본 `medium`이라 temperature가 400으로 거부된다고 함 → effort `none`에서만 허용될 가능성, 미검증). seed: 위와 같음. JSON: 지원. thinking: effort `none`/`low`/`medium`(기본)/`high`/`xhigh`/`max`, `reasoning.mode` `standard`/`pro` | 스냅샷 `gpt-5.6-sol` 하나뿐(날짜 없음). 별칭 `gpt-5.6`은 Sol로 라우팅 | 미확인 |
| `gpt-5.6-luna` (저가·고속, 구 nano 등급) | 표준: 입력 $0.20 / 캐시 $0.02 / 캐시 쓰기 $0.25 / 출력 $1.20. 배치·Flex: 입력 $0.10 / 출력 $0.60 | Sol과 같음: effort `none`~`max`(기본 `medium`), temperature·logprobs의 GPT-5.6 명시 규정 미확인, JSON 지원 | 스냅샷 `gpt-5.6-luna` 하나뿐(날짜 없음) | 미확인 |
| (참고) `gpt-5.6-terra` (구 mini 등급) | 입력 $2.00 / 캐시 $0.20 / 출력 $12.00. 배치 $1.00 / $6.00 | Luna와 같음 | 날짜 없음 | 미확인 |
| (참고) `gpt-5.5-2026-04-23`, `gpt-5.4-mini-2026-03-17`, `gpt-5.4-nano-2026-03-17` | gpt-5.5: 입력 $5.00 / 출력 $30.00(272K 미만) | 날짜 박힌 스냅샷 ID가 API 모델 목록에 존재 → 재현성용 대안. 파라미터 규정은 개별 확인 필요(미확인) | 날짜 박힌 스냅샷 | 미확인 |

공통 사항
- 폐기 정책: GA 모델 최소 6개월, 특수 변형(chat-latest, codex 등) 최소 3개월, `preview` 모델은 2주까지 짧아질 수 있음. 실제 예: `gpt-5-2025-08-07`, `gpt-5-mini-2025-08-07`, `gpt-5-nano-2025-08-07`, `o3-2025-04-16`은 2026-12-11 종료 예정(2026-06-11 통지).
- 요금 등급: Free(허용 국가) 월 $100, **Tier 1($5 결제) 월 사용 한도 $100**, Tier 2($50 결제) $500, Tier 3($100) $1,000, Tier 4($250) $5,000, Tier 5($1,000) $200,000. 신규 개인 계정은 월 $100 상한에 먼저 걸린다.
- 요청 한도(Tier 1): Astra·Sol·Luna 모두 500 RPM / 500,000 TPM. 배치 대기열 한도 Luna 5,000,000, Sol 1,500,000 토큰.
- Batch API: 50% 할인, 완료 창 `24h`만 가능. Flex 처리도 배치와 같은 단가.
- 추론 토큰은 보이지 않지만 출력 토큰으로 과금된다.
- 캐시 쓰기: GPT-5.6은 비캐시 입력가의 1.25배로 과금(모델 페이지 명시).
- 한국어 근거: 공식 개발자 문서에 현행 모델의 언어별 수치 없음. OpenAI의 MMMLU(인간 번역 MMLU 14개 언어, 한국어 포함) 벤치마크가 존재하나 현행 모델 수치는 미확인.

출처 URL (모두 2026-09-19 확인)
- https://developers.openai.com/api/docs/models → 현행 대표 모델(GPT-6 Astra, GPT-5.6 Sol/Terra/Luna)과 가격, 기본 추천 모델
- https://developers.openai.com/api/docs/models/gpt-6-astra.md → Astra 모델 ID, 스냅샷 목록(날짜 없음), effort 값(`none` 없음), Tier 1 한도
- https://developers.openai.com/api/docs/models/gpt-5.6-sol.md → Sol ID·별칭·스냅샷·effort·Tier 1 한도
- https://developers.openai.com/api/docs/models/gpt-5.6-luna.md → Luna ID·가격·캐시 쓰기 1.25배·effort `none` 지원·nano 등급 대응·Tier 1 한도
- https://developers.openai.com/api/docs/pricing → 표준·배치·Flex·Fast 단가표, Sol 프로모션가 기한
- https://developers.openai.com/api/docs/guides/latest-model → Astra 이관 시 `temperature`·`top_p`·`top_logprobs`·`logprobs` 제거 지시, `none` 미지원
- https://developers.openai.com/api/docs/changelog → Astra 출시(2026-09-03)와 temperature/top_p/logprobs 미지원, GPT-5.6 계열 출시·가격 인하
- https://developers.openai.com/api/docs/guides/reasoning → effort 값은 모델마다 다름, GPT-5.6 기본 `medium`, 추론 토큰 출력 과금, reasoning mode
- https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create → Chat Completions 파라미터(temperature 0~2, logprobs, `seed` Deprecated/Beta)
- https://developers.openai.com/api/reference/resources/responses/methods/create.md → Responses API 파라미터(`seed` 없음), 모델 ID 열거(날짜 박힌 gpt-5.5/5.4 스냅샷 확인)
- https://developers.openai.com/api/docs/deprecations → 폐기 통지 기간(6개월/3개월/2주), GPT-5·o3 스냅샷 종료일
- https://developers.openai.com/api/docs/guides/rate-limits → 등급별 결제 조건·월 사용 한도
- https://developers.openai.com/api/docs/guides/batch → 50% 할인, `24h` 완료 창
- https://developers.openai.com/api/docs/guides/structured-outputs → JSON Schema 준수 보장, enum 사용 가능
- (제3자, 근거 아님) https://github.com/UKGovernmentBEIS/inspect_ai/pull/5242 → GPT-5.5/5.6에서 effort 미지정 시 temperature 400 보고

---

## 3. Google (Gemini API, ai.google.dev)

| 모델 ID | 가격 (USD/MTok, 유료 등급) | temperature · seed · JSON · logprobs · thinking | 스냅샷 · 폐기 정책 | 한국어 근거 |
|---|---|---|---|---|
| `gemini-3.8-flash` (현행 최신 GA, 2026-09-02 출시, "가장 지능적인 Flash") | 표준: 입력 $0.75 / 출력 $3.75(사고 토큰 포함) — **2026-12-31까지 도입가**, 2027-01-01부터 입력 $1.50 / 출력 $7.50. 배치: 입력 $0.375 / 출력 $1.875(도입가). 캐시 $0.075(+저장 $0.50/MTok·시간) | temperature·top_p·top_k: **이관 체크리스트에서 "deprecated sampling parameters"로 제거 지시**. seed: API 레퍼런스 `generationConfig.seed` 필드 존재(3.8 Flash에서 동작 여부 미확인). JSON: Structured outputs 지원(`enum`, `minimum`/`maximum` 지원). logprobs: 공식 문서 명시 미확인(아래 참고). thinking: **항상 켜짐**, `thinking_level` = `low`/`medium`(기본)/`high`, `minimal`은 오류. prefill된 model 턴 제거 지시, `candidate_count` 미지원 | 버전은 `gemini-3.8-flash`(stable) 하나. 폐기일 "발표 없음". 날짜 박힌 스냅샷 ID 없음 | 공식 모델 카드에 다국어(MMMLU 등) 수치 없음 → 미확인. 지식 컷오프 2026-03 |
| `gemini-3.1-pro-preview` (Pro 계열 최상위, **Preview**) | 입력 $2.00 / 출력 $12.00(200K 이하), 200K 초과 $4.00 / $18.00. 캐시 $0.20. 무료 등급 없음 | temperature: Gemini 3 가이드는 "기본값 1.0 유지를 강력 권고, 낮추면 반복·성능 저하 가능"(설정 자체는 가능한 것으로 읽힘). thinking: 항상 켜짐, `low`/`medium`/`high`(기본 `high`). JSON 지원. logprobs: 미확인 | Preview(2026-02-19 출시), 폐기일 "발표 없음". Preview 모델은 요청 한도가 더 제한적 | 미확인 |
| `gemini-3.5-flash-lite` (저가·고속, 2026-07-21 출시) | 표준: 입력 $0.30 / 출력 $2.50. 배치: 입력 $0.15 / 출력 $1.25. 캐시 $0.03 | temperature: Gemini 3 공통 권고(1.0 유지). thinking: 기본 `minimal`, `minimal`/`low`/`medium`/`high` 선택 가능. 단 "minimal이 사고 꺼짐을 보장하지 않음". JSON 지원. logprobs: 미확인 | stable, 폐기일 "발표 없음" | 미확인 |
| (참고) `gemini-3.1-flash-lite` | 입력 $0.25 / 출력 $1.50 | — | **폐기 예정 2027-05-07**(대체: 3.5-flash-lite) | 미확인 |

공통 사항
- 무료 등급(Free): 일부 모델 무료 사용 가능하지만 **"Content used to improve our products: Yes"** — 실험 자극문이 학습에 쓰일 수 있음. 유료 등급은 "No".
- 사용 등급: Tier 1 = 결제 계정 연결만 하면 됨(청구 상한 $250), Tier 2 = 누적 $100 결제 + 첫 결제 후 3일(상한 $2,000), Tier 3 = $1,000 + 30일. 지출 기반 한도: Tier 1은 **10분당 $10**. 요청 한도는 프로젝트 단위이며 AI Studio에서만 확인 가능(문서에 모델별 RPM 표 없음).
- Batch API: 표준가의 50%, 목표 처리 시간 24시간, 동시 배치 100개, Tier 1 대기열 토큰 3.8 Flash 3,000,000 / 3.5 Flash-Lite 10,000,000 / 3.1 Pro Preview 5,000,000.
- logprobs: API 레퍼런스의 `generationConfig`에 `responseLogprobs`(bool)·`logprobs`(0~20) 필드가 있으나, 현행 3.x 모델 지원 여부는 공식 문서에서 미확인. 공식 개발자 포럼(discuss.ai.google.dev)의 사용자 보고에 따르면 3.1 Pro·3.6 Flash에서 "Logprobs is not supported for this model" 오류, 새 Interactions API 설정에도 logprobs 필드가 없음(비공식 보고, 근거 약함).
- 폐기 페이지 문구: 표의 종료일은 "가장 이른 가능 날짜"이며 정확한 날짜는 사전 통지.
- 2026년 5월 이후 문서의 기본 호출 방식이 `interactions.create`(Interactions API)로 바뀜. generateContent도 레퍼런스에 남아 있음.

출처 URL (모두 2026-09-19 확인)
- https://ai.google.dev/gemini-api/docs/models → 현행 모델 목록과 stable/preview 구분(3.8 Flash stable, 3.1 Pro preview)
- https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash → 모델 코드·버전(stable 하나)·토큰 한도·기능(Structured outputs, Batch, 사고 low/medium/high)
- https://ai.google.dev/gemini-api/docs/latest-model (→ whats-new-gemini-3.8-flash) → temperature/top_p/top_k 제거 지시, `minimal` 미지원, 기본 `medium`, 도입가와 2027년 정가
- https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite → 모델 코드·stable·기능
- https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview → 모델 코드·preview 버전 2종
- https://ai.google.dev/gemini-api/docs/pricing → 모델별 표준·배치 단가, 도입가 기한, 무료 등급의 데이터 사용 여부
- https://ai.google.dev/gemini-api/docs/gemini-3 → Gemini 3 공통 temperature 1.0 유지 권고, "minimal이 사고 꺼짐을 보장하지 않음"
- https://ai.google.dev/gemini-api/docs/thinking → 모델별 기본 사고 수준과 지원 수준 표
- https://ai.google.dev/gemini-api/docs/structured-output → JSON Schema 지원 키워드(enum, minimum, maximum 등)
- https://ai.google.dev/api/generate-content → `generationConfig.seed`, `responseLogprobs`, `logprobs` 필드 정의
- https://ai.google.dev/gemini-api/docs/rate-limits → 사용 등급 조건, 지출 기반 한도, 배치 한도
- https://ai.google.dev/gemini-api/docs/batch-api → 50% 가격, 24시간 목표
- https://ai.google.dev/gemini-api/docs/deprecations → 모델별 출시일·종료일(3.1 Flash-Lite 2027-05-07)
- https://deepmind.google/models/model-cards/gemini-3-8-flash/ → 다국어 벤치마크 미보고, 지식 컷오프 2026-03
- (비공식 참고) https://discuss.ai.google.dev/t/missing-logprobs-support-in-the-newest-gemini-models-3-1-pro-3-6-flash-on-vertex-ai-and-ai-studio/176557 → 최신 모델 logprobs 미지원 사용자 보고

---

## 4. 한국어 특화 상용 API

이 절은 1–3절과 같은 표 형식을 쓰되, 표 위에 **개인 연구자가 API 키를 받아 종량제로 쓸 수 있는지**를 먼저 적는다. 가격은 원문 통화(원화는 VAT 별도 여부를 함께) 그대로 적고, 비교를 위해 괄호 안에 MTok당 환산값을 덧붙였다(환산은 단순 곱셈이며 환율 변환은 하지 않았다).

### 4.1 NAVER HyperCLOVA X (CLOVA Studio)

**개인 이용 가능성: 가능한 것으로 보임(명시 문구는 미확인).** 네이버 클라우드 플랫폼 가입 화면에 회원 유형으로 "사업자 회원"과 "개인 회원"이 나란히 있고, 공식 FAQ는 CLOVA Studio를 "Open Beta로 운영"하며 콘솔의 '상품 이용 신청'만으로 이용 가능하다고 적는다. 2025-07-17 릴리스 노트부터는 "API 키 발급만으로" 모든 기능을 쓸 수 있다(테스트 앱 생성 불필요). 다만 "개인 회원도 CLOVA Studio를 쓸 수 있다"는 문장 자체와 결제 수단 등록 필수 여부는 공식 문서에서 찾지 못했다(미확인). 처리량을 늘리는 '서비스 앱'은 AI 윤리 가이드 준수 심사를 거친다.

| 모델 ID | 가격 (KRW, VAT 별도) | temperature · seed · JSON · logprobs · thinking | 스냅샷 · 폐기 정책 | 한국어 근거 |
|---|---|---|---|---|
| `HCX-007` (하이브리드 추론 모델, 2025-07-29 출시, 조사일 기준 최신) | 입력 1.25원 / 출력 5원 (1,000토큰당) = **입력 1,250원 / 출력 5,000원 (MTok당)** | temperature: **0.00~1.00 설정 가능**(기본 0.50). topP(기본 0.80)·topK(0~128)·repetitionPenalty(기본 1.1) 있음. seed: **있음**(0=무작위, 1~4,294,967,295). JSON: Structured Outputs 지원(`responseFormat` `{type:"json", schema}`, `enum`·`minimum`/`maximum`·`integer` 지원, `pattern` 미지원). **단 Structured Outputs와 추론은 동시 요청 불가 → `thinking.effort: "none"` 필수.** logprobs: **없음**(네이티브 파라미터 목록에 없고, OpenAI 호환 API는 `logprobs`·`top_logprobs`를 "미지원"으로 명시). thinking: `thinking.effort` = `none`/`low`(기본)/`medium`/`high`, 추론 시 `stop` 사용 불가, maxCompletionTokens 최대 32,768 | 모델명 고정(`HCX-007`), 날짜 박힌 스냅샷 없음. 폐기·지원 종료 정책 문서 미확인. 컨텍스트 128K | 공식 기술 보고서 "HyperCLOVA X THINK"(arXiv 2506.22403) 표 3, zero-shot CoT 정확도: KMMLU 69.7, CSAT 83.2, KoBALT-700 48.9, HAERAE-1.0 87.8, CLIcK 80.1, KoBigBench 85.9. **단 THINK = HCX-007이라는 문장은 보고서·가이드 어디에도 없어 동일 모델인지는 미확인** |
| `HCX-005` (비전 겸용, 2025-04-17) | 입력 1.25원 / 출력 5원 (1K) = 1,250원 / 5,000원 (MTok) | temperature 0.00~1.00(기본 0.50), seed 있음, Structured Outputs **미지원**, logprobs 없음, 추론 없음 | 모델명 고정, 폐기 정책 미확인. 컨텍스트 128K, 최대 출력 4,096 | 모델별 수치 미확인 |
| `HCX-DASH-002` (경량) | 입력 0.25원 / 출력 1원 (1K) = 250원 / 1,000원 (MTok) | HCX-005와 같음(추론·JSON 미지원) | 모델명 고정. 컨텍스트 32K | 미확인 |
| (참고) `HCX-003`, `HCX-DASH-001` (구세대) | 입출력 구분 없이 1,000토큰당 5원 / 1원 | 추론·Structured Outputs·Function calling 미지원, 컨텍스트 8K/4K | 폐기 정책 미확인. (별개로 구 API URL `clovastudio.apigw.ntruss.com`은 "지원 중단 예정" 공지) | 미확인 |

공통 사항
- 요청 한도(메인 계정 기준, 서브 계정 사용량 합산): 일반 API 키 HCX-007 **60 QPM / 60,000 TPM**, HCX-005 60 / 60,000, HCX-DASH-002 90 / 80,000. 서비스 앱 키는 HCX-007 180 QPM / 300,000 TPM. "최대치 이내에서도 지연·실패 가능" 단서.
- 배치(할인) API: 공식 문서에서 찾지 못함(미확인).
- OpenAI 호환 API: `https://clovastudio.stream.ntruss.com/v1/openai/` `/chat/completions`. 지원 파라미터에 `temperature`·`top_p`·`seed`·`n`(1만)·`response_format`(`json_schema`)·`reasoning_effort`(`none`/`low`/`medium`/`high`) 포함, `logprobs`·`top_logprobs`·`frequency_penalty`·`presence_penalty`·`logit_bias` 미지원.
- 지원 리전은 한국만, 지원 언어는 한국어·영어·일본어.
- 가격 페이지는 동적 렌더링이라 WebFetch로는 표가 보이지 않았고, 브라우저로 렌더링한 뒤 표를 읽었다(값은 공식 상품 페이지 그대로).

출처 URL (모두 2026-09-19 확인)
- https://www.ncloud.com/product/aiService/clovaStudio (요금 탭, 브라우저 렌더링) → 모델별 1,000토큰당 요금·VAT 별도·입출력 분리 과금 모델 목록
- https://guide.ncloud-docs.com/docs/clovastudio-model → 모델 목록(HCX-007/005/DASH-002/003/DASH-001), 컨텍스트·최대 출력, 추론·Structured Outputs·Function calling 지원 여부
- https://api.ncloud-docs.com/docs/clovastudio-chatcompletionsv3-thinking → HCX-007 추론 파라미터(`thinking.effort` 값·기본값, temperature/topP/topK/seed/repetitionPenalty 범위), 추론과 Structured Outputs 동시 요청 불가, 추론 시 `stop` 불가
- https://api.ncloud-docs.com/docs/clovastudio-chatcompletionsv3 → v3 공통 파라미터 범위·기본값, HCX-005/DASH-002 토큰 한도
- https://api.ncloud-docs.com/docs/clovastudio-chatcompletionsv3-so → Structured Outputs 지원 모델(HCX-007만)·지원 키워드·`thinking.effort: none` 필요
- https://api.ncloud-docs.com/docs/clovastudio-openaicompatibility → OpenAI 호환 지원/미지원 파라미터(`logprobs` 미지원)
- https://api.ncloud-docs.com/docs/ai-naver-clovastudio-summary → API 목록, 구 API URL 지원 중단 예정, 문서 갱신일 2026-09-17
- https://guide.ncloud-docs.com/docs/clovastudio-ratelimiting → 모델·키 종류별 QPM/TPM
- https://guide.ncloud-docs.com/docs/clovastudio-releasenote → HCX-007·Structured Outputs 출시(2025-07-29), API 키 발급만으로 이용(2025-07-17), HCX-005/DASH-002·OpenAI 호환(2025-04-17)
- https://guide.ncloud-docs.com/docs/clovastudio-spec → 과금 기준(모델·용도·토큰 수), 리전·언어
- https://guide.ncloud-docs.com/docs/clovastudio-app-publish → 서비스 앱 심사(AI 윤리 가이드 준수 확인)
- https://www.ncloud.com/join/type → 회원 유형 "사업자 회원 / 개인 회원"
- https://www.ncloud.com/support/faq/all/2951 → "CLOVA Studio는 Open Beta로 운영", 콘솔 '상품 이용 신청'으로 이용
- https://arxiv.org/abs/2506.22403 → HyperCLOVA X THINK 기술 보고서 표 3(한국어 벤치마크)

### 4.2 Upstage Solar (console.upstage.ai)

**개인 이용 가능성: 가능.** 콘솔은 이메일 가입·인증 후 신용카드를 등록해 쓰는 구조이며, 과금은 월말 후불 종량제(pay-as-you-go) 또는 선불 크레딧 중 선택이고 최소 구매액이 없다. 사업자 등록을 요구하는 문구는 없다. 월 $100 이상 선불 시 약정 등급(Explore/Build/Scale)이 붙어 한도와 보너스 크레딧이 오르지만 필수는 아니다. 2026-08-04부터 모든 계정이 기본 Organization 하나에 속한다. 콘솔 API 입력은 "학습에 쓰지 않고 저장하지 않음"(모델 페이지), 반면 무료 Playground 입력은 모델 개선에 쓰일 수 있다고 FAQ에 적혀 있다.

| 모델 ID | 가격 (USD/MTok, VAT 10% 별도) | temperature · seed · JSON · logprobs · thinking | 스냅샷 · 폐기 정책 | 한국어 근거 |
|---|---|---|---|---|
| `solar-pro4` → 스냅샷 `solar-pro4-260806` (플래그십, 2026-08-06 출시) | 정가: 입력 $0.30 / 캐시 입력 $0.06 / 출력 $1.20. **2026-10-09(UTC)까지 70% 할인가: 입력 $0.09 / 캐시 $0.018 / 출력 $0.36**(2026-09-11에 90%→70%로 할인 축소). 2026-08-10까지 무료 기간이 있었음 | temperature: **0~2 설정 가능**(Pro 4 기본 1.0). top_p 0~1. frequency_penalty 기본값이 **1.1**(0이 아님 → 재현 설정 시 명시 필요), presence_penalty 기본 0. seed: **요청 파라미터 없음**. JSON: `response_format` `json_object`/`json_schema`(strict, OpenAI 부분집합, `enum` 가능). logprobs: **요청 파라미터 없음, 응답의 `choices[].logprobs`는 "not yet available"로 항상 null**. thinking: `reasoning_effort` 생략·`null`·`none`·`minimal`이면 **꺼짐(기본 꺼짐)**, `low`~`max`로 켬, 켜면 `message.reasoning`에 과정 반환 | **날짜 박힌 스냅샷 ID로 고정 가능**(API가 `model`에 별칭과 스냅샷을 모두 열거, "특정 버전 고정이 필요하면 스냅샷 사용" 권고). 컨텍스트 512K, 최대 출력 128K, 지식 컷오프 2026-02 | 공식 블로그(2026-08-11): KMMLU-Pro 79.2, KBL(법률) 77.5, KorMedMCQA 93.2, Ko-GDPval 87.3(비교: Solar Open 2 78.4/75.5/93.0/86.8). 기술 보고서는 없음 |
| `solar-pro3` → 스냅샷 `solar-pro3-260323` | 입력 $0.15 / 캐시 $0.015 / 출력 $0.60 | temperature 0~2(Pro 3 기본 **0.8**), top_p 기본 **0.95**. seed·logprobs 없음. JSON 지원. thinking: 생략 시 꺼짐, `minimal`/`low` 꺼짐, `medium`/`high` 켬 | 스냅샷 고정 가능. **선례: 첫 스냅샷 `solar-pro3-260126`(2026-01-26 출시)은 새 스냅샷(2026-03-23) 후 2026-04-30 지원 종료 — 약 3개월 만에 폐기.** 102B 전체/12B 활성 MoE, 컨텍스트 128K | 모델 페이지·블로그의 한국어 수치 미확인. (참고: 같은 102B MoE 규모의 공개 모델 Solar Open 기술 보고서[arXiv 2601.07022]에 KMMLU 73.0·KMMLU-Pro 64.0·CLIcK 78.9·HAE-RAE v1.1 73.3이 있으나 Pro 3과 같은 모델이라는 공식 문구는 없음) |
| `solar-pro2` → 스냅샷 `solar-pro2-251215` | 입력 $0.15 / 캐시 $0.015 / 출력 $0.60 | Pro 3과 같음, 단 추론 과정 텍스트는 반환 안 됨 | 31B, 컨텍스트 65,536. 이전 스냅샷 `-250710`·`-250909`는 폐기 | 미확인 |
| `solar-mini` → 스냅샷 `solar-mini-250422` | $0.15 (입출력 구분 없이 MTok당) | 추론 미지원(`reasoning_effort`를 보내면 400). seed·logprobs 없음 | 스냅샷 고정 가능 | 미확인 |

공통 사항
- 엔드포인트: `https://api.upstage.ai/v1` `/chat/completions`(OpenAI SDK 호환). 한국 내 처리용 `kr.api.upstage.ai` 지역 엔드포인트도 있음(지원 모델은 별도 문서).
- 요청 한도 Tier 0(최하위 등급. 약정 없는 계정이 여기에 해당한다는 명시 문구는 없어 추정): Solar Pro 4·Pro 3·Pro 2 각 **100 RPM / 250,000 TPM**, Solar Mini 100 RPM / 50,000 TPM. Tier 1(Explore, 월 $100+ 선불) Pro 4 400 RPM / 500,000 TPM.
- 배치(할인) API: 공식 문서에서 찾지 못함(미확인). 프롬프트 캐시는 `prompt_cache_key`로 지정.
- 폐기 통지 기간을 정한 정책 문서는 찾지 못함(미확인). 변경 이력(Changelog)에 폐기가 "Breaking Change"로 기록된다.
- 추론 토큰은 출력 토큰으로 과금되며 `usage.completion_tokens_details.reasoning_tokens`에 보고된다.

출처 URL (모두 2026-09-19 확인)
- https://console.upstage.ai/api/chat (브라우저 렌더링) → 요청 파라미터 전체(`model` 허용값에 별칭·스냅샷 열거, temperature 0~2·모델별 기본값, top_p, frequency_penalty 기본 1.1, `reasoning_effort` 값표, `response_format`, `prompt_cache_key`; `seed`·`logprobs` 없음), 응답의 `logprobs`·`system_fingerprint` "not yet available"
- https://console.upstage.ai/docs/models/history → 모델·스냅샷별 출시일·파라미터 수·컨텍스트·폐기 표시(solar-pro3-260126, solar-pro2-250909 등), solar-open2 API 종료
- https://console.upstage.ai/docs/models/solar-pro-4 (브라우저 렌더링) → Pro 4 정가(입력 $0.30·출력 $1.20·캐시 $0.06), 스냅샷 `solar-pro4-260806`, API 데이터 비수집·비학습
- https://www.upstage.ai/pricing (브라우저 렌더링) → 70% 할인가와 기한(2026-10-09 UTC), Pro 3·Pro 2·Mini 단가, VAT 10% 별도, 약정 등급 조건, 신용카드 결제
- https://console.upstage.ai/docs/capabilities/generate/reasoning → 모델별 `reasoning_effort` on/off 값, 추론 토큰 과금, 기본 꺼짐
- https://console.upstage.ai/docs/capabilities/generate/structured-outputs → JSON mode vs Structured outputs, 지원·미지원 스키마 키워드
- https://console.upstage.ai/docs/guides/rate-limits → 등급별 RPM/TPM(Tier 0~4, Legacy)
- https://console.upstage.ai/docs/resources/changelog → Pro 4 출시·무료 기간 종료·할인율 변경(2026-09-11), solar-pro3-260126 지원 종료(2026-04-30), Organization 전환(2026-08-04), solar-open2 API 종료(2026-08-12)
- https://console.upstage.ai/docs/resources/faq (브라우저 렌더링) → 후불 종량제/선불 크레딧, 최소 구매액 없음, 신용카드, Playground 입력의 모델 개선 사용 가능성
- https://www.upstage.ai/blog/en/solar-pro-4 → Solar Pro 4 한국어 벤치마크(KMMLU-Pro 등), 게시일 2026-08-11
- https://arxiv.org/abs/2601.07022 → Solar Open 기술 보고서(공개 가중치 102B MoE, 한국어 벤치마크)

### 4.3 LG AI Research EXAONE

**개인 이용 가능성: LG의 자체 종량제 API는 없음.** LG AI연구원 공식 서비스 허브(EXAONE Showroom)는 "개인 사용자는 가입·이용 불가, 기업 고객 대상"이라고 명시한다. EXAONE은 공개 가중치로만 배포되고, 공식 모델 카드가 API 경로로 링크하는 곳은 FriendliAI뿐이다. 그런데 **조사일 기준 FriendliAI의 종량제(Model APIs, 구 Serverless) 실시간 카탈로그에는 EXAONE 계열이 하나도 없다**(GLM·Gemma·DeepSeek·MiniMax 7종만). K-EXAONE·K-EXAONE 2.0의 FriendliAI 모델 페이지는 "Dedicated Endpoints, Container"만 지원으로 표시한다. 즉 지금 EXAONE을 API로 쓰려면 FriendliAI 전용 엔드포인트(GPU 시간 과금)를 빌리는 수밖에 없다. 과거 경로(참고): EXAONE 4.0은 2025-07 FriendliAI 서버리스 독점 제공, K-EXAONE(236B)은 2026-01 서버리스로 출시(2026-01-28까지 무료)됐으나 현재 카탈로그에서는 빠졌다.

| 모델 ID (Hugging Face) | 가격 | temperature · seed · JSON · logprobs · thinking | 스냅샷 · 폐기 정책 | 한국어 근거 |
|---|---|---|---|---|
| `LGAI-EXAONE/K-EXAONE-2.0-750B-A37B` (2026-07-29 공개, 최신 플래그십, 750B 전체/37B 활성 MoE, **Apache-2.0**) | 종량제 API 없음. FriendliAI 전용 엔드포인트만(GPU 시간 과금: H100 80GB $3.9/시간 → 2026-10-01부터 $5.0/시간, B200 $8.9 → $9.0. 750B 모델은 GPU 여러 장 필요) | 자체 호스팅(vLLM·SGLang) 기준: temperature·seed·logprobs는 서빙 엔진이 결정. 권장 샘플링 temperature 1.0·top_p 0.95. 추론: `chat_template_kwargs` `enable_thinking`(기본 True), False면 비추론 | 가중치 파일 자체가 고정 스냅샷(재현성 최상). API 폐기 정책 해당 없음 | 공식 모델 카드: KMMLU-Pro 69.1, CLIcK 84.2, HRM8K-KSM 91.1 (추론 모드). 기술 보고서 arXiv 2608.04505 |
| `LGAI-EXAONE/K-EXAONE-236B-A23B` (2025-12-26 공개, 236B/23B 활성 MoE) | 종량제 API 없음(FriendliAI 서버리스에서 내려감). 전용 엔드포인트만 | 권장 temperature 1.0·top_p 0.95·presence_penalty 0.0. `enable_thinking` 토글 | 가중치 고정. 라이선스 "K-EXAONE AI Model License Agreement" | 공식 GitHub README(추론 모드): KMMLU-Pro 67.3, **KoBALT 61.8**, CLIcK 83.9, HRM8K 90.9, Ko-LongBench 86.8. 기술 보고서 arXiv 2601.01739 |
| `LGAI-EXAONE/EXAONE-4.5-33B` (2026-04 공개, 비전-언어) | 종량제 API 없음 | 권장 temperature 1.0(한국어·문서 과제는 0.6), top_p 0.95, presence_penalty 1.5. `enable_thinking` 기본 True(4.0과 반대) | 가중치 고정. **라이선스 "EXAONE AI Model License Agreement 1.2 - NC"(비상업)** — 학술 연구는 가능한 것으로 읽히나 약관 원문 확인 필요 | 모델 카드: KMMLU-Pro 67.6, KoBALT 52.1. 기술 보고서 arXiv 2604.08644 |

공통 사항
- 결론: 상용 종량제 API로 EXAONE을 부르는 공식 경로는 조사일 기준 **없음**. OpenRouter·Together 등 다른 호스팅 경로는 5절에서 확인.
- FriendliAI 계정 자체는 개인도 API 키 발급 가능(5절 참고)하나, EXAONE은 전용 GPU 엔드포인트라 "종량제 토큰 과금"이 아니다.

출처 URL (모두 2026-09-19 확인)
- https://showroom.exaone.ai/en → "individual users cannot sign up for Showroom … offered for enterprise customers"
- https://www.lgresearch.ai/exaone/ → 최신 모델(EXAONE 4.5), 공식 서비스(Showroom·ChatEXAONE·Data Foundry), 문의 채널
- https://huggingface.co/api/models?author=LGAI-EXAONE → 모델별 공개일(K-EXAONE 2.0 2026-07-29, EXAONE 4.5 2026-04-04, K-EXAONE 2025-12-26)
- https://huggingface.co/LGAI-EXAONE/K-EXAONE-2.0-750B-A37B → Apache-2.0, FriendliAI API 배지, 한국어 벤치마크, `enable_thinking`, 권장 샘플링
- https://github.com/LG-AI-EXAONE/K-EXAONE → K-EXAONE 한국어 벤치마크(KoBALT 포함), 권장 샘플링, FriendliAI 링크, 기술 보고서 링크
- https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B → NC 라이선스, KMMLU-Pro·KoBALT, `enable_thinking` 기본값, 권장 샘플링
- https://api.friendli.ai/serverless/v1/models (공개 JSON) 및 https://friendli.ai/api/public/model-apis → 조사일 현재 종량제 카탈로그 7개 텍스트 모델, EXAONE 없음
- https://friendli.ai/models/LGAI-EXAONE/K-EXAONE-2.0-750B-A37B, https://friendli.ai/models/LGAI-EXAONE/K-EXAONE-236B-A23B → 지원 형태 "Dedicated Endpoints, Container"
- https://friendli.ai/pricing → 전용 엔드포인트 GPU 시간 단가와 2026-10-01 인상
- https://friendli.ai/blog/k-exaone-on-serverless, https://friendli.ai/blog/lg-ai-research-partnership-exaone-4.0 → 과거 서버리스 제공 이력(참고)
- (제3자, 근거 보강) https://github.com/BerriAI/litellm/pull/41001 → 2026-09-13 LiteLLM이 FriendliAI 카탈로그에서 사라진 K-EXAONE 항목을 제거

### 4.4 Kakao Kanana

**개인 이용 가능성: 상용 종량제 API 없음.** 카카오가 처음 연 API는 멀티모달 `Kanana-1.5-o-9.8b-2602`의 **클로즈드 베타(CBT, 2026-02-27~2026-05-27)**였고, 신청자(개발자·학생·스타트업·연구자) 중 선정자에게만 카카오톡 알림톡으로 초대장을 보내는 방식이었다. 베타 기간 중 "정해진 매일 횟수만큼" 무료 테스트였고 가격은 공개되지 않았다. 조사일 기준 베타 안내·API 페이지(api-omni.kanana.ai, omni.kanana.ai)는 404이며, 정식(유료) API 출시 공지는 찾지 못했다(미확인). 텍스트 LLM(Kanana-2)은 공개 가중치로만 배포된다.

| 모델 ID (Hugging Face) | 가격 | temperature · seed · JSON · logprobs · thinking | 스냅샷 · 폐기 정책 | 한국어 근거 |
|---|---|---|---|---|
| `kakaocorp/kanana-2-30b-a3b-instruct-2601` / `-thinking-2601` (2026-01-15 공개, 30B 전체/3B 활성 MoE, MLA) | 종량제 API 없음(호스팅 경로는 5절) | 자체 호스팅 시 서빙 엔진이 결정. instruct/thinking이 **별도 체크포인트**(추론 토글이 아니라 모델 선택) | 가중치 고정. 이름에 `-2601` 날짜 접미사로 버전 구분(초판 `kanana-2-30b-a3b-instruct`는 2025-12-18). 라이선스 "Kanana License"(원문 확인 필요). 컨텍스트 32,768 | 공식 GitHub README(instruct-2601): **KMMLU 68.26, HAERAE-Bench v1.0 75.57**, KoMT-Bench 8.21(비교 Qwen3-30B-A3B-Instruct-2507: 67.56 / 53.41 / 8.49) |
| `kakaocorp/kanana-2-3b-instruct`, `kanana-2-1.3b-instruct` (2026-07-24 공개) | 종량제 API 없음 | 자체 호스팅 시 서빙 엔진이 결정 | 가중치 고정 | 미확인 |
| (종료) `Kanana-1.5-o-9.8b-2602` API 베타 | 베타 무료(일일 횟수 제한), 종료 | API 파라미터 문서는 HF `kakaocorp/Kanana-1.5-o-9.8B-instruct-2602-API_Doc`에 있었음(세부 미확인) | 베타 종료 | 미확인 |

출처 URL (모두 2026-09-19 확인)
- https://tech.kakao.com/posts/811 (2026-02-12 게시, 브라우저 렌더링) → Kanana-o API 베타: 모델 `Kanana-1.5-o-9.8b-2602`, 기간 2026-02-27~05-27, CBT, 신청 대상, 일일 횟수 제한, 알림톡 초대
- https://api-omni.kanana.ai/, https://omni.kanana.ai/ → 조사일 기준 404
- https://kanana.ai/ → 오픈소스 모델 다운로드·카카오톡 내 서비스 안내만, API 안내 없음
- https://github.com/kakao/kanana-2 → Kanana-2 공개 일정, 아키텍처, 컨텍스트, 벤치마크 표(KMMLU·HAERAE), 라이선스
- https://huggingface.co/api/models?author=kakaocorp → 체크포인트별 공개일(2601 버전, 3B/1.3B 2026-07-24, API_Doc 저장소)

### 4.5 KT 믿:음 (Mi:dm)

**개인 이용 가능성: 셀프서비스 종량제 API를 찾지 못함.** KT 기업 상품 페이지("믿음 K")는 Mi:dm API(감성분석·요약 등 13개 과제 기능)와 KT Cloud AI Foundry를 안내하지만, 이용 경로는 "상담 신청"(전화 1588-0114)이고 대상은 기업·중소기업·스타트업·공공 연구기관이다. 공개 요금표·개인 가입 절차·토큰 단가는 찾지 못했다(미확인). 공개 가중치는 Mi:dm 2.0(Base 11.5B, Mini 2.3B, MIT 라이선스)뿐이며, 2026-02 MWC에서 발표된 최신 "믿:음 K 2.5 Pro"(32B, 128K)는 Hugging Face K-intelligence 조직에 올라와 있지 않다(조사일 기준 목록 확인). 모델 카드는 FriendliAI "Deploy → Friendli Endpoints"(전용 엔드포인트) 경로만 안내한다.

| 모델 ID | 가격 | temperature · seed · JSON · logprobs · thinking | 스냅샷 · 폐기 정책 | 한국어 근거 |
|---|---|---|---|---|
| `K-intelligence/Midm-2.0-Base-Instruct` (2025-07-04 공개, 11.5B, MIT) | 종량제 API 미확인(기업 상담). 자체 호스팅 또는 FriendliAI 전용 엔드포인트 | 자체 호스팅 시 서빙 엔진이 결정. vLLM function calling 파서 지원(2025-10-29) | 가중치 고정 | 공식 모델 카드: **KMMLU 57.3, HAERAE 81.5**, Ko-Sovereign 56.3/58.0, K-Refer 89.6, Ko-IFEval 82, Ko-MTBench 89.7 (KoBALT 미보고) |
| `K-intelligence/Midm-2.0-Mini-Instruct` (2.3B) | 위와 같음 | 위와 같음 | 가중치 고정 | 모델 카드: KMMLU 45.1, HAERAE 70.8 |
| 믿:음 K 2.5 Pro (API ID 미확인) | 기업 상담(미확인) | 미확인 | 미확인 | 보도자료 수준의 주장(AAII v3.0 한국 모델 최고, τ²-bench 87%)만 있고 공식 기술 보고서 미확인 |

출처 URL (모두 2026-09-19 확인)
- https://enterprise.kt.com/pd/P_PD_NE_00_316.do → 믿음 K 상품(2.0 Mini/Base, 2.5 Pro), Mi:dm API 13개 기능, AI Foundry, "상담 신청", 대상 고객
- https://enterprise.kt.com/bt/dxstory/3701.do → Mi:dm 2.0 공개(2025-07), MIT 라이선스, 개인·기업 상업 이용 허용
- https://huggingface.co/K-intelligence/Midm-2.0-Base-Instruct → 한국어 벤치마크 표, News(2025-07-04 공개, 2025-10-29 function calling), Friendli 전용 엔드포인트 안내
- https://huggingface.co/api/models?author=K-intelligence → 공개 가중치 목록(2.5 Pro 없음)
- (보도, 근거 약함) https://m.news.nate.com/view/20260226n35390 → 믿:음 K 2.5 Pro 발표(MWC 2026)

### 4.6 SKT A.X

**개인 이용 가능성: 공개 셀프서비스 종량제 API 없음.** SKT 뉴스룸(2026-07-29)은 "자사 AI 모델을 API 형태로도 제공"한다고 하지만 대상은 과기정통부 '전국민AI경진대회' 참가자와 중기부 '모두의 챌린지 AX-LLM' 선정 스타트업(3곳, 연말까지 A.X K1 API)이다. 가입·가격·API 문서 공개 페이지는 찾지 못했다(미확인). 최신 모델 A.X K2는 Apache-2.0 공개 가중치다.

| 모델 ID (Hugging Face) | 가격 | temperature · seed · JSON · logprobs · thinking | 스냅샷 · 폐기 정책 | 한국어 근거 |
|---|---|---|---|---|
| `skt/A.X-K2` (2026-07-28 공개, 688B 전체/33B 활성 MoE, 256K, **Apache-2.0**) | 종량제 API 없음(호스팅 경로는 5절) | 자체 호스팅(vLLM, `deepseek_v3` 추론 파서) 시 엔진이 결정. 추론: 단일 모델 Think-Fusion, `chat_template_kwargs` `enable_thinking`(생략·False = 비추론) | 가중치 고정 | 공식 모델 카드(thinking 모드): **KMMLU-Pro 80.5, KoBALT 73.0, CLIcK 91.6**. 같은 표의 비교: DeepSeek-V4 Flash 78.8/**75.3**/89.6, Qwen3.5-397B-A17B 78.4/69.9/88.4, GLM-5.1 76.5/72.0/88.8, A.X K1 68.9/51.0/85.3. 기술 보고서 arXiv 2608.30181 |
| `skt/A.X-K1` (2025-12-29 공개, 519B/33B 활성) | 선정 스타트업·경진대회 참가자 한정 API | 미확인 | 가중치 고정 | 위 표: KMMLU-Pro 68.9, KoBALT 51.0, CLIcK 85.3 |
| `skt/A.X-4.0`, `skt/A.X-4.0-Light`, `skt/A.X-3.1` (2025-07) | 종량제 API 없음 | 자체 호스팅 | 가중치 고정 | 미확인(이번 조사에서 모델 카드 수치 미열람) |

출처 URL (모두 2026-09-19 확인)
- https://news.sktelecom.com/228501 → A.X K2 공개(2026-07-29), API 제공 대상(전국민AI경진대회·모두의 챌린지 AX-LLM), 가격 미공개
- https://huggingface.co/skt/A.X-K2 → Apache-2.0, 파라미터·컨텍스트, Think-Fusion·`enable_thinking`, 한국어 벤치마크 표(비교 모델 포함), 기술 보고서 링크
- https://huggingface.co/api/models?author=skt → 모델별 공개일
- (보도) https://www.ddaily.co.kr/page/view/2026072611175239932 → A.X K1 API는 선정 스타트업 3곳에 연말까지 제공

---

## 5. 호스팅 API로 쓰는 공개 가중치 모델

핵심 질문은 두 가지다. (1) 4절의 한국어 공개 모델(EXAONE·Kanana·HyperCLOVA X SEED·Mi:dm·A.X)을 종량제 API로 부를 수 있는가, (2) **logprobs를 주는 경로**가 있는가. logprobs는 두 종류로 나눠 적었다. **출력 logprobs**(생성한 토큰과 top-k 대안의 로그확률, 예: 평정 숫자 "1"~"7"의 확률 분포)와 **프롬프트 logprobs**(`echo`로 입력 문장 각 토큰의 로그확률을 돌려받는 것, 자극문 surprisal 계산에 필요)다.

### 5.1 한국어 공개 모델의 호스팅 현황 (조사일 기준)

| 모델 | OpenRouter | Together | Fireworks | Groq | FriendliAI 종량제 | Hugging Face Inference Providers |
|---|---|---|---|---|---|---|
| EXAONE (K-EXAONE 2.0, K-EXAONE, 4.5, 4.0.1) | 없음 | 없음 | 없음 | 없음 | **없음**(전용 엔드포인트만) | 매핑 없음 |
| Kanana-2 (`kakaocorp/kanana-2-30b-a3b-*-2601`) | 없음 | 없음 | 없음 | 없음 | 없음 | 매핑 없음 |
| HyperCLOVA X SEED (`naver-hyperclovax/HyperCLOVAX-SEED-Think-32B` 등) | 없음 | 없음 | 없음 | 없음 | 없음 | 매핑 없음 |
| Mi:dm 2.0 (`K-intelligence/Midm-2.0-*`) | 없음 | 없음 | 없음 | 없음 | 없음(전용 엔드포인트 안내만) | 매핑 없음 |
| A.X (`skt/A.X-K2`, K1, 4.0) | 없음 | 없음 | 없음 | 없음 | 없음 | 매핑 없음 |
| (상용) Upstage Solar | `upstage/solar-pro4`, `upstage/solar-pro-3`(제공자는 Upstage 하나, logprobs·seed 미지원) | 없음 | 없음 | 없음 | 없음 | — |

→ **조사한 5개 호스팅 서비스 어디에서도 한국 회사의 공개 가중치 모델을 종량제로 부를 수 없다.** 한국어 공개 모델로 logprobs를 얻으려면 자체 GPU 또는 GPU 시간 임대(FriendliAI 전용 엔드포인트 H100 $3.9→$5.0/시간 등)가 필요하다. HyperCLOVA X SEED Think 32B의 라이선스는 자체 "HyperCLOVA X SEED 32B Think Model License"이며, 한국어 벤치마크(KoBALT·CLIcK·HAERAE)는 모델 카드에 그림으로만 있어 수치는 미확인(기술 보고서 arXiv 2601.03286).

### 5.2 호스팅 서비스별 요약

| 서비스 | 대표 다국어 모델 ID · 가격 (USD/MTok, 입력/출력) | 출력 logprobs | 프롬프트 logprobs (echo) | seed · temperature | 버전 고정 · 폐기 | 기타 |
|---|---|---|---|---|---|---|
| **OpenRouter** (중개) | `qwen/qwen3.5-397b-a17b` 0.55/3.50(최저 제공자 0.39/2.34), `deepseek/deepseek-v4-flash` 0.047/0.095, `google/gemma-4-31b-it` 0.09/0.34, `meta-llama/llama-3.3-70b-instruct` 0.10/0.32, `qwen/qwen3-235b-a22b-2507` 0.087/0.35 | 파라미터 `logprobs`(bool)·`top_logprobs`(0~20) 있음. **지원 여부는 제공자별로 다름**: 전체 447개 모델 중 156개가 지원. 예) gemma-4-31b-it는 14개 제공자 중 CoreWeave·Venice·Novita·Parasail만, deepseek-v4-flash는 StreamLake·DigitalOcean·Parasail·Mancer 2만 | 문서에 `echo`·prompt logprobs 파라미터 없음(미지원으로 판단) | `seed` 있음("일부 모델은 결정성 보장 안 됨"). temperature 0~2. 파라미터를 생략하면 제공자 기본값이 적용 | 기본은 **가격 기준 제공자 부하 분산** → 같은 모델 ID라도 제공자·양자화(fp4/fp8/bf16)가 요청마다 바뀔 수 있음. `provider.order`+`allow_fallbacks:false`, `require_parameters:true`(logprobs 미지원 제공자 제외), `quantizations` 필터로 고정해야 함. 날짜 박힌 ID(`deepseek-v4-flash-0731`, `qwen3.5-plus-20260420`)도 있으나 `~…-latest` 별칭은 바뀜 | 크레딧 구매 수수료 5.5%(최소 $0.80), 추론 단가는 제공자 가격 그대로. `data_collection:"deny"`·`zdr:true`로 데이터 보존 제공자 제외 가능. `:batch` 변형 일부 존재 |
| **Together AI** | `Qwen/Qwen3.5-9B` 0.17/0.25(FP8), `deepseek-ai/DeepSeek-V4-Flash-0731` 0.14/0.28(FP4), `openai/gpt-oss-120b` 0.15/0.60, `meta-llama/Llama-3.3-70B-Instruct-Turbo` 1.04/1.04(FP8), `zai-org/GLM-5.3-Flash` 0.15/0.50 | `logprobs`(정수 0~20, top-k) 지원 — chat·completions 모두 | **있음**: `echo: true` + `logprobs` → "prompt logprobs 반환"(API 레퍼런스 명시) | `seed` 있음. temperature 설명은 "0-1" | 모델 표에 양자화 명시(FP4/FP8). 폐기 통지 정책 문서는 찾지 못함(미확인) | Batch API 최대 50% 할인(할인 대상 모델 한정), 24시간 창. 주의: OpenRouter 경유 시 Together 엔드포인트는 logprobs 미지원으로 표시됨 → **직접 호출해야 함**(모델별 실제 반환은 미검증) |
| **Fireworks AI** | `deepseek-v4-flash-0731` 0.22/0.66, `gpt-oss-120b` 0.15/0.60, `glm-5p3-flash` 0.15/0.50, `qwen3p8-max` 2.00/6.00. 개별 가격이 없는 모델은 크기별 단가(16B 초과 $0.90, MoE 56B 이하 $0.50) | `logprobs`(bool 또는 정수)·`top_logprobs` 지원, **상한은 배포의 `--max-logprobs`(기본 5)** | **있음**: `echo`(프롬프트 반환)·`echo_last`(마지막 N토큰) 파라미터 — chat·completions 모두 | `seed`("deterministic sampling"), temperature 있음 | 서버리스 모델은 **최소 2주 전 통지 후 제거 가능**(인기 모델은 더 길게) | 배치 추론 50%. Completions API(원시 프롬프트) 있음 |
| **Groq** | `openai/gpt-oss-120b` 0.15/0.60, `openai/gpt-oss-20b` 0.075/0.30, `qwen/qwen3.8-27b` 0.80/4.00. Llama 3.x는 "Contact Sales"(기업 전용) | **미지원 — `logprobs`·`top_logprobs`를 보내면 400** | 미지원 | temperature 0은 1e-8로 변환. seed 미확인 | 미확인 | 개발자 플랜 gpt-oss-120b 250K TPM / 1K RPM. 한국어 모델 없음 |
| **FriendliAI** (Model APIs) | 카탈로그 7종뿐: `zai-org/GLM-5.3` 1.26/3.96(10% 할인), `zai-org/GLM-5.3-Flash` 0.15/0.50, `google/gemma-4-31B-it` 0.14/0.40, `deepseek-ai/DeepSeek-V3.2` 0.50/1.50, `MiniMaxAI/MiniMax-M2.5` 0.30/1.20 | API 레퍼런스에 `logprobs`·`top_logprobs` 있음(단 OpenRouter 경유 Friendli 엔드포인트는 미지원 표시) | completions의 `echo`는 미확인 | `seed` 있음. 카탈로그의 기본값 temperature 1.0·top_p 1.0 | 카탈로그 JSON에 `deprecationDate` 필드(현재 모두 null). **EXAONE·K-EXAONE이 예고 없이 빠진 선례** | 전용 엔드포인트로는 EXAONE·Mi:dm 등 임의 HF 모델 배포 가능(GPU 시간 과금) |
| (참고) DeepSeek 공식 API | `deepseek-flash`(=V4.1-Flash) 0.15~0.30/0.60~1.20, `deepseek-v4-pro`(=V4-Pro-0813) 0.66~1.32/1.98~3.96 (시간대별 할인가~정가) | `logprobs`·`top_logprobs` 지원 | 미확인 | temperature 0~2, **thinking 모드에서는 temperature 무효**. seed 문서에 없음 | **별칭이 최신 버전으로 자동 교체**(구 ID `deepseek-v4-flash`는 이미 `deepseek-flash`로 라우팅) → 스냅샷 고정 불가 | 중국 사업자 — 데이터 정책 별도 검토 필요 |

한국어 근거(다국어 모델): 공식 한국어 수치는 대부분 각 모델 카드에 없다. 참고로 SKT A.X K2 공식 모델 카드의 비교표(thinking 모드)에 따르면 KMMLU-Pro / KoBALT / CLIcK는 DeepSeek-V4 Flash 78.8 / 75.3 / 89.6, Qwen3.5-397B-A17B 78.4 / 69.9 / 88.4, GLM-5.1 76.5 / 72.0 / 88.8, Kimi-K2.6 73.4 / 66.0 / 80.9, MiniMax M2.7 66.6 / 51.4 / 76.1이다(평가 주체가 경쟁사인 점에 유의).

출처 URL (모두 2026-09-19 확인)
- https://openrouter.ai/api/v1/models (공개 JSON) → 447개 모델·가격·`supported_parameters`(logprobs 지원 156개), 한국 모델은 Upstage 2종만
- https://openrouter.ai/api/v1/models/{author}/{slug}/endpoints (공개 JSON; gemma-4-31b-it, deepseek-v4-flash, qwen3.5-397b-a17b, qwen3.6-35b-a3b, llama-3.3-70b-instruct, solar-pro4) → 제공자별 양자화·가격·logprobs/seed 지원
- https://openrouter.ai/docs/api_reference/parameters.md → `seed`·`logprobs`·`top_logprobs` 정의, 생략 시 제공자 기본값
- https://openrouter.ai/docs/guides/routing/provider-selection.md → 가격 기준 부하 분산, `order`·`allow_fallbacks`·`require_parameters`·`quantizations`·`data_collection`·`zdr`
- https://openrouter.ai/docs/faq.md → 크레딧 구매 수수료 5.5%(최소 $0.80), 추론 가격 무마진
- https://docs.together.ai/docs/serverless/models.md → 서버리스 모델 ID·가격·양자화
- https://docs.together.ai/reference/chat-completions.md, https://docs.together.ai/reference/completions.md → `logprobs`(0~20), `echo`("prompt logprobs 반환"), `seed`
- https://docs.together.ai/docs/inference/chat/logprobs.md → logprobs 사용법, "모델 계열 간 logprob 크기는 직접 비교 불가"
- https://docs.together.ai/docs/inference/batch/overview.md → 배치 최대 50% 할인, 24시간 창
- https://docs.fireworks.ai/serverless/pricing.md → 서버리스 단가·크기별 단가·배치 50%
- https://docs.fireworks.ai/serverless/overview.md → 서버리스 모델 제거 최소 2주 전 통지
- https://docs.fireworks.ai/api-reference/post-completions.md, https://docs.fireworks.ai/api-reference/post-chatcompletions.md → `logprobs`·`top_logprobs`(상한 기본 5)·`echo`·`echo_last`·`seed`
- https://console.groq.com/docs/openai.md → `logprobs`·`top_logprobs`·`logit_bias` 400 오류, temperature 0→1e-8
- https://console.groq.com/docs/models.md → 모델·가격·개발자 플랜 한도, Llama 기업 전용
- https://api.friendli.ai/serverless/v1/models, https://friendli.ai/api/public/model-apis → 종량제 카탈로그 7종·가격·기본 파라미터·`deprecationDate`
- https://friendli.ai/docs/openapi/model-apis/chat-completions.md, https://friendli.ai/docs/openapi/model-apis/completions.md → `logprobs`·`top_logprobs`·`seed`
- https://huggingface.co/api/models/{id}?expand[]=inferenceProviderMapping → 한국 공개 모델 10종 모두 추론 제공자 매핑 없음(대조: Llama-3.3-70B·Qwen3.5-9B는 매핑 있음)
- https://huggingface.co/naver-hyperclovax/HyperCLOVAX-SEED-Think-32B → 자체 라이선스, 벤치마크는 그림
- https://api-docs.deepseek.com/api/create-chat-completion, https://api-docs.deepseek.com/quick_start/pricing → DeepSeek 공식 모델 ID·가격·logprobs·thinking 모드 temperature 무효·구 ID 라우팅
- https://huggingface.co/skt/A.X-K2 → 다국어 모델의 한국어 비교 수치(참고)

---

## 6. 실험 설계에 영향을 주는 발견 (1–5절 종합)

### 6.1 temperature를 고정할 수 없는 모델

| 구분 | 모델 |
|---|---|
| **temperature 지정 자체가 불가(기본값만)** | `claude-fable-5-1`·`claude-opus-5`·`claude-sonnet-5`(1.0 외 값은 400), `gpt-6-astra`(파라미터 제거 지시), `gemini-3.8-flash`(이관 가이드가 temperature·top_p·top_k 제거 지시), DeepSeek 공식 API의 thinking 모드("효과 없음") |
| 공식 문서로 확정 못 함 | `gpt-5.6-sol`·`-luna`·`-terra`(제3자 보고로는 effort `none`에서만 허용 가능성), `gemini-3.1-pro-preview`·`gemini-3.5-flash-lite`(설정은 되지만 "1.0 유지 강력 권고") |
| **지정 가능** | `claude-haiku-4-5`(0~1, 단 Python SDK v1.0+는 인자를 제거해 원시 HTTP 필요), `HCX-007`·`HCX-005`·`HCX-DASH-002`(0~1, **seed도 있음**), Solar Pro 4/3/2(0~2, seed 없음, frequency_penalty 기본 1.1이라 명시 필요), 호스팅 공개 모델(0~2, seed는 제공자별) |

함의: 프런티어 상용 모델 대부분에서 "temperature 0 + 반복 1회" 설계가 불가능하다. **모든 모델을 공급자 기본 샘플링으로 두고 반복(예: 5회)으로 분포를 추정하는 설계**가 공통 분모다. temperature를 조작 변인으로 쓰려면 비교 대상이 HCX·Solar·Haiku 4.5·공개 모델로 좁아진다.

### 6.2 추론(thinking)을 끌 수 없는 모델

- **끌 수 없음**: `claude-fable-5-1`(항상 켜짐), `gpt-6-astra`(effort 최저 `low`), `gemini-3.8-flash`·`gemini-3.1-pro-preview`(항상 켜짐, 최저 `low`). `gemini-3.5-flash-lite`의 `minimal`도 "사고 꺼짐을 보장하지 않음".
- **끌 수 있음**: Opus 5·Sonnet 5(effort `high` 이하에서 `disabled`), Haiku 4.5(기본 꺼짐), GPT-5.6(`none`), HCX-007(`none` — 그리고 **Structured Outputs를 쓰려면 반드시 `none`**), Solar Pro 4(기본 꺼짐), 공개 모델(`enable_thinking` 등).
- 함의: 추론 켬/끔이 모델 간 교란 변인이 된다. 추론 조건을 요인으로 명시하거나, 끌 수 있는 모델끼리 비교군을 따로 묶어야 한다. 추론 토큰은 모두 출력 토큰으로 과금된다.

### 6.3 logprobs를 주는 곳과 안 주는 곳

| 출력 logprobs | 프롬프트 logprobs(echo, surprisal용) |
|---|---|
| **줌**: Together(0~20), Fireworks(상한 기본 5), OpenRouter의 일부 제공자(요청에 `require_parameters:true` 필요), FriendliAI(문서상), DeepSeek 공식 API | **줌**: **Together**(`echo`+`logprobs`, 문서 명시), **Fireworks**(`echo`, `echo_last`) |
| **안 줌**: Anthropic 전 모델, `gpt-6-astra`, Upstage Solar(응답 필드 "not yet available"), CLOVA Studio(OpenAI 호환 API에서 "미지원" 명시), Groq(보내면 400). 미확인: GPT-5.6, Gemini 3.x(API 필드는 있으나 최신 모델 미지원 사용자 보고) | 안 줌/미확인: OpenRouter(파라미터 없음), 모든 상용 API |

함의: surprisal 확장은 **다국어 공개 모델(Qwen·DeepSeek·GLM·Llama·gpt-oss 등)을 Together/Fireworks에 직접 호출하는 경로로만 가능**하다. 한국 회사 공개 모델로 surprisal을 재려면 GPU(전용 엔드포인트 임대 포함)가 필요하다. 상용 모델의 평정은 텍스트 응답(생성된 숫자)으로만 받을 수 있으므로, 평정 분포는 logprobs가 아니라 반복 샘플의 빈도로 추정해야 한다. logprobs 값은 "모델 계열 간 크기를 직접 비교할 수 없다"(Together 문서).

### 6.4 한국 회사 중 개인이 실제로 API를 쓸 수 있는 곳

| 회사 | 개인 종량제 API | 비고 |
|---|---|---|
| **Upstage** | **가능**(이메일 가입 + 신용카드, 후불 또는 선불, 최소액 없음) | OpenRouter로도 호출 가능 |
| **NAVER** | **가능성 높음**(네이버 클라우드 플랫폼 "개인 회원" 가입 유형 존재, 콘솔 이용 신청만 요구) | "개인도 CLOVA Studio 사용 가능" 명시 문구·결제 수단 필수 여부는 미확인 → 가입해서 직접 확인 필요 |
| LG(EXAONE) | 불가 | Showroom은 기업 전용, FriendliAI 종량제에서도 빠짐 |
| Kakao(Kanana) | 불가 | 유일한 API는 2026-05-27 종료된 클로즈드 베타 |
| KT(Mi:dm) | 불가(확인된 셀프서비스 없음) | 기업 상담 |
| SKT(A.X) | 불가 | 경진대회 참가자·선정 스타트업 한정 |

함의: "한국어 특화 상용 모델" 비교군은 현실적으로 **HCX-007(또는 HCX-005/DASH-002)과 Solar Pro 4/3 두 계열**이다. EXAONE·Kanana·Mi:dm·A.X를 넣으려면 GPU 임대 예산이 따로 필요하다.

### 6.5 스냅샷 고정

- **강함**: Anthropic("모든 모델 ID는 고정 스냅샷", 폐기 60일 전 통지, 모델별 최소 유지일 공개). 단 `claude-haiku-4-5-20251001`은 "2026-10-15 이전은 아님"이라 실험 기간 중 폐기 공지 가능.
- **중간**: OpenAI(GA 폐기 6개월 전 통지, 날짜 박힌 스냅샷은 gpt-5.5/5.4 계열에만 있고 현행 Astra·5.6은 날짜 없는 단일 스냅샷), Upstage(`solar-pro4-260806` 등 **날짜 스냅샷 지정 가능**, 그러나 `solar-pro3-260126`은 약 3개월 만에 폐기됐고 통지 기간 정책 없음), Google(stable ID, 날짜 스냅샷 없음, 폐기일은 "가장 이른 가능 날짜" 표기), NAVER(`HCX-007` 모델명 고정, 폐기 정책 문서 없음).
- **약함**: DeepSeek 공식(별칭이 최신 모델로 자동 교체), OpenRouter 기본 라우팅(제공자·양자화가 요청마다 바뀔 수 있음 → `provider.order`·`allow_fallbacks:false`·`quantizations`로 고정하고 응답의 제공자를 기록), Fireworks(서버리스 모델 2주 통지 후 제거), FriendliAI(EXAONE을 카탈로그에서 뺀 선례).
- 함의: 실험 로그에 **요청 모델 ID, 응답의 `model` 필드(Upstage는 스냅샷명 반환), 제공자명, 호출 일시**를 모두 저장하고, 가능한 곳은 날짜 스냅샷 ID로 호출한다. 짧은 기간에 모든 모델을 몰아 실행하는 것이 가장 확실한 고정 수단이다.

### 6.6 비용 규모 — 문항 400개 × 반복 5회 × 모델 1개 = 2,000회 호출

가정(측정값 아님): 호출당 입력 500토큰(지시문·맥락·문장·선택지), 최종 답 20토큰(JSON 한 줄). 추론 토큰은 시나리오로 나눴다: A = 추론 끔(출력 20), B = 추론 약 300토큰(출력 320), C = 추론 약 1,000토큰(출력 1,020). 총량: 입력 1.0 MTok, 출력 A 0.04 / B 0.64 / C 2.04 MTok. 한국어 토큰 수는 토크나이저마다 크게 달라 이 가정이 틀릴 수 있다 → 본 실험 전에 각 사의 토큰 계산 기능(CLOVA 토큰 계산기 API, Upstage Counting tokens 가이드 등)으로 실제 자극문을 재어 단가에 곱할 것.

| 모델 (표준 단가) | A 추론 끔 | B 추론 ~300 | C 추론 ~1,000 |
|---|---|---|---|
| `claude-opus-5` ($5/$25) | $6.00 | $21.00 | $56.00 |
| `claude-sonnet-5` ($2/$10) | $2.40 | $8.40 | $22.40 |
| `claude-haiku-4-5` ($1/$5) | $1.20 | $4.20 | $11.20 |
| `claude-fable-5-1` ($10/$50) | 불가(추론 필수) | $42.00 | $112.00 |
| `gpt-6-astra` ($10/$50) | 불가(추론 필수) | $42.00 | $112.00 |
| `gpt-5.6-sol` ($4/$20, 프로모션가) | $4.80 | $16.80 | $44.80 |
| `gpt-5.6-luna` ($0.20/$1.20) | $0.25 | $0.97 | $2.65 |
| `gemini-3.8-flash` ($0.75/$3.75 도입가 → 2027 $1.50/$7.50) | 불가(추론 필수) | $3.15 → $6.30 | $8.40 → $16.80 |
| `gemini-3.1-pro-preview` ($2/$12) | 불가(추론 필수) | $9.68 | $26.48 |
| `HCX-007` (1,250원/5,000원, VAT 별도) | 1,450원 | 4,450원 | 11,450원 |
| `HCX-DASH-002` (250원/1,000원) | 290원 | 890원 | 2,290원 |
| `solar-pro4` 정가 ($0.30/$1.20) · 할인가(~10-09) | $0.35 · $0.10 | $1.07 · $0.32 | $2.75 · $0.82 |
| `solar-pro3` ($0.15/$0.60) | $0.17 | $0.53 | $1.37 |
| `qwen/qwen3.5-397b-a17b` OpenRouter 목록가 ($0.55/$3.50) | $0.69 | $2.79 | $7.69 |
| `deepseek/deepseek-v4-flash` OpenRouter ($0.047/$0.095) | $0.05 | $0.11 | $0.24 |
| `openai/gpt-oss-120b` Together·Fireworks·Groq ($0.15/$0.60) | $0.17 | $0.53 | $1.37 |

- 배치 API를 쓰면 Anthropic·OpenAI·Google·Fireworks는 위 금액의 절반(24시간 창), Together는 할인 대상 모델만 최대 50%. CLOVA Studio·Upstage는 배치 할인 문서 미확인.
- 비용보다 **한도가 병목**이 될 수 있다: OpenAI Tier 1은 월 사용 한도 $100(Astra C 시나리오 1회분 $112가 초과), Google Tier 1은 10분당 $10 지출 한도, CLOVA HCX-007 일반 키 60 QPM(2,000회에 최소 약 34분), Upstage Tier 0 100 RPM.
- 가격 기한: Solar Pro 4 할인은 2026-10-09까지, Gemini 3.8 Flash 도입가는 2026-12-31까지, GPT-5.6 Sol 프로모션가는 "최소 2026-11-21까지". 실행 시점에 따라 단가가 바뀐다.
- 결론적으로 모델 1개·2,000회 호출은 추론을 끌 수 있는 모델이면 대부분 **$0.1~$6(HCX는 약 1,500원)**, 추론이 강제되는 최상위 모델은 **$40~$110 이상**이다. 비용의 대부분은 추론 토큰이 결정한다.

### 6.7 그 밖의 설계 제약

- 구조화 출력의 스키마 제약이 회사마다 다르다: Anthropic은 `minimum`/`maximum` 미지원 → Likert는 `enum: [1..7]`, CLOVA는 `pattern` 미지원·추론과 동시 사용 불가, Upstage·OpenAI는 strict 모드(모든 필드 `required`, `additionalProperties:false`). 공통 분모는 **`enum`으로 선택지를 고정한 JSON 한 줄**이다.
- assistant prefill(응답 앞부분 강제)은 Opus 5·Sonnet 5에서 400, Gemini 3.8 Flash에서 제거 지시 → prefill에 의존하는 응답 형식 유도는 쓰지 않는다.
- 데이터 사용: Gemini 무료 등급은 입력을 제품 개선에 사용, Upstage Playground도 모델 개선에 쓰일 수 있음 → 자극문은 유료 API로만 보낸다. OpenRouter는 `data_collection:"deny"`로 보존 제공자를 제외할 수 있다.

