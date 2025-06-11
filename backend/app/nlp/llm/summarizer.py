from .provider import call, LLMRequest
from app.integrations.gmail.service import load_thread_plain

SYSTEM_PROMPT = """
You are an email assistant. Summarise the thread in 5 bullet points
(max 80 chars each) and list any explicit questions separately.
"""

def summarise_thread(user_id: str, thread_id: str) -> dict:
    thread_text = load_thread_plain(user_id, thread_id)
    prompt      = SYSTEM_PROMPT + "\n\n### THREAD:\n" + thread_text
    summary_txt = call(LLMRequest(prompt=prompt))
    return {"thread_id": thread_id, "summary": summary_txt}
