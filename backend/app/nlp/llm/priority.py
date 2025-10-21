# backend/app/nlp/llm/priority.py

"""
LLM-powered priority classifier.
Determines whether a given email thread requires immediate attention.
"""

# Import LLM call interface
from .provider import call, LLMRequest

# Import helper to fetch the plain text content of an email thread
from app.integrations.gmail.utils import load_thread_plain

# System-level instruction guiding the LLM to output exactly "High" or "Normal"
SYSTEM_PROMPT = """
You are an email assistant.  Determine whether this email thread 
requires immediate or urgent attention.  If yes, reply ONLY with "High"; 
otherwise reply "Normal".
"""


def classify_priority(user_id: str, thread_id: str) -> dict:
    """
    1) Load the plain-text body of the thread from the database.
    2) Build an LLM prompt combining the system instruction and the thread text.
    3) Call the LLM provider to get a raw string response.
    4) Normalize the response to exactly "High" or "Normal".

    Args:
        user_id   (str): Unique user identifier (Cognito sub).
        thread_id (str): Unique message/thread ID in DynamoDB.

    Returns:
        dict: {
          "thread_id": <same thread_id>,
          "priority": "High" | "Normal"
        }
    """
    # 1️⃣ Retrieve the thread text
    text = load_thread_plain(user_id, thread_id)

    # 2️⃣ Compose the LLM prompt: system + user thread
    prompt = SYSTEM_PROMPT + "\n\n### THREAD:\n" + text

    # 3️⃣ Invoke the LLM to classify priority
    raw = call(LLMRequest(prompt=prompt))

    # 4️⃣ Simple heuristics: if the response starts with "high" (case-insensitive), choose "High"
    #    otherwise default to "Normal". This covers minor spelling or whitespace variations.
    choice = raw.strip().lower().startswith("high") and "High" or "Normal"

    # Return a structured payload for the API
    return {"thread_id": thread_id, "priority": choice}
