# Fix Plans — QA 발견 이슈별 수정 계획

- Date: 2026-06-10
- 결과 근거: `10_qa-results.md`
- 요약: **ima2-gen 앱 자체 결함 0건.** 발견 이슈 4건은 전부 QA 인프라/환경(CU 런타임, grok CLI, CU 리사이즈) 또는 QA 절차 문제. 각각 root-cause 추정과 수정 계획을 기록.

---

## ISSUE-1 — A7 false FAIL (QA 절차 결함)

- **증상**: Control(CU)이 "메뉴 밖 스크롤 후에도 메뉴 잔존"으로 A7 FAIL 보고
- **교차 검증**: Boss CDP 실측에서 `.sidebar__scroll` 실제 스크롤·`.history-strip` 스크롤 모두 메뉴 정상 닫힘 → 앱 동작은 정상 (`ImageModelSelect.tsx:144-147`의 close 리스너 동작 확인)
- **Root cause 추정** (우선순위순):
  1. CU `scroll` 액션이 화면 중앙 기준으로 **열린 메뉴 자체**를 스크롤 — b735565 이후 메뉴 내부 스크롤은 의도적으로 메뉴를 유지하므로, 잔존이 오히려 올바른 동작
  2. 스크롤 대상 영역에 오버플로가 없어 scroll 이벤트 자체가 미발생 (이벤트 없으면 close 미호출은 정상)
  3. 스크롤 후 stale a11y 스냅샷 판독
- **수정 계획** (QA 절차 — `00_plan.md` 차기 rev에 반영):
  - A7 절차를 "사이드바 영역에 마우스 커서를 올린 뒤 스크롤" + "스크롤 대상에 오버플로 존재 확인 선행"으로 구체화
  - CU 한계로 스크롤 타겟팅이 불확실하면 A7은 BLOCKED(scroll targeting) 처리하고 CDP 교차 검증을 표준 경로로 명시
- **코드 수정**: 불필요

## ISSUE-2 — Computer Use 런타임 비활성 (환경, Part B 차단 원인)

- **증상**: `get_app_state(app="Google Chrome")`은 성공하나 직후 `click`/`press_key`/`set_value`가 `Computer Use is not active for 'Google Chrome'. You first must call get_app_state...` 오류로 차단. 새 디스패치(새 codex 세션)에서도 재현. 단 Part A 디스패치(약 30분 전)에서는 동일 패턴이 정상 동작했고, 재시도 디스패치에서 `set_value`만 간헐 성공 → **세션 중 활성 상태가 즉시 소실되는 불안정 상태**
- **Root cause 추정**:
  1. CU MCP 서버의 앱별 활성 토큰(activation lease)이 state-read 후 액션 사이에 만료/소실 — Part A 후반(드래그 4연속 실패) 즈음부터 불안정해진 시계열과 일치
  2. macOS TCC(손쉬운 사용/자동화) 권한 세션이 끊겼거나, cli-jaw 서버/codex 프로세스가 Terminal 권한 컨텍스트 밖에서 재기동됨
  3. Chrome 창 식별 불일치 (CDP 자동화 Chrome과 일반 Chrome이 공존할 때 CU가 바라보는 창과 활성 등록된 창이 다름)
- **수정 계획** (순서대로, 각 단계 후 스모크 테스트):
  1. 스모크 테스트 정의: Control에 `$computer-use`로 "list_apps → get_app_state(Finder) → Finder 창 1회 클릭" 최소 시나리오 디스패치 → 통과 여부로 CU 레이어 자체 건강 판정
  2. 실패 시: cli-jaw 서버를 Terminal(자동화 권한 보유 컨텍스트)에서 재시작 → 시스템 설정 > 개인정보 보호 및 보안 > 손쉬운 사용/자동화에서 해당 터미널·codex 프로세스 권한 확인/재부여 (사용자 액션 필요 — Boss가 단독 수행 불가)
  3. Chrome 혼선 제거: QA 시 CDP 자동화 Chrome(`cli-jaw browser`)을 종료한 상태에서 CU QA 수행하거나, CU에 창 타이틀로 대상 창을 명시
  4. 복구 확인 후 Part B(B1–B8) 재디스패치 (체크리스트 `00_plan.md` 그대로 재사용)
