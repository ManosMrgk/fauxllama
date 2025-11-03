from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Iterable, Iterator, List, Optional, Any, Protocol, TypedDict

ChatMessage = Dict[str, Any]
ModelParams = Dict[str, Any]

class StreamEvent(TypedDict, total=False):
    ''' Normalized streaming event your API can pipe through as SSE "data: ..." '''
    id: Optional[str]
    model: Optional[str]
    choices: List[Dict[str, Any]] 
    usage: Optional[Dict[str, int]]
    error: Optional[str]
    raw: Optional[str]

class LLMClient(ABC):
    """Provider-agnostic streaming chat client."""
    name: str

    @abstractmethod
    def stream_chat(
        self,
        messages: List[ChatMessage],
        params: Optional[ModelParams] = None,
        request_id: Optional[str] = None,
    ) -> Iterator[StreamEvent]:
        """Yield normalized StreamEvent objects until complete."""
        raise NotImplementedError

    def validate(self) -> None:
        """Validate credentials/connectivity. Raise RuntimeError if invalid."""
        return