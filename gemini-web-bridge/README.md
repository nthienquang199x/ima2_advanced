# gemini-web-bridge

Local HTTP server that lets ima2-gen's `gemini-web` provider generate images
through the *Gemini Web app* (gemini.google.com, cookie auth) instead of the
official Gemini API. Wraps
[HanaokaYuzu/Gemini-API](https://github.com/HanaokaYuzu/Gemini-API)
(`gemini_webapi`), which is the actual reference implementation that parses
generated (Nano Banana) images out of the StreamGenerate response —
`gemini-web2api` does not do this, it only handles image *input*.

This is unofficial and against Google's ToS for gemini.google.com. Use a
throwaway/secondary account, not one you can't afford to lose. Cookies expire
and Google can change the wire protocol at any time without notice.

## Setup

```bash
cd gemini-web-bridge
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Get your cookies:
1. Open gemini.google.com in a browser, logged in.
2. DevTools -> Application (Chrome) / Storage (Firefox) -> Cookies -> `https://gemini.google.com`.
3. Copy `__Secure-1PSID` and `__Secure-1PSIDTS` into `.env`.
4. `nano-banana-pro` (Gemini Pro image) requires the cookie account to have
   Gemini Advanced; otherwise the bridge will error on that model — use
   `nano-banana-2` instead.

Run it:

```bash
set -a; source .env; set +a
uvicorn server:app --host 127.0.0.1 --port "${PORT:-8787}"
```

Point ima2-gen at it:

```bash
export IMA2_GEMINI_WEB_URL=http://127.0.0.1:8787
```

Then select provider `gemini-web` (models `nano-banana-2` / `nano-banana-pro`)
in ima2-gen same as you would `gemini-api`.

## Notes

- `__Secure-1PSIDTS` rotates periodically; the bridge process keeps a live
  `GeminiClient` with `auto_refresh=True` so it re-signs itself in the
  background. If it eventually dies with `GEMINI_WEB_COOKIE_EXPIRED`, just
  grab fresh cookie values and restart the bridge.
- This process holds the Google cookie, not ima2-gen — matching the same
  "user-run local server" trust boundary ima2-gen already uses for its Comfy
  provider (`IMA2_COMFY_URL`).
