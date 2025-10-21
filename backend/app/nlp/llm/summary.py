# app/nlp/llm/summary.py

"""
LLM-powered summariser for email threads.
Chooses bullet count dynamically based on thread length, then formats a prompt
to extract concise summary points via an LLM.
"""

# Import the generic LLM call interface and its request schema
from .provider import call, LLMRequest

# Import helper to retrieve the plain-text content of the email from storage
from app.integrations.gmail.utils import load_thread_plain


def summarise_thread(user_id: str, thread_id: str) -> dict:
    """
    1) Load the plain-text body of the email thread from DynamoDB.
    2) Determine an appropriate number of summary bullets based on length:
       - <200 chars → 1 bullet
       - <600 chars → 3 bullets
       - otherwise  → 5 bullets
    3) Build the LLM prompt to summarise accordingly and list any questions.
    4) Call the LLM and split its response into non-empty lines.

    Args:
        user_id (str): Cognito user sub (partition key in DynamoDB).
        thread_id (str): Unique ID for the Gmail thread/message.

    Returns:
        dict: {
            "thread_id": <same thread_id>,
            "summary": ["Point 1", "Point 2", ...]
        }
    """
    # 1️⃣ Retrieve the full plain-text or snippet fallback
    thread_text = load_thread_plain(user_id, thread_id)

    # 2️⃣ Keep summaries very short - maximum 2 bullet points
    length = len(thread_text or "")
    if length < 300:
        num = 1
    else:
        num = 2

    # 3️⃣ Compose a system/user prompt for ultra-concise summaries
    prompt = (
        f"You are an email assistant. Summarise the thread in {num} "
        f"ultra-concise bullet point{'s' if num > 1 else ''} (max 60 chars each). "
        "Focus only on the main point and key actions needed.\n\n"
        "### THREAD:\n" + thread_text
    )

    # 4️⃣ Invoke the LLM and process its raw output
    raw = call(LLMRequest(prompt=prompt))
    # Split into individual lines, trimming whitespace and discarding empties
    lines = [line.strip() for line in raw.splitlines() if line.strip()]

    # Return a structured response
    return {"thread_id": thread_id, "summary": lines}
