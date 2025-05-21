from pydantic import BaseModel

class SlackConnectURL(BaseModel):
    auth_url: str
