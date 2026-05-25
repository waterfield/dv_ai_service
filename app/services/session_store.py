import threading
from datetime import datetime, timedelta

_sessions: dict[str, dict] = {}
_lock = threading.Lock()
_TTL_MINUTES = 60


def get_history(session_id: str) -> list[dict]:
    with _lock:
        entry = _sessions.get(session_id)
        if not entry:
            return []
        if datetime.now() - entry["updated"] > timedelta(minutes=_TTL_MINUTES):
            del _sessions[session_id]
            return []
        return list(entry["messages"])


def append_messages(session_id: str, messages: list[dict]) -> None:
    with _lock:
        if session_id not in _sessions:
            _sessions[session_id] = {"messages": [], "updated": datetime.now()}
        _sessions[session_id]["messages"].extend(messages)
        _sessions[session_id]["updated"] = datetime.now()
        # cap at 20 messages to avoid token overflow
        _sessions[session_id]["messages"] = _sessions[session_id]["messages"][-20:]


def clear_session(session_id: str) -> None:
    with _lock:
        _sessions.pop(session_id, None)
