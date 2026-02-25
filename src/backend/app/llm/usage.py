from pydantic import BaseModel
from typing import Optional


class LlmUsage(BaseModel):
    input: Optional[int] = None
    output: Optional[int] = None
    total: Optional[int] = None
