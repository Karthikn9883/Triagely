"""
LLM-powered checklist extractor.
At the moment this is a *stub* that simply returns a mock list so the
API starts; you can wire real LLM logic later.
"""
from .provider import call, LLMRequest
from app.integrations.gmail.service import load_thread_plain

SYSTEM_PROMPT = """
You are an email assistant. Extract a concise checklist of
action items from the email thread.  Return each task on its own line
starting with a dash (-).
"""

def extract_checklist(user_id: str, thread_id: str) -> dict:
    thread_text = load_thread_plain(user_id, thread_id)
    prompt      = SYSTEM_PROMPT + "\n\n### THREAD:\n" + thread_text
    raw         = call(LLMRequest(prompt=prompt))

    # for now just echo whatever the model (or mock) returns
    return {"thread_id": thread_id, "checklist": raw.splitlines()}
