from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass(frozen=True)
class TestBlock:
    trace_id: str
    input: Any
    pre_state: Dict[str, Any]
    action: str
    expected_state: Dict[str, Any]
    actual_state: Dict[str, Any]
    diff: Dict[str, Any]
    result: Optional[str] = None

@dataclass(frozen=True)
class Message:
    from_agent: str
    to_agent: str
    trace_id: str
    payload: Dict[str, Any]
    state_ref: Optional[str] = None
