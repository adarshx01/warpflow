from pydantic import BaseModel, UUID4
from typing import Literal, Any


class FormsExecuteRequest(BaseModel):
    credentialId: UUID4
    operation: Literal[
        "create", "get", "list_responses", "get_response", "update",
    ]
    params: dict[str, Any]
