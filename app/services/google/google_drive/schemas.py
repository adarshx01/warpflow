from pydantic import BaseModel, UUID4
from typing import Literal, Any


class DriveExecuteRequest(BaseModel):
    credentialId: UUID4
    operation: Literal[
        "list_files", "get_file", "upload_file", "delete_file",
        "create_folder", "share_file", "download_file",
    ]
    params: dict[str, Any]
