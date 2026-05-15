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
            azure_endpoint=self.config.api.resolved_responses_base_url(),
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
        response_input: list[dict[str, Any]] = list(messages)
        response_tools = [responses_tool(tool) for tool in tools] if tools else []
        called_tools: set[str] = set()
        attempts = 0

        while True:
            response = await self.create_response(response_input, response_tools, use_web_search=self.config.web_search and attempts == 0)
            content = await self.run_tools(response_input, response, response_tools, tool_handlers or {}, called_tools)

            feedback = None
            if validate_no_tool_call is not None:
                feedback = validate_no_tool_call(called_tools)
            if (feedback is None or feedback.get("success", True)) and validate_result is not None:
                feedback = validate_result(content)
            if feedback is None or feedback.get("success", True):
                return content

            attempts += 1
            if attempts > max_no_tool_call:
                return content
            if content:
                response_input.append({"role": "assistant", "content": content})
            response_input.append({"role": "user", "content": feedback["message"]})

    async def create_response(self, response_input: list[dict[str, Any]], tools: list[dict[str, Any]], use_web_search: bool) -> Any:
        self.calls += 1
        params: dict[str, Any] = {
            "model": self.config.model,
            "input": response_input,
        }
        if self.config.reasoning_effort:
            params["reasoning"] = {"effort": self.config.reasoning_effort}
        active_tools = list(tools)
        if use_web_search:
            active_tools.append({"type": "web_search"})
        if active_tools:
            params["tools"] = active_tools
        return self.client.responses.create(**params)

    async def run_tools(
        self,
        response_input: list[dict[str, Any]],
        response: Any,
        tools: list[dict[str, Any]],
        tool_handlers: dict[str, Callable[[dict[str, Any]], Any]],
        called_tools: set[str],
    ) -> str:
        while True:
            function_calls = [item for item in getattr(response, "output", []) or [] if getattr(item, "type", None) == "function_call"]
            if not function_calls:
                return extract_responses_text(response)

            for call in function_calls:
                name = call.name
                called_tools.add(name)
                response_input.append({
                    "type": "function_call",
                    "call_id": call.call_id,
                    "name": name,
                    "arguments": call.arguments or "{}",
                })
                if name not in tool_handlers:
                    continue
                arguments = json.loads(call.arguments or "{}")
                result = tool_handlers[name](arguments)
                if inspect.isawaitable(result):
                    result = await result
                response_input.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                })
            response = await self.create_response(response_input, tools, use_web_search=False)


def responses_tool(tool: dict[str, Any]) -> dict[str, Any]:
    if tool.get("type") != "function":
        return tool
    return {
        "type": "function",
        "name": tool["name"],
        "description": tool.get("description", ""),
        "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
    }


def extract_responses_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text
    parts = []
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) != "message":
            continue
        for part in getattr(item, "content", []) or []:
            part_text = getattr(part, "text", None)
            if part_text:
                parts.append(part_text)
    return "\n".join(parts)
