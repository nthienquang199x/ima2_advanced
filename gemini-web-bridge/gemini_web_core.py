"""Shared Gemini Web (cookie-based) image generation core.

Wraps HanaokaYuzu/Gemini-API (`gemini_webapi`) — the reverse-engineered
client for gemini.google.com that actually parses generated (Nano Banana)
images out of the StreamGenerate response. Both `server.py` (the HTTP bridge
ima2-gen's `gemini-web` provider calls) and `mcp_server.py` (an MCP tool for
any MCP client, e.g. Claude Code) are thin wrappers around this module so the
Gemini Web calling logic exists in exactly one place.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import contextlib
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from gemini_webapi import GeminiClient

log = logging.getLogger("gemini-web-core")

_client: GeminiClient | None = None
_client_lock = asyncio.Lock()

# ima2's model ids -> gemini_webapi model name strings. Gemini Web has no
# separate "image model"; Nano Banana image generation is a capability of the
# chat model itself, triggered by the prompt asking for an image.
# gemini_webapi's `Model` enum is deprecated (model identity is now discovered
# per-account at init, since ids/tiers drift without a library release) — its
# own docstring says to pass a plain name/alias/id string instead, which is
# what these are. "gemini-pro" asks for the "pro" tier, which only exists on
# accounts with a Gemini Advanced subscription; on a free account the library
# falls back to the account's real default, same tradeoff gemini-web2api
# documents for its chat-only lane.
MODEL_MAP = {
    "nano-banana-2": "gemini-flash",
    "nano-banana-pro": "gemini-pro",
}

MIME_TO_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


class GeminiWebError(Exception):
    """Carries an HTTP-style status + machine-readable code for callers to map."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code


@dataclass
class GeneratedImage:
    b64: str
    mime: str


@dataclass
class GenerateResult:
    images: list[GeneratedImage]
    text: str


def cookies_configured() -> bool:
    return bool(os.environ.get("SECURE_1PSID"))


async def get_client() -> GeminiClient:
    global _client
    async with _client_lock:
        if _client is not None:
            return _client
        psid = os.environ.get("SECURE_1PSID")
        psidts = os.environ.get("SECURE_1PSIDTS")
        if not psid:
            raise GeminiWebError(401, "GEMINI_WEB_COOKIE_MISSING", "SECURE_1PSID not set")
        client = GeminiClient(psid, psidts, proxy=os.environ.get("HTTPS_PROXY") or None)
        # auto_refresh keeps the session alive for a long-running process
        # instead of dying whenever __Secure-1PSIDTS rotates.
        try:
            await client.init(timeout=45, auto_close=False, auto_refresh=True)
        except Exception as e:
            raise GeminiWebError(502, "GEMINI_WEB_AUTH_FAILED", f"cookie auth failed: {e}") from e
        _client = client
        return client


async def close_client() -> None:
    global _client
    if _client is not None:
        with contextlib.suppress(Exception):
            await _client.close()
        _client = None


def _decode_reference_bytes(ref: dict, index: int) -> bytes:
    b64 = ref.get("b64")
    if not isinstance(b64, str) or not b64:
        raise GeminiWebError(400, "GEMINI_WEB_BAD_REQUEST", f"reference[{index}] missing b64")
    try:
        return base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError) as e:
        raise GeminiWebError(400, "GEMINI_WEB_BAD_REQUEST", f"reference[{index}] is not valid base64") from e


async def generate(
    prompt: str,
    model_id: str = "nano-banana-2",
    references: list[dict] | None = None,
) -> GenerateResult:
    """Generate image(s) from Gemini Web. Raises GeminiWebError on any failure."""
    if not prompt or not prompt.strip():
        raise GeminiWebError(400, "GEMINI_WEB_BAD_REQUEST", "prompt is required")

    model = MODEL_MAP.get(model_id)
    if model is None:
        raise GeminiWebError(400, "GEMINI_WEB_UNKNOWN_MODEL", f"unknown model: {model_id}")

    files = [_decode_reference_bytes(ref, i) for i, ref in enumerate(references or [])]

    client = await get_client()

    try:
        response = await client.generate_content(prompt, files=files or None, model=model)
    except asyncio.TimeoutError as e:
        raise GeminiWebError(504, "GEMINI_WEB_TIMEOUT", "Gemini Web request timed out") from e
    except Exception as e:
        message = str(e)
        if "429" in message or "rate" in message.lower():
            raise GeminiWebError(429, "GEMINI_WEB_RATE_LIMITED", message) from e
        if "UNAUTHENTICATED" in message or "BardErrorInfo" in message or "1052" in message:
            raise GeminiWebError(401, "GEMINI_WEB_COOKIE_EXPIRED", message) from e
        raise GeminiWebError(502, "GEMINI_WEB_UPSTREAM_ERROR", message) from e

    if not response.images:
        raise GeminiWebError(
            502, "GEMINI_WEB_NO_IMAGE",
            "Gemini Web returned no generated image (it may have answered with text only, "
            "or safety-filtered the prompt)",
        )

    images_out: list[GeneratedImage] = []
    with tempfile.TemporaryDirectory(prefix="gemini-web-core-") as tmpdir:
        for i, image in enumerate(response.images):
            try:
                # save() ignores a filename with no suffix and picks its own
                # (timestamp + url hash) — always use the path it returns
                # rather than guessing the name back with a glob.
                filename = f"out_{uuid.uuid4().hex}.png"
                saved_path = Path(await image.save(path=tmpdir, filename=filename, verbose=False))
                data = saved_path.read_bytes()
                ext = saved_path.suffix.lower()
                mime = next((m for m, e in MIME_TO_EXT.items() if e == ext), "image/png")
                images_out.append(GeneratedImage(b64=base64.b64encode(data).decode("ascii"), mime=mime))
            except Exception:
                log.exception("failed to save generated image %d", i)
                continue

    if not images_out:
        raise GeminiWebError(502, "GEMINI_WEB_NO_IMAGE", "Gemini Web reported images but none could be downloaded")

    return GenerateResult(images=images_out, text=response.text or "")
