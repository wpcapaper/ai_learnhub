from collections.abc import AsyncGenerator
from typing import Optional, Any

from .usage import LlmUsage


class StreamUsageCollector:
    def __init__(self, stream: AsyncGenerator[Any, None]):
        self._stream = stream
        self.usage: Optional[LlmUsage] = None

    async def iter(self) -> AsyncGenerator[Any, None]:
        async for chunk in self._stream:
            if getattr(chunk, "usage", None):
                usage = chunk.usage
                self.usage = LlmUsage(
                    input=usage.get("prompt_tokens"),
                    output=usage.get("completion_tokens"),
                    total=usage.get("total_tokens"),
                )
                continue
            yield chunk
