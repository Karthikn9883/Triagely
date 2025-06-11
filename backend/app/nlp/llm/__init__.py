"""
High-level LLM helpers (Bedrock / OpenAI).
Exposed publicly as `from app.nlp.llm import summarise_thread, extract_checklist`.
"""
from .summarizer import summarise_thread
from .checklist  import extract_checklist     # <-- now exists
