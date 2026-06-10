from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TestBlock:
    trace_id: str
    input: Any
    pre_state: dict[str, Any]
    action: str
    expected_state: dict[str, Any]
    actual_state: dict[str, Any]
    diff: dict[str, Any]
    result: str | None = None


@dataclass(frozen=True)
class Message:
    from_agent: str
    to_agent: str
    trace_id: str
    payload: dict[str, Any]
    state_ref: str | None = None
