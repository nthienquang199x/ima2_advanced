# Issue #95 Implementation Plan

## Phase 1: Devlog DONE → _fin 이동

DONE 확정 6개 plan 폴더를 `_fin/`으로 이동:
- `260602_grok-gemini-api-provider-research`
- `260602_switch_account`
- `260611_agent-mode-escape`
- `260611_generation-limit-unlock`
- `260621_repo-housekeeping`
- `_future/260611_swimwear-moderation-intent`

## Phase 2: Generation Request Log 구현

### NEW: `lib/generationRequestLog.ts`
ChatPoongKun 구현 기반. JSON-file 로그, max 200 entries, atomic write queue.

### NEW: `routes/generationRequestLog.ts`
GET /api/generation-requests 엔드포인트.

### MODIFY: `config.ts` (line ~238)
`storage` 블록에 `generationRequestLogFile` 추가:
```ts
generationRequestLogFile: pickStr(
  env.IMA2_GENERATION_REQUEST_LOG_FILE,
  fileCfg.storage?.generationRequestLogFile,
  join(configDir, "generation-request-log.json"),
),
```

### MODIFY: `routes/index.ts`
import + `registerGenerationRequestLogRoutes(app, ctx)` 추가.

### MODIFY: `routes/generate.ts` (finally block, line 527)
```ts
// in finally block, after finishJob:
appendGenerationRequestLog(ctx.config.storage.generationRequestLogFile, {
  id: randomBytes(8).toString("hex"),
  requestId,
  createdAt: Date.now(),
  prompt: typeof req.body?.prompt === "string" ? req.body.prompt : "",
  requested: parseInt(req.body?.n) || 1,
  succeeded: finishStatus === "completed" ? (finishMeta.imageCount as number ?? 1) : 0,
  error: finishStatus === "error" ? (finishErrorCode ?? "unknown") : null,
}).catch(() => {});
```

### NEW: `ui/src/lib/api-log.ts`
```ts
export type GenerationRequestLogEntry = { ... };
export async function getGenerationRequestLog(): Promise<{items: GenerationRequestLogEntry[]}> {
  return jsonFetch("/api/generation-requests");
}
```

### MODIFY: `ui/src/lib/api.ts`
barrel re-export 추가.

### NEW: `ui/src/components/GenerationRequestLogPanel.tsx`
ChatPoongKun 구현 기반. activeGenerations 감시 → 자동 refresh, 클릭 프롬프트 복사.

### NEW: `ui/src/lib/clipboard.ts`
navigator.clipboard + execCommand fallback.

### MODIFY: `ui/src/components/RightPanel.tsx`
4번째 탭 "log" 추가, GenerationRequestLogPanel lazy load.

### MODIFY: `ui/src/i18n/en.json` + `ko.json`
generationLog.* 키 추가.

### NEW: `tests/generation-request-log.test.ts`
ChatPoongKun 테스트 기반 + 추가 케이스.

### MODIFY: `ui/src/index.css`
`.generation-request-log` 스타일 추가.
