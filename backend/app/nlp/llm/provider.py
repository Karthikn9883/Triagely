# app/nlp/llm/provider.py

"""
This module encapsulates the interface to various LLM providers (OpenAI, AWS Bedrock, or a mock fallback).
It exposes a single `call` function that dynamically delegates to the configured provider based on environment variables.

Key components:
- LLMRequest: Typed schema for all requests (prompt + generation parameters).
- _openai_call: Handles calls to the OpenAI Chat Completions API.
- _bedrock_call: Handles calls to AWS Bedrock for model inference.
- call: Chooses provider at runtime or falls back to a mock for local development.
"""

import os
import json
import boto3
import httpx
from pydantic import BaseModel


class LLMRequest(BaseModel):
    """
    Standardized request model for LLM invocations.

    Attributes:
        prompt (str): The user/system instruction and content to send to the model.
        max_tokens (int): Maximum number of tokens to generate in the response.
        temperature (float): Sampling temperature (creativity vs determinism).
    """
    prompt: str
    max_tokens: int = 200  # Reduced from 1024 to 200 for shorter responses
    temperature: float = 0.1  # Lower temperature for more consistent, concise responses


def _openai_call(req: LLMRequest) -> str:
    """
    Invoke the OpenAI Chat Completions API using the configured model.
    Includes retry logic with exponential backoff for rate limits.

    Steps:
      1) Read the API key from env var OPENAI_API_KEY.
      2) Fetch the preferred model ID from OPENAI_MODEL (default: gpt-4.1-nano).
      3) Make the chat.completions.create call with retry logic.
      4) Return the text of the first choice.

    Args:
        req (LLMRequest): The prompt and generation settings.
    Returns:
        str: The raw text response from the model.
    Raises:
        Exception: If all retry attempts fail.
    """
    import openai  # delayed import so it's only needed if OpenAI is used
    import time
    import logging
    
    log = logging.getLogger("openai.provider")
    openai.api_key = os.environ["OPENAI_API_KEY"]
    
    max_retries = 3
    base_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            resp = openai.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4.1-nano"),
                messages=[{"role": "user", "content": req.prompt}],
                temperature=req.temperature,
                max_tokens=req.max_tokens,
            )
            # Always take the first choice's message content
            return resp.choices[0].message.content
            
        except openai.RateLimitError as e:
            if attempt == max_retries - 1:
                log.error("OpenAI rate limit exceeded after %d attempts", max_retries)
                raise e
            
            # Exponential backoff: 0.5s, 1s, 2s
            delay = base_delay * (2 ** attempt)
            log.warning("OpenAI rate limit hit, retrying in %.1fs (attempt %d/%d)", 
                       delay, attempt + 1, max_retries)
            time.sleep(delay)
            
        except Exception as e:
            log.error("OpenAI API error: %s", e)
            raise e


def _bedrock_call(req: LLMRequest) -> str:
    """
    Invoke an AWS Bedrock model for inference.

    Steps:
      1) Create a Bedrock Runtime client in the configured region.
      2) Wrap the prompt, max_tokens, and temperature into a JSON payload.
      3) Call invoke_model with the given modelId from BEDROCK_MODEL.
      4) Parse and return the textual completion from the response body.

    Args:
        req (LLMRequest): The prompt and generation settings.
    Returns:
        str: The completion string.
    """
    # Create Bedrock runtime client (default region or env var AWS_REGION)
    brt = boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )
    # Prepare the JSON body for the request
    body = json.dumps({
        "prompt": req.prompt,
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
    })
    # Call the Bedrock model; modelId from env var or fallback
    resp = brt.invoke_model(
        modelId=os.getenv(
            "BEDROCK_MODEL",
            "anthropic.claude-3-sonnet-20240229-v1:0"
        ),
        body=body,
        contentType="application/json",
    )
    # The response body is a stream; parse and extract the completion field
    result = json.loads(resp["body"].read())
    return result.get("completion", "")


def call(req: LLMRequest) -> str:
    """
    Entry point for all LLM calls. Chooses the provider based on AI_PROVIDER env var:
      - "openai": use the OpenAI chat endpoint
      - "bedrock": use AWS Bedrock
      - otherwise: return a mock (for local/offline development)

    Args:
        req (LLMRequest): Standard LLM request payload.
    Returns:
        str: The model's text response.
    """
    provider = os.getenv("AI_PROVIDER", "mock").lower()
    if provider == "openai":
        return _openai_call(req)
    if provider == "bedrock":
        return _bedrock_call(req)

    # 🚧 Mock fallback: prefix with marker so it's clear in logs
    return "[MOCK] " + req.prompt[:60] + "..."
