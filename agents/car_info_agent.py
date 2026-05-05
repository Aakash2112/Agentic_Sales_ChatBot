from agents.base import BaseAgent
from tools.car_search import search_cars
from tools.price_lookup import lookup_price


class CarInfoAgent(BaseAgent):
    name = "CarInfoAgent"

    system_prompt = (
        "You are a knowledgeable Kia sales specialist. "
        "You have two tools:\n"
        "1. search_cars — retrieves detailed information (features, specs, comparisons) from our Kia catalog.\n"
        "2. lookup_price — fetches current MSRP pricing from kia.com/us (with a local fallback).\n\n"
        "Always use the appropriate tool before answering. "
        "Never make up car details or prices. "
        "If the customer shows interest in a specific model, gently suggest scheduling a test drive."
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_cars",
                "description": "Search the Kia catalog for model details, features, specs, and comparisons.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "e.g. 'Kia EV6 range and features' or 'Telluride vs Sorento'",
                        }
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "lookup_price",
                "description": "Look up the MSRP price of a Kia model from kia.com/us.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "Kia model name, e.g. 'EV6', 'Telluride', 'Sportage'",
                        },
                        "variant": {
                            "type": "string",
                            "description": "Optional trim/variant, e.g. 'GT-Line', 'LX'",
                        },
                    },
                    "required": ["model"],
                },
            },
        },
    ]

    tool_handlers = {
        "search_cars": lambda args: search_cars(args["query"]),
        "lookup_price": lambda args: lookup_price(args["model"], args.get("variant")),
    }

    def run(self, conversation_history: list[dict], context: dict = None) -> str:
        messages = [{"role": "system", "content": self.system_prompt}] + conversation_history
        return self._run_loop(messages)
