# Feature 6: Network Settings UI

Verdict: **ADAPT**

## What

REST API로 allowExternalAccess 토글 (host 0.0.0.0 ↔ 127.0.0.1).
IMA2_HOST 환경변수 override 감지 시 UI disable.

## Files (전부 신규)

- `routes/networkSettings.ts` — GET/PUT /api/settings/network
- `ui/src/components/settings/NetworkAccessSettings.tsx` — 체크박스 토글

## Quality

- atomicWriteJson 사용
- restartRequired 비교 정확
- 환경변수 override UX 배려
- **보안 우려**: PUT에 인증 없이 0.0.0.0 바인딩 가능 → auth guard 추가 권장

## Cherry-pick Plan

1. 두 파일 cherry-pick
2. `config.storage.configFile` upstream 존재 확인
3. `ui/src/lib/api.ts`에 getNetworkSettings/updateNetworkSettings 추가
4. `SettingsWorkspace.tsx`에 컴포넌트 연결
5. PUT 엔드포인트에 local-only 또는 auth guard 추가
