"""Server-Sent Events (SSE) formatting utilities."""
import json
from typing import Any, Dict


def format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """Format payload into standard Server-Sent Event text format.
    
    Example:
        event: content_delta
        data: {"delta": "Hello"}
    """
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {json_data}\n\n"
