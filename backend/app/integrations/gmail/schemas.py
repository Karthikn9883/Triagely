# app/integrations/gmail/schemas.py

"""
Pydantic model definitions for Gmail messages returned by the /gmail/messages endpoint.
Defines both list-view and detail-view fields, including AI metadata and persisted priority.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict


class GmailMessage(BaseModel):
    """
    Represents a single email thread/item in the Triagely UI.

    Attributes:
        MessageID   (str):   Unique key constructed as 'gmail-<address>-<threadId>'.
        subject     (str):   The email's Subject header or '(No subject)'.
        snippet     (str):   A short preview (snippet) from the email body.
        sender      (str):   The raw 'From' header (name and address).
        senderEmail (str?):  Parsed email address for display/links.
        dateISO     (str?):  ISO-8601 formatted timestamp of first message.

        priority    (str):   Persisted AI‐driven priority label ('High' or 'Normal').

        plain       (str?):  Full plain-text body (detail view only).
        html        (str?):  Full HTML body (detail view only).

        aiSummary   (List[str]):  Cached list of AI summary bullet points.
        aiChecklist (List[Dict]):  Cached checklist items (with text + checked flag).
        account     (str?):       Gmail address this message was fetched from.
    """

    MessageID:   str
    subject:     str
    snippet:     str
    sender:      str
    senderEmail: Optional[str]
    dateISO:     Optional[str]

    # Persisted AI‐driven priority: High or Normal
    priority:    str

    # Detail‐view bodies and AI metadata
    plain:       Optional[str]
    html:        Optional[str]
    aiSummary:   List[str]  = Field(default_factory=list)
    aiChecklist: List[Dict] = Field(default_factory=list)
    account:     Optional[str]

    # Pydantic v2 config: allow population by alias/name
    model_config = ConfigDict(populate_by_name=True)

    @property
    def date(self) -> Optional[str]:
        """
        Legacy alias for dateISO to maintain backward compatibility
        with older UI code that may reference `message.date`.
        """
        return self.dateISO
