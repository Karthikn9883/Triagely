# app/nlp/router.py

# FastAPI imports for routing and dependency injection
from fastapi import APIRouter, Depends, HTTPException

# Import auth helper to identify the currently logged-in user
from app.core.auth import current_user

# Import DynamoDB wrapper from app.core.db (ddb is a Boto3 resource)
from app.core.db import ddb

# Import our LLM-powered utility functions for summaries, checklists, and priority
from .llm.summary   import summarise_thread
from .llm.checklist import extract_checklist
from .llm.priority  import classify_priority

# Instantiate a new APIRouter for all /nlp endpoints
# Prefix all routes with "/nlp" and tag for automatic docs grouping
router = APIRouter(prefix="/nlp", tags=["nlp"])


@router.post("/summaries/{thread_id}")
def create_summary(thread_id: str, user=Depends(current_user)):
    """
    1) Look up an existing summary/checklist/priority in DynamoDB.
    2) If found, return the cached version immediately.
    3) Otherwise, generate each via LLM once, persist back to DynamoDB,
       and then return the newly created values.

    Parameters:
    - thread_id: Unique message/thread ID (comes from path)
    - user: Injected by Depends(current_user), contains JWT claims

    Returns JSON:
    {
      "thread_id": string,
      "summary": ["bullet1", "bullet2", ...],
      "checklist": [{"text": ..., "checked": false}, ...],
      "priority": "High" | "Normal"
    }
    """
    # Extract the cognito user ID (sub) for multi-tenant isolation
    user_id = user["sub"]

    # Reference to our DynamoDB table where we store messages and AI metadata
    table = ddb.Table("triagely-messages")

    # Primary key for this item: partition=UserID, sort=MessageID
    key = {"UserID": user_id, "MessageID": thread_id}

    # 1️⃣ Attempt to read the existing item from DynamoDB
    resp = table.get_item(Key=key)
    item = resp.get("Item", {})  # default to empty dict if no Item

    # If both aiSummary and aiChecklist are non-empty, we assume this is already processed
    if item.get("aiSummary") and item.get("aiChecklist"):
        # Return the cached values, including any previously stored priority
        return {
            "thread_id": thread_id,
            "summary": item["aiSummary"],
            "checklist": item["aiChecklist"],
            # Default to "Normal" priority if none saved
            "priority": item.get("priority", "Normal"),
        }

    # 2️⃣ No cached AI metadata found → generate fresh
    # 2a) Summarize the thread into bullet points
    sum_res = summarise_thread(user_id, thread_id)
    summary = sum_res["summary"]

    # 2b) Extract explicit action items into a checklist
    chk_res   = extract_checklist(user_id, thread_id)
    raw_items = chk_res.get("checklist", [])
    # Convert each line into an object with checked=false
    checklist = [{"text": line, "checked": False} for line in raw_items]

    # 2c) Classify overall priority: High vs Normal
    prio_res = classify_priority(user_id, thread_id)
    priority = prio_res.get("priority", "Normal")

    # 3️⃣ Persist the newly generated metadata back into DynamoDB
    #    so we never re-run the LLM for this message again
    table.update_item(
        Key=key,
        UpdateExpression="SET aiSummary = :s, aiChecklist = :c, priority = :p",
        ExpressionAttributeValues={
            ":s": summary,
            ":c": checklist,
            ":p": priority,
        },
    )

    # Finally, return the freshly generated data
    return {
        "thread_id": thread_id,
        "summary": summary,
        "checklist": checklist,
        "priority": priority,
    }


@router.post("/checklists/{thread_id}")
async def create_checklist(thread_id: str, user=Depends(current_user)):
    """
    Lightweight wrapper to return just the checklist via LLM.
    Does NOT cache — you can choose to cache separately if desired.
    """
    return await extract_checklist(user["sub"], thread_id)


@router.post("/priority/{thread_id}")
def create_priority(thread_id: str, user=Depends(current_user)):
    """
    Lightweight wrapper to return just the priority via LLM.
    Does NOT cache — see /summaries/{thread_id} for caching logic.
    """
    return classify_priority(user["sub"], thread_id)
