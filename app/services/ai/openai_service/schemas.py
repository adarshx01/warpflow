from pydantic import BaseModel
from typing import Literal, Any


class OpenAIExecuteRequest(BaseModel):
    apiKey: str
    operation: Literal["chat_completion", "image_generation"]
    params: dict[str, Any]
