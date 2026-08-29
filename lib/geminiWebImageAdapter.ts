// lib/geminiWebImageAdapter.ts — the gemini-web lane's runtime.
//
// Thin HTTP client for the local gemini-web-bridge (gemini-web-bridge/server.py),
// which wraps HanaokaYuzu/Gemini-API's cookie-authenticated Gemini Web client.
// ima2 holds no Google credential for this lane: it only calls a URL the user
// runs themselves (IMA2_GEMINI_WEB_URL / ctx.config.geminiWeb.defaultUrl), the
// same "local-http" shape lib/comfyImageAdapter.ts uses for comfy. Unlike
// lib/geminiApiImageAdapter.ts, there is no REST payload to build: the bridge
// does its own prompt/model handling, so this adapter only shapes the
// request/response envelope described in gemini-web-bridge/server.py's contract.
import { logEvent } from "./logger.js";
import type { RuntimeContext } from "./runtimeContext.js";
import { detectImageMimeFromB64 } from "./refs.js";
import { deriveReferenceLimit } from "./providers/derive.js";

export interface GeminiWebGenerateResult {
  b64: string;
  revisedPrompt?: string;
  usage: Record<string, number> | null;
  webSearchCalls: number;
  mime?: string;
}

interface GeminiWebRefDetail {
  b64: string;
  declaredMime?: string | null;
  detectedMime?: string | null;
}

// Slower/flakier than the official API's 120s ceiling (lib/geminiApiImageAdapter.ts),
// but far under comfy's 30min local-GPU ceiling (lib/comfyImageAdapter.ts).
const GEMINI_WEB_TIMEOUT_MS = 180_000;

function geminiWebError(message: string, status: number, code: string): Error {
  const err: any = new Error(message);
  err.status = status;
  err.code = code;
  return err;
}

function buildReferences(references: GeminiWebRefDetail[]): Array<{ b64: string; mime: string }> {
  return references
    .slice(0, deriveReferenceLimit("gemini-web", "edit"))
    .map((ref) => ({
      b64: ref.b64,
      mime: ref.declaredMime || ref.detectedMime || detectImageMimeFromB64(ref.b64) || "image/png",
    }));
}

export async function generateViaGeminiWeb(
  prompt: string,
  ctx: RuntimeContext,
  options: {
    model?: string;
    signal?: AbortSignal;
    requestId?: string;
    references?: GeminiWebRefDetail[];
  } = {},
): Promise<GeminiWebGenerateResult> {
  const model = options.model || "nano-banana-2";
  const references = buildReferences(options.references || []);
  const baseUrl = ctx.config.geminiWeb.defaultUrl;
  const url = `${baseUrl.replace(/\/$/, "")}/generate`;

  logEvent("gemini-web", "generate:start", {
    requestId: options.requestId,
    model,
    promptChars: prompt.length,
    refs: references.length,
  });

  const timeoutSignal = AbortSignal.timeout(GEMINI_WEB_TIMEOUT_MS);
  const combinedSignal = options.signal
    ? AbortSignal.any([options.signal, timeoutSignal])
    : timeoutSignal;

  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, model, references }),
      signal: combinedSignal,
    });
  } catch (e: any) {
    if (e.name === "AbortError") {
      if (options.signal?.aborted) {
        throw geminiWebError("Generation canceled", 499, "GENERATION_CANCELED");
      }
      throw geminiWebError("Gemini Web bridge request timed out", 504, "GEMINI_WEB_TIMEOUT");
    }
    // The fetch itself threw (connection refused, DNS failure, etc.): the
    // bridge process is not running at all, distinct from an HTTP error status.
    throw geminiWebError(
      `Could not reach the gemini-web bridge at ${baseUrl}. Start it (see gemini-web-bridge/README.md) `
      + `and check IMA2_GEMINI_WEB_URL: ${e.message}`,
      502,
      "GEMINI_WEB_OFFLINE",
    );
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null) as { error?: { code?: string; message?: string } } | null;
    const code = body?.error?.code || "GEMINI_WEB_UPSTREAM_ERROR";
    const message = body?.error?.message || `gemini-web bridge returned HTTP ${res.status}`;
    throw geminiWebError(message, res.status, code);
  }

  const json = await res.json() as { images?: Array<{ b64: string; mime: string }>; text?: string };
  const image = json.images?.[0];
  if (!image) {
    throw geminiWebError("gemini-web bridge returned no image", 502, "GEMINI_WEB_NO_IMAGE");
  }

  logEvent("gemini-web", "generate:done", {
    requestId: options.requestId,
    model,
    b64Len: image.b64.length,
    mime: image.mime,
    textResponseLen: json.text?.length || 0,
  });

  return {
    b64: image.b64,
    revisedPrompt: json.text || prompt,
    usage: null,
    webSearchCalls: 0,
    mime: image.mime,
  };
}
