import os, json, boto3, httpx
from pydantic import BaseModel

class LLMRequest(BaseModel):
    prompt: str
    max_tokens: int = 1024
    temperature: float = 0.3

def _openai_call(req: LLMRequest) -> str:
    import openai
    openai.api_key = os.environ["OPENAI_API_KEY"]
    resp = openai.chat.completions.create(
        model   = os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": req.prompt}],
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )
    return resp.choices[0].message.content

def _bedrock_call(req: LLMRequest) -> str:
    brt = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
    body = json.dumps({"prompt": req.prompt,
                       "max_tokens": req.max_tokens,
                       "temperature": req.temperature})
    resp = brt.invoke_model(
        modelId = os.getenv("BEDROCK_MODEL", "anthropic.claude-3-sonnet-20240229-v1:0"),
        body    = body,
        contentType="application/json",
    )
    return json.loads(resp["body"].read())["completion"]

def call(req: LLMRequest) -> str:
    provider = os.getenv("AI_PROVIDER", "mock")
    if provider == "openai":
        return _openai_call(req)
    if provider == "bedrock":
        return _bedrock_call(req)
    # mock fallback for offline/local dev
    return "[MOCK] " + req.prompt[:60] + "..."
