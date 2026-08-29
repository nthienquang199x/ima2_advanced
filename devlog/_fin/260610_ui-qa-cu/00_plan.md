# Plan — ima2-gen UI 수동 QA (Computer Use via Control) — rev2

- Date: 2026-06-10 (rev2 — 1차 감사 FAIL 반영: B6 절차, A4 Gemini 예외, 전제조건/BLOCKED 기준 확장, 라벨 정정)
- Class: C2 (QA 실행 + 문서 산출, 코드 변경 없음)
- Trigger: 사용자 지시 — "컨트롤 직원에게 CU 시키고 QA 리스트 만들고 devlog 폴더 하나 만들고 기록. 에러는 수정 계획까지."
- 직전 컨텍스트: 사이드바 모델 드롭다운 스크롤/오버플로 수정 커밋 `b735565`

## Scope

- 대상: http://localhost:3333 (ima2-gen UI, b735565 반영 빌드)
- 수행 주체: Control 직원 (codex) — `$computer-use` 디스패치, 실제 마우스/키보드 조작
- 산출물: 본 폴더에 체크리스트(본 문서), 결과(`10_qa-results.md`), 이슈별 수정 계획(`20_fix-plans.md`)
- 제외: 실제 이미지/비디오 생성, 코드 수정(계획까지만)
- 보조 검증(선택): Boss가 CDP로 콘솔 에러 수집 — CU 경로와 별개 작업

## 공통 전제 (CU 시작 절차)

- P0. Chrome에서 http://localhost:3333 접속 (창 없으면 Chrome 실행부터)
- P1. **온보딩/인증 팝업**이 떠 있으면 먼저 dismiss ("알아서 진행" 등 닫기 경로 사용). dismiss 불가하면 이후 항목 전부 BLOCKED(onboarding) 처리
- P2. 갤러리에 **히스토리 이미지 ≥1** 존재 확인. 없으면 B6/B7은 BLOCKED(empty gallery)
- P3. 화면이 사이드바+중앙 캔버스 기본 레이아웃인지 확인. 프롬프트 입력창이 사이드바가 아닌 **하단**에 있으면(prompt-studio 프로필) 그 위치 기준으로 B1 수행하고 결과에 레이아웃 명시

## QA Checklist

판정: PASS / FAIL / BLOCKED(+사유) / N/A(+사유). FAIL은 재현 절차 + 관찰 내용 필수. 확인 불가 시 추측 PASS 금지 — BLOCKED로.

### Part A — 모델 드롭다운 (b735565 회귀 검증 핵심)
| # | 항목 | 기대 결과 |
|---|------|-----------|
| A1 | 앱 로드 | 사이드바 + 중앙 영역 렌더, 에러 오버레이(ErrorCard) 없음 |
| A2 | 모델 pill 클릭 (aria "모델과 추론 강도 선택…") | 드롭다운 열림: "이미지"(GPT-IMAGE/Grok Imagine/Gemini 서브섹션), "비디오", "추론" 섹션 |
| A3 | 다른 이미지 모델 선택 | 메뉴 닫힘 + pill 라벨이 선택 모델로 갱신 |
| A4 | "추론" 토글 펼침 → effort 변경 | 접기/펼치기 동작, 선택 시 pill 하단 effort 라벨 갱신. **단, Gemini 이미지 모델 선택 상태면 "추론" 섹션이 원래 없음 → N/A(Gemini). GPT/Grok 모델로 바꾼 뒤 수행** |
| A5 | **좁은 창**: 창 세로를 ~500–600px로 줄인 뒤 드롭다운 열기 | 메뉴 하단이 화면 안(잘리지 않음) |
| A6 | **좁은 창**: 드롭다운 내부에서 스크롤 | 메뉴 안에서 스크롤되어 하단 항목("추론" 등)이 보이고, **스크롤 중 메뉴가 닫히지 않음** |
| A7 | 메뉴 연 채 사이드바(메뉴 밖) 스크롤 | 메뉴 닫힘 (기존 동작 보존) |

### Part B — 주요 UI 플로우
| # | 항목 | 기대 결과 |
|---|------|-----------|
| B1 | 프롬프트 textarea 입력/삭제 (위치는 P3 기준) | 한글/영문 입력 정상, 비우면 플레이스홀더 복원 |
| B2 | 탭 전환 (기본 ↔ 노드) | 탭 컨텐츠 전환, 빈 화면/freeze 없음 |
| B3 | 토글 3종: 비디오 모드(aria "비디오 모드 전환 (Grok 1.5)") / Direct(시각 텍스트 **"1:1"**, aria "프롬프트를 원문 그대로 전달 (Direct 모드)") / 검색(aria **"검색 켬"/"검색 끔"**) | 클릭 시 활성/비활성 시각 상태 토글 |
| B4 | 프롬프트 라이브러리 열기/닫기 (aria "프롬프트 라이브러리" / 닫기) | 패널 열리고 닫힘 |
| B5 | 설정 열기/닫기 (aria "설정 열기" / "설정 닫기") | 설정 화면 렌더(모델 select, 계정 섹션), 닫으면 복귀 |
| B6 | 갤러리 이미지 **클릭** → 중앙 포커스 뷰의 ResultActions | "다운로드"/"이미지 복사"/"여기서 이어서"/"애니메이트" 버튼 표시. (타일 hover에는 favorite/delete만 있음 — hover로 판정하지 말 것). 전제 P2 |
| B7 | 포커스 뷰에서 "캔버스 모드에서 이미지 열기" → 캔버스 렌더 → "캔버스 닫기" | 진입/종료 정상 복귀. 전제 P2 |
| B8 | 히스토리 스트립/사이드바 히스토리에서 다른 이미지 클릭 | 중앙 포커스 이미지 전환 |

## Execution Plan

1. **디스패치 1** (Control, `$computer-use`): P0–P3 + Part A (A1–A7)
2. **디스패치 2** (Control, `$computer-use`): P0 확인 + Part B (B1–B8)
3. Boss가 결과를 `10_qa-results.md`로 정리, FAIL/이슈마다 `20_fix-plans.md`에 root-cause 추정 + 수정 계획(파일:줄) 작성
4. 보조 검증(선택): Boss가 CDP로 콘솔 에러 수집해 첨부

## BLOCKED / N/A 기준

- 창 리사이즈 실패(A5/A6) → BLOCKED(resize). 추측 PASS 금지
- Chrome 부재 → Chrome 실행부터; 그래도 불가면 전체 BLOCKED(no browser)
- 온보딩/인증 팝업 dismiss 불가 → 이후 항목 BLOCKED(onboarding)
- 갤러리 비어 있음 → B6/B7/B8 BLOCKED(empty gallery)
- Gemini 모델 상태에서 A4 → N/A(Gemini) 후 GPT/Grok로 전환해 재시도
- 디스패치당 10분 제한 → Part A/B 분리

## 1차 감사 반영 이력 (rev2)

- B6: hover → 클릭+ResultActions로 절차 정정 (GalleryImageTile은 favorite/delete만)
- A4: Gemini 예외 N/A 추가 (`ImageModelSelect.tsx:303` 조건부 렌더)
- 전제 P1(온보딩)/P2(빈 갤러리)/P3(prompt-studio 레이아웃) 신설
- 라벨 정정: REASONING→"추론", Direct 시각 텍스트 "1:1", 검색 "검색 켬/끔"
- B8(히스토리 네비게이션) 추가 — 감사 권고 R4 반영
