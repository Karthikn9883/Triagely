from fastapi import FastAPI, Depends
from app.core.auth import current_user
from app.integrations.gmail.router import router as gmail_router
from app.integrations.slack.router import router as slack_router

app = FastAPI()

@app.get("/health")
async def health(): return {"ok": True}

@app.get("/protected")
async def protected(u=Depends(current_user)): 
    print("USER OBJ:", u)
    return {
        "message": f"Hello, {u.get('email', 'unknown')} (sub: {u.get('sub')})"
    }

app.include_router(gmail_router)
app.include_router(slack_router)
 