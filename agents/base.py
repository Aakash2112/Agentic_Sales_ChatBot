import json
from openai import OpenAI
from config import OLLAMA_BASE_URL, LLM_MODEL

llm_client = OpenAI(
    api_key="ollama",
    base_url=OLLAMA_BASE_URL,
)


class BaseAgent:
    """Base class for all agents. Handles the OpenRouter tool-use loop."""

    name: str = "BaseAgent"
    system_prompt: str = ""
    tools: list = []
    tool_handlers: dict = {}

    def _run_loop(self, messages: list[dict], model: str = None) -> str:
        """Run the tool-use loop until the model returns a final text response."""
        while True:
            kwargs = {"model": model or LLM_MODEL, "messages": messages, "temperature": 0.3}
            if self.tools:
                kwargs["tools"] = self.tools
                kwargs["tool_choice"] = "auto"

            response = llm_client.chat.completions.create(**kwargs)
            message = response.choices[0].message

            if not message.tool_calls:
                return message.content

            # Append assistant tool-call message
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            # Execute tools and append results
            for tc in message.tool_calls:
                tool_name = tc.function.name
                tool_args = json.loads(tc.function.arguments)
                print(f"    [{self.name}] calling tool: {tool_name}")

                handler = self.tool_handlers.get(tool_name)
                result = handler(tool_args) if handler else f"Unknown tool: {tool_name}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result) if not isinstance(result, str) else result,
                })

    def run(self, conversation_history: list[dict], context: dict = None) -> str:
        raise NotImplementedError
