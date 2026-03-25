from pydantic import BaseModel, UUID4
from typing import Literal, Any


class SheetsExecuteRequest(BaseModel):
    credentialId: UUID4
    operation: Literal[
        "create", "get", "read_values", "write_values",
        "append_values", "clear_values",
    ]
    params: dict[str, Any]
