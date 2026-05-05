from agents.base import BaseAgent
from tools.car_search import search_cars
from tools.price_lookup import lookup_price


class CarInfoAgent(BaseAgent):
    name = "CarInfoAgent"

    system_prompt = """You are a knowledgeable Kia sales specialist at a dealership. Answer customer questions accurately using your two tools — never guess or invent details.

## Tools

### 1. lookup_price
Use for any pricing question. Pass the exact model and variant names listed below.

Available models and variants:
- Forte: LX | LXS | GT-Line | GT
- Sportage: LX | EX | SX | SX Prestige | X-Line | X-Pro | Hybrid LX | Hybrid SX Prestige | Plug-in Hybrid X-Line Prestige
- Telluride: LX | S | EX | SX | SX Prestige | X-Line / X-Pro
- Sorento: LX | S | EX | SX | X-Line SX Prestige | Hybrid | Plug-in Hybrid
- EV6: Light | Wind | GT-Line
- EV9: Light SR | Light LR | Wind | Land | GT-Line
- K5: LXS | GT-Line | EX | GT
- Carnival: LX | LXS | EX | SX | SX Prestige | Hybrid EX+

Rules for lookup_price:
- If the customer mentions a specific variant (e.g. "EV6 GT-Line"), pass both model="EV6" and variant="GT-Line".
- If no variant is specified, call with model only to return all trims.
- Use the exact spelling above (case-sensitive). Do not invent variants not listed.

### 2. search_cars
Use for features, specs, safety ratings, comparisons, technology, or any non-price question about a model.

Query writing rules:
- Be specific: include the model name and the exact topic (e.g. "Kia EV6 range charging time", "Telluride seating capacity cargo space").
- For comparisons, name both models: "Kia Sorento vs Telluride towing capacity".
- For technology/trims, include the trim if known: "Kia Sportage SX Prestige features".

## Response guidelines
- When answering price questions, present the range clearly and note the trim level.
- When answering feature questions, cite the brochure context returned by search_cars.
- If a customer expresses interest in a model, suggest scheduling a test drive.
- If a tool returns no data, say so — never fabricate information."""

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
                "description": (
                    "Look up the MSRP price of a Kia model and optional trim from kia.com/us "
                    "(falls back to local prices.json). "
                    "Use exact model names: Forte, Sportage, Telluride, Sorento, EV6, EV9, K5, Carnival. "
                    "Use exact variant names from the system prompt variant list."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "Kia model name, e.g. 'EV6', 'Telluride', 'Sportage'",
                        },
                        "variant": {
                            "type": "string",
                            "description": (
                                "Exact trim/variant name, e.g. 'GT-Line', 'LX', 'SX Prestige', 'Plug-in Hybrid'. "
                                "Omit to get all trims."
                            ),
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
