from app.core.db import get_message

def load_thread_plain(user_id: str, message_id: str) -> str:
    """
    Return the cached plain-text body for a message/thread.
    Falls back to snippet if plain is empty. Returns '' if not found.
    """
    msg = get_message(user_id, message_id)
    if not msg:
        return ""
    return msg.get("plain") or msg.get("snippet", "")
