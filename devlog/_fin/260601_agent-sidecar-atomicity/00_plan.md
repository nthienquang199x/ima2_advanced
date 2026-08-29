---
created: 2026-06-01
tags: [bug, agent, video, atomicity, sidecar]
status: plan
---

# Plan: Agent Artifact Sidecar Atomicity

## Part 1 — 요약

Agent 이미지/비디오 저장 시 .json sidecar 쓰기 실패를 `.catch(() => {})`로 삼키고 있어,
메타데이터 없는 고아 파일이 남을 수 있음. `/api/video/generate`에서 사용하는 rollback 패턴을
agentRuntime에도 적용하여 all-or-nothing 보장.

## Part 2 — Diff

### MODIFY: `lib/agentRuntime.ts`

#### A. import에 unlink 추가 (line 2)

**Before:**
```typescript
import { mkdir, readFile, writeFile } from "node:fs/promises";
```

**After:**
```typescript
import { mkdir, readFile, unlink, writeFile } from "node:fs/promises";
```

#### B. persistAgentImage — sidecar rollback (line 395-396)

**Before:**
```typescript
  await writeFile(join(ctx.config.storage.generatedDir, filename), embedded.buffer);
  await writeFile(join(ctx.config.storage.generatedDir, `${filename}.json`), JSON.stringify(meta)).catch(() => {});
```

**After:**
```typescript
  const filePath = join(ctx.config.storage.generatedDir, filename);
  await writeFile(filePath, embedded.buffer);
  try {
    await writeFile(`${filePath}.json`, JSON.stringify(meta));
  } catch (err) {
    await unlink(filePath).catch(() => {});
    throw err;
  }
```

#### C. persistAgentVideo — sidecar rollback (line 506-507)

**Before:**
```typescript
  await writeFile(join(ctx.config.storage.generatedDir, filename), result.videoBuffer);
  await writeFile(join(ctx.config.storage.generatedDir, `${filename}.json`), JSON.stringify(meta)).catch(() => {});
```

**After:**
```typescript
  const filePath = join(ctx.config.storage.generatedDir, filename);
  await writeFile(filePath, result.videoBuffer);
  try {
    await writeFile(`${filePath}.json`, JSON.stringify(meta));
  } catch (err) {
    await unlink(filePath).catch(() => {});
    throw err;
  }
```

## 관련 파일

| 파일 | 변경 |
|------|------|
| `lib/agentRuntime.ts` | MODIFY — 2곳 sidecar write에 rollback 패턴 적용 |
