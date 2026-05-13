from dataclasses import dataclass
import inspect
import json
from typing import Any, Callable

from openai import AzureOpenAI

from src.core.config import Config


@dataclass
class LLMClient:
    config: Config
    calls: int = 0

    def __post_init__(self) -> None:
        self.client = AzureOpenAI(
            azure_endpoint=self.config.api.resolved_base_url(),
            api_key=self.config.api.resolved_key(),
            api_version=self.config.api.api_version,
            timeout=self.config.api.timeout,
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        tool_handlers: dict[str, Callable[[dict[str, Any]], Any]] | None = None,
        validate_result: Callable[[str], dict[str, Any]] | None = None,
        validate_no_tool_call: Callable[[set[str]], dict[str, Any]] | None = None,
        max_no_tool_call: int = 2,
    ) -> str:
        chat_messages: list[dict[str, Any]] = list(messages)
        chat_tools = [chat_tool(tool) for tool in tools] if tools else None
        called_tools: set[str] = set()
        no_tool_count = 0

        while True:
            response = await self.create_response(chat_messages, chat_tools)
            if tools and tool_handlers:
                response = await self.run_tools(chat_messages, response, tool_handlers, chat_tools, called_tools)
            message = response.choices[0].message
            content = message.content or ""

            feedback = None
            if validate_no_tool_call is not None:
                feedback = validate_no_tool_call(called_tools)
            if (feedback is None or feedback.get("success", True)) and validate_result is not None:
                feedback = validate_result(content)
            if feedback is None or feedback.get("success", True):
                return content

            no_tool_count += 1
            if no_tool_count > max_no_tool_call:
                return content
            chat_messages.append(message.model_dump())
            chat_messages.append({"role": "user", "content": feedback["message"]})

    async def create_response(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> Any:
        self.calls += 1
        params = {
            "model": self.config.model,
            "messages": messages,
        }
        if self.config.reasoning_effort:
            params["reasoning_effort"] = self.config.reasoning_effort
        if tools:
            params["tools"] = tools
        return self.client.chat.completions.create(**params)

    async def run_tools(self, messages: list[dict[str, Any]], response: Any, tool_handlers: dict[str, Callable[[dict[str, Any]], Any]], tools: list[dict[str, Any]] | None, called_tools: set[str]) -> Any:
        while True:
            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None) or []
            if not tool_calls:
                return response
            messages.append(message.model_dump())
            for call in tool_calls:
                name = call.function.name
                called_tools.add(name)
                if name not in tool_handlers:
                    continue
                arguments = json.loads(call.function.arguments or "{}")
                result = tool_handlers[name](arguments)
                if inspect.isawaitable(result):
                    result = await result
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": name,
                    "content": json.dumps(result, ensure_ascii=False),
                })
            response = await self.create_response(messages, tools)


def chat_tool(tool: dict[str, Any]) -> dict[str, Any]:
    if tool.get("type") != "function" or "function" in tool:
        return tool
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
        },
    }
