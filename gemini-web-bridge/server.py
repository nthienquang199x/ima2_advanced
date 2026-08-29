"""Local HTTP bridge exposing Gemini Web (cookie-based) image generation.

ima2-gen's "gemini-web" provider is a `local-http` credential lane (see
lib/providers/registry.ts): ima2 does not hold or supervise any Google
credential for it, it only calls a URL the user runs themselves
(IMA2_GEMINI_WEB_URL). This process is that URL's server. See
gemini_web_core.py for the actual Gemini Web calling logic — this file is
just the HTTP shape.

Contract (mirrors lib/geminiApiImageAdapter.ts's shape so the TS adapter can
stay a thin HTTP client):

  GET /health
    -> 200 {"ok": true, "cookiesLoaded": bool}

  POST /generate
    body: {"prompt": str, "model": "nano-banana-2"|"nano-banana-pro",
           "references": [{"b64": str, "mime": str}, ...]}
    -> 200 {"images": [{"b64": str, "mime": str}], "text": str}
    -> 4xx/5xx {"error": {"code": str, "message": str}}
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import gemini_web_core as core

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("gemini-web-bridge")

app = FastAPI(title="gemini-web-bridge")


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.get("/health")
async def health():
    return {"ok": True, "cookiesLoaded": core.cookies_configured()}


@app.post("/generate")
async def generate(request: Request):
    try:
        body = await request.json()
    except Exception:
        return error_response(400, "GEMINI_WEB_BAD_REQUEST", "invalid JSON body")

    try:
        result = await core.generate(
            prompt=body.get("prompt"),
            model_id=body.get("model") or "nano-banana-2",
            references=body.get("references") or [],
        )
    except core.GeminiWebError as e:
        return error_response(e.status, e.code, str(e))
    except Exception as e:
        log.exception("unexpected error in /generate")
        return error_response(502, "GEMINI_WEB_UPSTREAM_ERROR", str(e))

    return {
        "images": [{"b64": img.b64, "mime": img.mime} for img in result.images],
        "text": result.text,
    }


@app.on_event("shutdown")
async def shutdown():
    await core.close_client()
