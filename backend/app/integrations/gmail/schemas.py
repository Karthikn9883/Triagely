from pydantic import BaseModel

class GmailConnectURL(BaseModel):
    auth_url: str
