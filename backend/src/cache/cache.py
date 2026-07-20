import threading
import time
import uuid
from typing import Any

from src.cache.session import Session


class SessionCache:
    def __init__(self, ttl: float = 86400):
        if ttl <= 0:
            raise ValueError("TTL must be greater than 0")
        self._ttl = ttl
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    def _is_expired(self, session: Session) -> bool:
        return bool(time.time() - session.last_activity > self._ttl)

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        now = time.time()
        session = Session(
            session_id=session_id,
            created_at=now,
            last_activity=now,
        )
        with self._lock:
            self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Session | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if self._is_expired(session):
                return None
            session.last_activity = time.time()
            return session

    def session_exists(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            if self._is_expired(session):
                return False
            return True

    def store_data(self, session_id: str, key: str, value: Any) -> bool:
        if not key:
            raise ValueError("Key must be a non-empty string")
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            if self._is_expired(session):
                return False
            session.data[key] = value
            session.last_activity = time.time()
            return True

    def get_data(self, session_id: str, key: str) -> tuple[Any, bool]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None, False
            if self._is_expired(session):
                return None, False
            session.last_activity = time.time()
            if key in session.data:
                return session.data[key], True
            return None, False

    def update_data(self, session_id: str, key: str, value: Any) -> bool:
        if not key:
            raise ValueError("Key must be a non-empty string")
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            if self._is_expired(session):
                return False
            session.data[key] = value
            session.last_activity = time.time()
            return True

    def delete_data(self, session_id: str, key: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            if self._is_expired(session):
                return False
            session.last_activity = time.time()
            if key in session.data:
                del session.data[key]
                return True
            return False

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def clear_all(self) -> None:
        with self._lock:
            self._sessions.clear()

    def clear_expired(self) -> int:
        count = 0
        with self._lock:
            expired_ids = [sid for sid, s in self._sessions.items() if self._is_expired(s)]
            for sid in expired_ids:
                del self._sessions[sid]
                count += 1
        return count