- **코드 수정**: ima2-gen 없음. cli-jaw/CU 쪽 진단은 별건

## ISSUE-3 — 니지카(grok CLI) 디스패치 실패 (환경)

- **증상**: `cli-jaw dispatch --agent 니지카` 가 `Couldn't create session: Session does not exist` 로 2회 연속 즉사 (당일 오전에는 정상 동작했음 — 드롭다운 수정 감사 수행 이력 있음)
- **Root cause 추정**: grok CLI 인증 세션 만료 또는 grok 서비스 측 세션 무효화. CLI 업데이트로 인한 세션 스토어 비호환 가능성도 있음
- **수정 계획**:
  1. `grok` CLI 단독 실행으로 재현 확인 → 인증 상태 확인/재로그인 (사용자 액션 필요 가능)
  2. 복구 전까지 UI 감사 디스패치는 세이카/료(cursor)로 우회 (이번 세션에서 적용한 방식, 보고서에 명시)
  3. 반복되면 `/employee cli 니지카 <cli>` 변경은 사용자 결정 사항으로 제안만
- **코드 수정**: 없음

## ISSUE-4 — CU 창 리사이즈 불가 (환경/도구 한계, A5·A6 차단 원인)

- **증상**: CU `drag`로 Chrome 창 모서리 드래그 시 `windowNotFoundAtPosition` 반복, 창 크기 변경 실패
- **Root cause 추정**: CU drag가 창 프레임 바깥 좌표(데스크톱 영역)를 대상으로 할 때 대상 창 해석 실패 — 창 경계 드래그는 CU 액션 모델의 약점
- **수정 계획** (QA 런북 — 차기 CU QA부터 적용):
  1. 창 리사이즈는 drag 대신 **osascript**로 수행: `osascript -e 'tell application "Google Chrome" to set bounds of front window to {0, 0, 900, 560}'` — Boss가 디스패치 전에 창 크기를 미리 세팅해주고 CU는 검증만 담당
  2. 또는 해당 항목을 CDP 실측(`cli-jaw browser resize`)을 표준 경로로 격상 (이번에 A5/A6 PASS(보조)로 처리한 방식)
- **코드 수정**: 불필요

---

## 재검 체크리스트 (CU 복구 후)

1. ISSUE-2 수정 계획 1–3 수행 → 스모크 PASS
2. osascript로 창 900×560 세팅 → Part A의 A5/A6/A7만 재디스패치 (CU 실측 승격)
3. Part B(B1–B8) 재디스패치
4. 결과를 `10_qa-results.md`에 추기

---

## 이슈 상태 업데이트 (2026-06-10 재검 라운드 후)

| 이슈 | 상태 | 비고 |
|------|------|------|
| ISSUE-1 (A7 QA 절차) | **종결 — 검증 불가 항목으로 확정** | 재검에서도 CU FAIL 재현. CDP 실측: 좁은 창(900×520)에서 메뉴 rect [12,68,292,508]가 사이드바 rect [0,0,259,520]를 12px 띠만 남기고 덮음 → 포인터 기반 "메뉴 밖 사이드바 스크롤" 자체가 불성립. 앱 동작은 CDP 이벤트 실측으로 정상(닫힘) 확인. 차기 QA부터 A7은 CDP 표준 경로 |
| ISSUE-2 (CU 런타임) | **해소** | 사용자 환경 패치 후 스모크 PASS, A/B 재검 전 라운드에서 `Computer Use is not active` 미재발 |
| ISSUE-3 (니지카/grok CLI) | **미해결 (사용자 액션 대기)** | 재검 라운드 헬스체크 디스패치에서도 `Couldn't create session: Session does not exist` 동일 재현. grok CLI 재로그인 필요. 복구 전 감사·UI 검증 디스패치는 세이카/료 우회 |
| ISSUE-4 (CU 창 리사이즈) | **해소 (우회안 채택)** | osascript bounds 사전 세팅을 실전 적용해 A5/A6 CU 재검 성공. QA 런북 표준으로 채택 |

## 최종 결론

- ima2-gen 앱 코드 패치 필요 사항: **없음** (QA 전 항목 PASS, 결함 0건)
- 잔여 액션: grok CLI 재로그인(ISSUE-3, 사용자) 1건
