import json
from typing import Iterable, Iterator, Dict, Any

def stream_events_as_sse(events: Iterable[Dict[str, Any]]) -> Iterator[str]:
    for ev in events:
        yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"