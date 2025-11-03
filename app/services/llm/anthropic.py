from .base import LLMClient, StreamEvent, ChatMessage, ModelParams
from typing import Iterator, List, Optional

class AnthropicClient(LLMClient):
    name = "anthropic"
    def stream_chat(self, messages: List[ChatMessage],
                    params: Optional[ModelParams] = None, request_id: Optional[str] = None) -> Iterator[StreamEvent]:
        raise NotImplementedError
