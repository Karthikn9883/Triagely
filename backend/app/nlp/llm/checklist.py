# app/nlp/llm/checklist.py

"""
LLM-powered checklist extractor.
At present this function is a stub that simply returns a mock list so the
API starts; you can wire real LLM logic later by replacing the stubbed
call to `call` with a fully implemented completion-based extraction.
"""

# Import the generic LLM call function and its request schema
from .provider import call, LLMRequest

# Import the helper to read the plain-text of an email thread from DynamoDB
from app.integrations.gmail.utils import load_thread_plain

# System prompt guiding the LLM to extract action-items as a checklist
SYSTEM_PROMPT = """
You are an email assistant. Extract ONLY the 2 most important 
action items from the email thread. Return maximum 2 tasks, each on its own line
starting with a dash (-). Be concise (max 50 chars per task).
"""


def extract_checklist(user_id: str, thread_id: str) -> dict:
    """
    1) Loads the plain text of the specified email thread from storage.
    2) Constructs an LLM prompt asking for a checklist of action items.
    3) Calls the LLM provider with the prompt.
    4) Splits the raw model output into individual lines.

    Args:
        user_id   (str): The Cognito user sub (tenant partition key).
        thread_id (str): Unique identifier of the Gmail thread/message.

    Returns:
        dict: {
            "thread_id": <same thread_id>,
            "checklist": ["- Task 1", "- Task 2", ...]
        }

    Note:
    - `load_thread_plain` will return either the full plain-body or fallback to a snippet.
    - `call` wraps your chosen provider (OpenAI, Bedrock, or mock).
    - Currently this stub simply echoes whatever the model returns;
      you may want to parse JSON or more structured output in a real implementation.
    """
    # 1️⃣ Retrieve the email content from DynamoDB
    thread_text = load_thread_plain(user_id, thread_id)

    # 2️⃣ Build the full prompt combining system and user context
    prompt = SYSTEM_PROMPT + "\n\n### THREAD:\n" + thread_text

    # 3️⃣ Invoke the LLM to perform the extraction
    #    - LLMRequest holds prompt, max_tokens, temperature
    raw = call(LLMRequest(prompt=prompt))

    # 4️⃣ Convert the raw string output into a list of lines (checklist items)
    #    Splitting on newline preserves any dash prefixes.
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    
    # 5️⃣ Enforce maximum 2 tasks to minimize token usage
    limited_lines = lines[:2]

    # Return a consistent schema for the API
    return {"thread_id": thread_id, "checklist": limited_lines}
