from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    session_id: str
    data: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    last_activity: float = 0.0
