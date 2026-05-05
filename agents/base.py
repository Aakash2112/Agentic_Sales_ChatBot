import json
import time
from openai import OpenAI, RateLimitError, NotFoundError
from config import OLLAMA_API_KEY, OLLAMA_BASE_URL, LLM_MODEL, LLM_FALLBACK_MODELS

llm_client = OpenAI(
    api_key=OLLAMA_API_KEY,
    base_url=OLLAMA_BASE_URL,
)


class BaseAgent:
    """Base class for all agents. Handles the Ollama tool-use loop."""

    name: str = "BaseAgent"
    system_prompt: str = ""
    tools: list = []
    tool_handlers: dict = {}

    def _call_llm(self, kwargs: dict) -> object:
        """Call LLM with retry + backoff on rate limit, then fallback models."""
        models = [LLM_MODEL] + LLM_FALLBACK_MODELS
        for model in models:
            for attempt in range(3):
                try:
                    return llm_client.chat.completions.create(**{**kwargs, "model": model})
                except NotFoundError:
                    print(f"    [{self.name}] {model} not found, skipping.")
                    break
                except RateLimitError:
                    wait = 5 * (attempt + 1)
                    print(f"    [{self.name}] {model} rate-limited, retrying in {wait}s...")
                    time.sleep(wait)
        raise RuntimeError("All models rate-limited. Please wait a moment and try again.")

    def _run_loop(self, messages: list[dict]) -> str:
        """Run the tool-use loop until the model returns a final text response."""
        while True:
            kwargs = {"model": LLM_MODEL, "messages": messages, "temperature": 0.3}
            if self.tools:
                kwargs["tools"] = self.tools
                kwargs["tool_choice"] = "auto"

            response = self._call_llm(kwargs)
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
