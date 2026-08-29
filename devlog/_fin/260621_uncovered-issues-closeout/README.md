# Uncovered Issues Closeout — 2026-06-21

Devlog 체계 확립(#45, 2026-04-29) 이후 closed된 이슈 중 별도 devlog 없이 커밋으로 해결된 건들의 일괄 기록.

---

## #42 — Gallery UX: default gallery to current session with All images toggle
- **Closed**: 2026-04-30
- **Resolution**: 갤러리 기본 뷰를 현재 세션으로 변경, "All images" 토글 추가. UI 스토어 + 갤러리 컴포넌트 수정.

## #43 — Generation settings: audit persisted controls across mobile and desktop
- **Closed**: 2026-04-30
- **Resolution**: 모바일/데스크탑 간 생성 설정 영속화 감사. localStorage 키 통일 및 누락 컨트롤 보완.

## #46 — Canvas Mode: add visible white canvas source for Paint-to-AI flow
- **Closed**: 2026-04-30
- **Resolution**: 캔버스 모드에 빈 흰색 캔버스 소스 추가. Paint-to-AI 워크플로 진입점 제공.

## #49 — Backend: enable provider:'api' image generation via Responses image_generation tool
- **Closed**: 2026-04-30
- **Resolution**: OpenAI Responses API의 image_generation 도구를 통한 provider:api 모드 구현. 기존 DALL-E 직접 호출과 병행.

## #54 — Generation: implement true in-flight cancellation
- **Closed**: 2026-05-07
- **Resolution**: 생성 중 취소 시 서버 측 AbortController 연동. SSE 스트림 즉시 종료 + UI 상태 롤백.

## #55 — GPT-5.5 Instant 지원
- **Closed**: 2026-05-07
- **Resolution**: 서버사이드 모델 목록에 GPT-5.5 Instant 추가. 별도 코드 변경 없이 모델 레지스트리 업데이트.

## #56 — bug(cli): --out/--out-dir remains empty when generation completes after client timeout
- **Closed**: 2026-05-07
- **Resolution**: CLI 클라이언트 타임아웃 후에도 서버가 파일 저장을 완료하도록 수정. 폴링 기반 완료 확인 추가.

## #73 — API GET endpoints can return 304 due to ETag, causing UI error after generation
- **Closed**: 2026-05-23
- **Resolution**: ETag 캐싱에 의한 304 응답 시 UI에서 빈 데이터로 처리되던 문제 수정. Cache-Control 헤더 조정.

## #82 — VPS/headless 환경에서 ima2 grok login 수동 코드 입력 흐름
- **Closed**: 2026-05-31
- **Resolution**: headless 환경에서 브라우저 없이 device code flow로 Grok OAuth 인증. `devlog/_plan/260608_grok-url-continue` 참조.

## #83 — CI: add nix flake check to GitHub Actions
- **Closed**: 2026-05-31
- **Resolution**: GitHub Actions에 nix flake check 스텝 추가. `flake.nix` + CI 워크플로 수정.

## #89 — fix: show source provenance in UI when auto-selecting I2V source
- **Closed**: 2026-06-01
- **Resolution**: I2V 소스 자동 선택 시 출처 정보 UI 표시. `devlog/_plan/260611_agent-source-policy-progress` 참조.

## #91 — fix: Ctrl+C on Windows leaves file locks (EBUSY on npm update)
- **Closed**: 2026-06-01
- **Resolution**: Windows에서 SIGINT 핸들링 시 파일 잠금 해제 로직 추가. graceful shutdown 보강.

## #92 — fix: cross-platform audit — SIGKILL, path.isAbsolute, spawn error handlers
- **Closed**: 2026-06-01
- **Resolution**: 크로스플랫폼 감사 — SIGKILL→SIGTERM fallback, path.isAbsolute 호환, spawn 에러 핸들러 통일.
