# filepath: app/services/llm/openai.py
from __future__ import annotations
import os
import json
from typing import Iterator, List, Optional, Dict, Any

import requests
from requests.adapters import HTTPAdapter, Retry

from .base import LLMClient, StreamEvent, ChatMessage, ModelParams


class OpenAIClient(LLMClient):
    """
    Streams chat completions from OpenAI's /v1/chat/completions endpoint
    and yields normalized StreamEvent dicts with OpenAI-style deltas.

    Required env:
      - OPENAI_API_KEY

    Optional env:
      - OPENAI_BASE           (default: https://api.openai.com/v1)
      - OPENAI_MODEL          (fallback model if none is provided at call time)
      - OPENAI_ORG            (sets OpenAI-Organization header)
      - OPENAI_PROJECT        (sets OpenAI-Project header, if your tenant uses it)
    """
    name = "openai"

    def __init__(self) -> None:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAIClient")

        self.base = (os.environ.get("OPENAI_BASE") or "https://api.openai.com/v1").rstrip("/")
        self.key = key
        self.default_model = os.environ.get("OPENAI_MODEL")  # e.g., "gpt-4o-mini"
        self.org = os.environ.get("OPENAI_ORG")
        self.project = os.environ.get("OPENAI_PROJECT")

        self._session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["POST"]),
        )
        self._session.mount("https://", HTTPAdapter(max_retries=retries))
        self._session.mount("http://", HTTPAdapter(max_retries=retries))

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        if self.org:
            headers["OpenAI-Organization"] = self.org
        if self.project:
            headers["OpenAI-Project"] = self.project
        return headers

    def validate(self) -> None:
        url = f"{self.base}/models"
        try:
            resp = self._session.get(url, headers=self._headers(), timeout=(5, 15))
        except requests.RequestException as e:
            raise RuntimeError(f"OpenAI connectivity error: {e}") from e

        if resp.status_code == 200:
            return
        if resp.status_code in (401, 403):
            key = os.environ.get("OPENAI_API_KEY")
            raise RuntimeError(f"Invalid OpenAI API key {key} or access denied (HTTP {resp.status_code}).")
        if resp.status_code == 429:
            return
        raise RuntimeError(f"OpenAI validation failed (HTTP {resp.status_code}): {resp.text[:500]}")

    def _filter_params(self, params: Optional[ModelParams]) -> Dict[str, Any]:
        """
        Only pass through parameters that OpenAI's chat/completions understands.
        (Keeps unknown keys like vendor-specific options from causing 400s.)
        """
        if not params:
            return {}

        allowed = {
            "temperature",
            "top_p",
            "n",
            "presence_penalty",
            "frequency_penalty",
            "max_tokens",
            "stop",
            "logit_bias",
            "seed",
            "tools",
            "tool_choice",
            "response_format",
            "stream_options",
            "modalities",
            "audio",
            "vision",
        }
        return {k: v for k, v in params.items() if k in allowed and v is not None}

    def stream_chat(
        self,
        messages: List[ChatMessage],
        params: Optional[ModelParams] = None,
        request_id: Optional[str] = None,
    ) -> Iterator[StreamEvent]:
        """
        Yields dict events shaped like:
          {
            "id": "...",
            "model": "...",
            "choices": [{"delta": {"content": "..."}, ...}],
            "raw": "<provider JSON chunk>"
          }

        Terminates cleanly when the provider sends [DONE].
        """
        resolved_model = self.default_model
        if not resolved_model:
            resolved_model = "gpt-4o-mini"

        url = f"{self.base}/chat/completions"

        payload: Dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "stream": True,
        }
        payload.update(self._filter_params(params))

        timeout = (5, 300)

        with self._session.post(
            url,
            headers=self._headers(),
            json=payload,
            stream=True,
            timeout=timeout,
        ) as resp:
            resp.raise_for_status()

            for raw in resp.iter_lines():
                if not raw:
                    continue
                line = raw.decode("utf-8")

                if not line.startswith("data: "):
                    yield {"raw": line}
                    continue

                data_json = line[len("data: "):].strip()

                if data_json == "[DONE]":
                    break

                try:
                    parsed = json.loads(data_json)
                    yield {
                        "id": parsed.get("id"),
                        "model": parsed.get("model"),
                        "choices": parsed.get("choices", []),
                        "raw": data_json,
                    }
                except Exception as e:
                    yield {"error": f"Bad chunk: {e}", "raw": data_json}
