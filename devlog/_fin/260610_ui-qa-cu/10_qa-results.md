# QA Results — ima2-gen UI 수동 QA (Computer Use via Control)

- Date: 2026-06-10
- 체크리스트: `00_plan.md` (rev2, 감사 PASS — 세이카)
- 수행: Control 직원(codex) `$computer-use` 디스패치 2회(Part A/B) + 재시도 1회, Boss CDP 보조 검증
- 대상: http://localhost:3333 (커밋 `b735565` 반영 빌드)

## Part A — 모델 드롭다운 (Control, CU 실측)

| # | 판정 (CU) | 관찰 | Boss 보조 검증(CDP) 반영 후 최종 |
|---|-----------|------|--------------------------------|
| A1 | PASS | 사이드바+중앙 뷰어 렌더, 에러 오버레이 없음. 온보딩 팝업 없음(P1 미발생), 갤러리 이미지 ≥1(P2 충족) | **PASS** |
| A2 | PASS | pill 클릭 → 이미지/비디오/추론 섹션 메뉴 열림 | **PASS** |
| A3 | PASS | 모델 선택 시 메뉴 닫힘 + pill 라벨 갱신 (5.4m→5.5 확인) | **PASS** |
| A4 | PASS | GPT 모델 상태에서 추론 펼침 → med 선택 → pill 라벨 'reasoning med' 갱신 | **PASS** |
| A5 | BLOCKED(resize) | CU drag로 창 리사이즈 반복 실패 (`windowNotFoundAtPosition`) | **PASS(보조)** — CDP 900×520 실측: menuBottom 508 ≤ 520, maxHeight 440px (`260610_model-dropdown-scroll/10_phase1-results.md`) |
| A6 | BLOCKED(resize) | 좁은 창 전제 미성립. 단 일반 창에서 메뉴 내부 스크롤 시 메뉴 유지는 관찰됨 | **PASS(보조)** — CDP: 내부 scrollBy 후 open 유지, scrollTop 140.5(최대) |
| A7 | FAIL | 메뉴 연 채 바깥 스크롤 후에도 a11y 트리에 menu 잔존 관찰 | **PASS — false FAIL 판정** (아래 교차 검증) |

### A7 교차 검증 (Boss, CDP — 본 세션 실측)

- 메뉴 연 상태에서 `.sidebar__scroll.scrollTop += 30` (실제 스크롤 이벤트 발생) → **메뉴 닫힘 확인**
- 메뉴 재오픈 후 `.history-strip` 스크롤(메인 영역) → **메뉴 닫힘 확인**
- 사이드바는 해당 창 크기에서 실제 스크롤 가능 상태였음 (scrollH 690 > clientH 633)
- false FAIL 추정 원인: CU `scroll` 액션이 (a) 메뉴 자체를 스크롤했거나(이 경우 유지가 **올바른** 동작 — b735565의 의도), (b) 오버플로 없는 영역을 대상으로 해 scroll 이벤트가 발생하지 않았거나, (c) 스크롤 후 stale a11y 스냅샷을 읽었을 가능성. 상세는 `20_fix-plans.md` ISSUE-1

## Part B — 주요 UI 플로우 (Control, CU)

| # | 판정 | 관찰 |
|---|------|------|
| B1 | 부분 확인 | `set_value`로 'QA 테스트 123' 입력/초기화 액션은 ok 응답. 단 a11y 트리에서 값 표시를 재확인 못 해 화면 검증 미완 |
| B2–B8 | **BLOCKED(CU runtime)** | `get_app_state`는 성공하나 `click`/`press_key`가 전부 `Computer Use is not active for 'Google Chrome'` 오류로 차단. 새 디스패치 재시도에서도 동일 재현 |

→ Part B는 CU 런타임 환경 이슈로 미완. 환경 이슈 분석/수정 계획은 `20_fix-plans.md` ISSUE-2. 재검 절차는 같은 문서 참조.

### Boss 보조 관찰 (CDP, 참고용 — CU 재검 대체 아님)

- 페이지 콘솔: 에러/경고 0건 (`cli-jaw browser console` 수집 결과 빈 로그)

## 디스패치 이력 / 환경 노트

- Part A: Control 1회 성공 수행 (A1–A4 실조작 완료, A5/A6 리사이즈 차단, A7 판정은 교차 검증으로 정정)
- Part B: Control 2회 모두 CU 액션 차단 (1회차 전체 차단, 재시도서 set_value 일부만 통과 후 click 차단)
- 별건: A 페이즈 플랜 감사에서 니지카(grok CLI) 디스패치가 `Couldn't create session` 으로 2회 연속 실패 → 세이카(cursor)로 대체 수행. grok CLI 환경 이슈는 ISSUE-3

## 종합 (1차 라운드 시점)

