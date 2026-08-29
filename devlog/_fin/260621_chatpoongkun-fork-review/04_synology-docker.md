# Feature 4: Synology Docker Deployment

Verdict: **PICK**

## What

Synology NAS (DS918+, amd64) 대상 Docker 배포 패키지.
Multi-stage build, tini init, node user, persistent /data volume.

## Files (전부 신규)

- `Dockerfile` — node:22-bookworm-slim, multi-stage
- `docker-compose.synology.yml` — /volume1/docker/ima2-gen/data 마운트
- `docker/entrypoint.sh` — 첫 실행 시 config.json 자동 생성
- `docker/README.synology.md` — 단계별 설치 가이드

## Quality

- Multi-stage로 ui/node_modules 제거, dev deps prune
- tini PID 1 (시그널 핸들링 정상)
- Idempotent entrypoint
- Non-root (node user)
- IMA2_GENERATION_REQUEST_LOG_FILE은 Feature 1 의존 (없으면 harmless)

## Cherry-pick Plan

그대로 cherry-pick. 충돌 없음.
Synology 한정이 아니라 범용 Docker 세팅으로도 활용 가능.
