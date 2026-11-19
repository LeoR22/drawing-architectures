"""Planner backed by GitHub Models (OpenAI-compatible chat completions, stdlib only).

Enabled by GITHUB_MODELS_TOKEN (or GITHUB_TOKEN): a GitHub token with the `models:read` permission.
Usage is governed by GitHub Models limits for your account, which are separate from Copilot's quota.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.request

from ..domain.errors import SpecError
from ..domain.models import Architecture, Requirements
from . import llm_common as common

API_URL = "https://models.github.ai/inference/chat/completions"
DEFAULT_MODEL = "openai/gpt-4.1"  # accepts text + images


def _token() -> str:
    return os.environ.get("GITHUB_MODELS_TOKEN") or os.environ.get("GITHUB_TOKEN", "")


class GithubModelsPlanner:
    name = "github"

    def __init__(self, token: str | None = None, model: str | None = None, opener=urllib.request.urlopen):
        self._token = token if token is not None else _token()
        self._model = model or os.environ.get("GITHUB_MODELS_MODEL", DEFAULT_MODEL)
        self._open = opener

    @staticmethod
    def available() -> bool:
        return bool(_token())

    def plan(self, req: Requirements) -> Architecture:
        if not self._token:
            raise SpecError("GITHUB_MODELS_TOKEN is not set; create a token with 'models: read' permission or use another mode.")
        content: list[dict] = []
        for _name, data in req.images[: common.MAX_IMAGES]:
            media = common.media_type(data)
            if media:
                url = f"data:{media};base64,{base64.b64encode(data).decode()}"
                content.append({"type": "image_url", "image_url": {"url": url}})
        content.append({"type": "text", "text": f"Use case:\n{req.text[:20000] or '(see images)'}"})
        body = json.dumps({
            "model": self._model, "max_tokens": 2000, "temperature": 0.2,
            "messages": [{"role": "system", "content": common.system_prompt()}, {"role": "user", "content": content}],
        }).encode()
        request = urllib.request.Request(API_URL, data=body, method="POST", headers={
            "Content-Type": "application/json", "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}", "X-GitHub-Api-Version": "2022-11-28",
        })
        payload = common.call_json(self._open, request, "GitHub Models")
        try:
            text = payload["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise SpecError("GitHub Models returned an unexpected response.") from None
        return common.parse_reply(text)
