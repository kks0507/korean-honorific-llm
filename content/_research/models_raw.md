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

