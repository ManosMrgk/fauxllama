from .base import LLMClient, StreamEvent, ChatMessage, ModelParams
from typing import Iterator, List, Optional

class GeminiClient(LLMClient):
    name = "gemini"
    def stream_chat(self, messages: List[ChatMessage], model: Optional[str] = None,
                    params: Optional[ModelParams] = None, request_id: Optional[str] = None) -> Iterator[StreamEvent]:
        raise NotImplementedError
