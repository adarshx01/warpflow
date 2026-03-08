from pydantic import BaseModel
from typing import Literal, Any


class GeminiExecuteRequest(BaseModel):
    apiKey: str
    operation: Literal["generate_content", "chat"]
    params: dict[str, Any]
