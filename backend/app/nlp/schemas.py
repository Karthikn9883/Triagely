# app/nlp/schemas.py

# This module defines the response schemas for the NLP (Natural Language Processing)
# endpoints of the Triagely backend. We use Pydantic models to enforce
# structure, validation, and documentation of the JSON payloads exchanged
# between the client and server for summary, checklist, and priority operations.

from pydantic import BaseModel
from typing import List, Dict


class SummaryResponse(BaseModel):
    """
    Schema for the Summary endpoint (/nlp/summaries/{thread_id}).

    Attributes:
        thread_id (str): The unique identifier of the email thread.
        summary (List[str]): A list of bullet points summarizing the thread.
    """
    # The ID of the email thread for which the summary was generated.
    thread_id: str
    # A list of string bullet points representing the AI-generated summary.
    summary: List[str]


class ChecklistResponse(BaseModel):
    """
    Schema for the Checklist endpoint (/nlp/checklists/{thread_id}).

    Attributes:
        thread_id (str): The unique identifier of the email thread.
        checklist (List[Dict]): A list of action-item objects.
            Each object typically contains:
              - text (str): The action item description.
              - checked (bool) [optional]: Whether the action is marked done.
    """
    # The ID of the email thread for which the checklist was extracted.
    thread_id: str
    # List of checklist items; flexible Dict allows future extension.
    checklist: List[Dict]


class PriorityResponse(BaseModel):
    """
    Schema for the Priority endpoint (/nlp/priority/{thread_id}).

    Attributes:
        thread_id (str): The unique identifier of the email thread.
        priority (str): The AI-classified priority label, e.g. "High" or "Normal".
    """
    # The ID of the email thread for which priority was determined.
    thread_id: str
    # The priority level assigned by the LLM.
    priority: str
