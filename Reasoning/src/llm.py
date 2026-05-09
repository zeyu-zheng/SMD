from dataclasses import dataclass

from openai import AzureOpenAI

from utils import Config

MAX_OUTPUT_TOKENS = 20000


@dataclass
class LLMClient:
    config: Config
    calls: int = 0

    def __post_init__(self) -> None:
        self.client = AzureOpenAI(
            base_url=self.config.api.resolved_base_url(),
            api_key=self.config.api.resolved_key(),
            api_version=self.config.api.api_version,
        )

    async def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls += 1
        params = {
            "model": self.config.model,
            "input": "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in messages),
            "reasoning": {"effort": self.config.reasoning_effort},
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        }
        if self.config.web_search:
            params["tools"] = [{"type": "web_search_preview"}]
        response = self.client.responses.create(**params)
        chunks: list[str] = []
        for item in response.output:
            if hasattr(item, "content") and item.content:
                for content in item.content:
                    if hasattr(content, "text"):
                        chunks.append(content.text)
        return "\n".join(chunks)
