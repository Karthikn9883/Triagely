from fastapi import APIRouter, Depends
from app.core.auth import current_user
from .llm import summarise_thread

router = APIRouter(prefix="/nlp", tags=["nlp"])

@router.post("/summaries/{thread_id}")
def create_summary(thread_id: str, user=Depends(current_user)):
    # change from user.id to user["sub"]
    return summarise_thread(user["sub"], thread_id)

@router.post("/checklists/{thread_id}")
async def create_checklist(thread_id: str, user=Depends(current_user)):
    return await extract_checklist(user.id, thread_id)
