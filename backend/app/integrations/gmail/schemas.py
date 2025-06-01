from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict


class GmailMessage(BaseModel):
    """
    A single row returned to the React app.
    – list-view gets the header fields only
    – detail-view (/messages/{id}) includes plain / html + AI meta
    """

    # Dynamo keys
    MessageID: str

    # Envelope / preview
    subject: str = "(No subject)"
    snippet: str = ""
    sender: str = ""
    senderEmail: Optional[str] = None

    # ISO-8601 date string *always* present after the latest backend fix
    dateISO: Optional[str] = None

    # Flags
    urgent: bool = False

    # Body (present only for the detail call)
    plain: Optional[str] = None
    html: Optional[str] = None

    # AI enrichment (place-holders for later)
    aiSummary: List[str]            = Field(default_factory=list)
    aiChecklist: List[Dict]         = Field(default_factory=list)

    # --- Pydantic v2 tweaks ---------------------------------------------
    model_config = ConfigDict(populate_by_name=True)   # let alias names populate

    # Back-compat: some old client code might still ask for `date`
    @property
    def date(self) -> Optional[str]:                   # noqa: D401
        """Alias for dateISO (kept for legacy code)."""
        return self.dateISO
