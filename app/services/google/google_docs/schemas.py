from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Literal, Any


class CredentialCreate(BaseModel):
    type: str
    name: str
    client_id: str
    client_secret: str


class CredentialResponse(BaseModel):
    id: UUID4
    type: str
    name: str
    has_tokens: bool  # True if access_token is set

    class Config:
        from_attributes = True


class ExecuteRequest(BaseModel):
    credentialId: UUID4
    operation: Literal["create", "get", "update", "delete", "find_text"]
    params: dict[str, Any]