| 분류 | 항목 |
|------|------|
| PASS (CU 실측) | A1, A2, A3, A4 |
| PASS (CDP 보조/교차) | A5, A6, A7 |
| 미완 — 재검 필요 | B1(화면 확인), B2–B8 (CU 런타임 복구 후) |
| 앱 자체 결함 발견 | **0건** (A7은 false FAIL로 판정) |
| 환경 이슈 | CU 런타임 비활성(ISSUE-2), grok CLI 세션 실패(ISSUE-3), CU 창 리사이즈 불가(ISSUE-4) |

---

# 재검 라운드 (2026-06-10 21:4x — 사용자 CU 환경 패치 후)

사용자가 CU 환경을 복구한 뒤 `20_fix-plans.md` 재검 체크리스트를 수행. 창 사전 세팅은 ISSUE-4 우회안(osascript bounds) 적용.

## A5/A6/A7 재검 (Control, CU — 창 900×560 사전 세팅)

| # | 판정 (CU) | 관찰 | 최종 |
|---|-----------|------|------|
| 스모크 | PASS | get_app_state → 헤더 클릭 정상, `Computer Use is not active` 미재발 | CU 복구 확인 (ISSUE-2 해소) |
| A5 | PASS(트리 기반) | 좁은 창에서 메뉴 열림, REASONING 섹션까지 트리 노출. 픽셀 단위 잘림 판독은 CU 한계로 간접 판정 | **PASS** (CDP 픽셀 실측과 합치) |
| A6 | PASS | REASONING 펼침 + 메뉴 내부 스크롤 후에도 메뉴 유지, off/low/med/high/xhigh 노출 | **PASS (CU 실측 승격)** — 핵심 회귀 항목 |
| A7 | FAIL(CU) | 바깥 추정 요소(16/17) 스크롤에도 메뉴 유지 | **PASS — CU 측정 불가 판정.** 아래 결정적 교차 검증 |

### A7 결정적 교차 검증 (Boss, CDP 900×520 실측)

- 메뉴 rect [12, 68, 292, 508] vs 사이드바 rect [0, 0, 259, 520] → **메뉴가 사이드바를 왼쪽 12px 띠만 남기고 전부 덮음**. 좁은 창에서 포인터로 "메뉴 밖 사이드바 스크롤"을 만드는 것 자체가 물리적으로 거의 불가능 → CU FAIL은 구조적 타겟팅 아티팩트
- 같은 조건에서 `.sidebar__scroll` 실제 스크롤 이벤트 발생 시 → **메뉴 정상 닫힘** 재확인
- 결론: 앱 동작 정상. A7은 CU로는 좁은 창에서 검증 불가 항목으로 분류 (00_plan 차기 rev 반영 사항)

## Part B 재검 (Control, CU — 창 1400×900)

| # | 판정 | 관찰 요지 |
|---|------|-----------|
| B1 | **PASS** | set_value로 'QA 테스트 123' 입력 값 확인 → select_text+Delete로 제거 → 플레이스홀더 복원 확인 |
| B2 | **PASS** | Classic↔Node 전환·복귀, selected 상태 및 DOM 정상, 프리징 없음 |
| B3 | **PASS** | 비디오(0→1→0), Direct('PROMPT 1:1' 표시 후 복귀), 검색(on/off 복귀) 모두 정상 |
| B4 | **PASS** | Prompt Library 패널 열림(제목/검색/Close 확인) → 닫기 정상 |
| B5 | **PASS** | 설정 화면(WORKSPACE SETTINGS/Account/Generation/Image model/Web search) 렌더 → Close settings 복귀 |
| B6 | **PASS** | 갤러리(496 total) 썸네일 클릭 → 중앙 포커스 뷰에 Download/Copy image/Continue here/Animate/Open in canvas 노출 (hover 미사용) |
| B7 | **PASS** | Open in canvas → CANVAS MODE 렌더 → Close Canvas 복귀 |
| B8 | **PASS** | 다른 썸네일 클릭 시 메타데이터 변경(102.7s·34097tok → 480.1s·4388tok)으로 이미지 전환 확인 |

## 최종 종합

| 분류 | 항목 |
|------|------|
| PASS (CU 실측) | A1–A4, A5(트리)+A6 재검, B1–B8 |
| PASS (CDP 실측/교차) | A5(픽셀), A7 |
| 앱 자체 결함 | **0건** |
| 환경 이슈 잔여 | ISSUE-3(니지카/grok CLI)만 미해결 — 재검 라운드 헬스체크에서도 `Couldn't create session` 재현, grok 재로그인(사용자 액션) 필요 |
| 해소된 환경 이슈 | ISSUE-2(CU 런타임 — 사용자 패치로 복구 확인), ISSUE-4(osascript 우회안 실전 적용 성공) |
