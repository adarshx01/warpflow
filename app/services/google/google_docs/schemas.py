from pydantic import BaseModel, UUID4
from typing import Literal, Any


class ExecuteRequest(BaseModel):
    credentialId: UUID4
    operation: Literal["create", "get", "update", "delete", "find_text"]
    params: dict[str, Any]
