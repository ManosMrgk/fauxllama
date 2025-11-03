from __future__ import annotations
import os, json
import requests
from typing import Iterator, List, Optional, Dict, Any
from requests.adapters import HTTPAdapter, Retry
from .base import LLMClient, StreamEvent, ChatMessage, ModelParams

class AzureOpenAIClient(LLMClient):
    name = "azure"

    def __init__(self) -> None:
        self.endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
        self.deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]
        self.key = os.environ["AZURE_OPENAI_KEY"]
        self.version = os.environ.get("AZURE_OPENAI_VERSION", "2024-12-01-preview")

        self._session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["POST"]),
        )
        self._session.mount("https://", HTTPAdapter(max_retries=retries))

    def stream_chat(
        self,
        messages: List[ChatMessage],
        params: Optional[ModelParams] = None,
        request_id: Optional[str] = None,
    ) -> Iterator[StreamEvent]:
        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions"
        query = {"api-version": self.version}
        headers = {
            "api-key": self.key,
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "messages": messages,
            "stream": True,
        }

        defaults: Dict[str, Any] = {"temperature": 0.1, "top_p": 1, "n": 1}
        payload.update({**defaults, **(params or {})})

        with self._session.post(url, headers=headers, params=query, json=payload, stream=True, timeout=(5, 300)) as resp:
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
                    yield {"choices": [], "raw": data_json}
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
