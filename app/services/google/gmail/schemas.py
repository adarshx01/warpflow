from pydantic import BaseModel, UUID4
from typing import Literal, Any


class GmailExecuteRequest(BaseModel):
    credentialId: UUID4
    operation: Literal[
        "send_email", "list_messages", "get_message",
        "search_messages", "trash_message", "list_labels",
    ]
    params: dict[str, Any]
