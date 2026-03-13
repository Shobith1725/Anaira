"""
In-memory session store.
Plain Python dict.
Lives for the duration of the server process.
"""

from typing import Optional

_sessions: dict = {}


def store_session(session_id: str, data: dict) -> None:
    _sessions[session_id] = data


def get_session(session_id: str) -> Optional[dict]:
    return _sessions.get(session_id)


def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


def update_session(session_id: str, updates: dict) -> Optional[dict]:
    """Merge updates into existing session."""
    session = _sessions.get(session_id)
    if session is None:
        return None
    session.update(updates)
    _sessions[session_id] = session
    return session


def get_all_sessions() -> dict:
    """For dashboard/debugging only."""
    return {sid: {"driver_name": s.get("driver_name"), "mode": s.get("mode")}
            for sid, s in _sessions.items()}