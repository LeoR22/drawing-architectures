"""Planner backed by the Anthropic Messages API (stdlib only). Enabled by ANTHROPIC_API_KEY.

The model only chooses services and flows from the catalog; layout and drawing stay deterministic.
Any API/parse failure raises SpecError so the caller can fall back to the offline planner.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.request

from ..domain.errors import SpecError
from ..domain.models import Architecture, Requirements
from . import llm_common as common

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5-5"


class AnthropicPlanner:
    name = "anthropic"

    def __init__(self, api_key: str | None = None, model: str | None = None, opener=urllib.request.urlopen):
        self._key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = model or os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
        self._open = opener

    @staticmethod
    def available() -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def plan(self, req: Requirements) -> Architecture:
        if not self._key:
            raise SpecError("ANTHROPIC_API_KEY is not set; use another mode or set the variable.")
        content: list[dict] = []
        for _name, data in req.images[: common.MAX_IMAGES]:
            media = common.media_type(data)
            if media:
                content.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": base64.b64encode(data).decode()}})
        content.append({"type": "text", "text": f"Use case:\n{req.text[:20000] or '(see images)'}"})
        body = json.dumps({
            "model": self._model, "max_tokens": 2000, "system": common.system_prompt(),
            "messages": [{"role": "user", "content": content}],
        }).encode()
        request = urllib.request.Request(API_URL, data=body, method="POST", headers={
            "content-type": "application/json", "x-api-key": self._key, "anthropic-version": "2023-06-01",
        })
        payload = common.call_json(self._open, request, "the Anthropic API")
        text = "".join(b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text")
        return common.parse_reply(text)
