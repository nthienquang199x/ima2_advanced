"""MCP server exposing Gemini Web (cookie-based) Nano Banana image generation
as a tool, for Claude Code / Claude Desktop / any MCP client.

Same underlying logic as server.py's HTTP /generate (see gemini_web_core.py)
— this is a second, independent way to reach it that needs no separate HTTP
process: an MCP client launches this script over stdio on demand.

Setup: copy .env.example to .env next to this file (or export the vars) with
SECURE_1PSID / SECURE_1PSIDTS from a logged-in gemini.google.com session, then
register it with an MCP client, e.g. (claude mcp add has no --env-file flag,
so pass the cookie values with -e):

    claude mcp add gemini-web-image -s user \\
        -e SECURE_1PSID="$(grep ^SECURE_1PSID= gemini-web-bridge/.env | cut -d= -f2-)" \\
        -e SECURE_1PSIDTS="$(grep ^SECURE_1PSIDTS= gemini-web-bridge/.env | cut -d= -f2-)" \\
        -- gemini-web-bridge/.venv/bin/python gemini-web-bridge/mcp_server.py

or as a Claude Desktop / Claude Code JSON entry:

    {
      "mcpServers": {
        "gemini-web-image": {
          "command": "/absolute/path/to/gemini-web-bridge/.venv/bin/python",
          "args": ["/absolute/path/to/gemini-web-bridge/mcp_server.py"],
          "env": { "SECURE_1PSID": "...", "SECURE_1PSIDTS": "..." }
        }
      }
    }
"""
from __future__ import annotations

import base64
import binascii
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.utilities.types import Image

import gemini_web_core as core

# Load a sibling .env for convenience when launched directly (an MCP client
# config's own "env" block, if set, still takes precedence via os.environ).
_ENV_FILE = Path(__file__).parent / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

mcp = MCPServer(
    "gemini-web-image",
    instructions=(
        "Generates images with Google Gemini's Nano Banana model through the "
        "Gemini Web app (gemini.google.com), authenticated with a browser "
        "cookie rather than an API key. Unofficial: this can break if Google "
        "changes gemini.google.com, and the cookie session can expire."
    ),
)


@mcp.tool()
async def generate_image(
    prompt: str,
    model: str = "nano-banana-2",
    reference_image_paths: list[str] | None = None,
) -> list[str | Image]:
    """Generate (or edit) an image with Gemini Web's Nano Banana.

    Parameters
    ----------
    prompt: What to generate, e.g. "a watercolor painting of a fox in a
        library". Phrase it so it clearly asks for an image — Gemini Web
        answers with text-only if the request reads as a question.
    model: "nano-banana-2" (default, works on a free Google account) or
        "nano-banana-pro" (needs the cookie's account to have Gemini
        Advanced; otherwise Gemini Web silently falls back to its default
        model for that account).
    reference_image_paths: Optional local file paths of images to edit or use
        as visual reference, read from disk and attached to the request.
    """
    references = []
    if reference_image_paths:
        for path in reference_image_paths:
            data = Path(path).read_bytes()
            references.append({"b64": base64.b64encode(data).decode("ascii")})

    try:
        result = await core.generate(prompt=prompt, model_id=model, references=references)
    except core.GeminiWebError as e:
        return [f"Gemini Web generation failed ({e.code}): {e}"]
    except (OSError, binascii.Error) as e:
        return [f"Could not read a reference image: {e}"]

    output: list[str | Image] = []
    if result.text:
        output.append(result.text)
    for img in result.images:
        output.append(Image(data=base64.b64decode(img.b64), format=img.mime.split("/")[-1]))
    return output


if __name__ == "__main__":
    mcp.run()
