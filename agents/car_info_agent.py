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
- Seltos: LX | S | EX | SX | SX Prestige | Nightfall Edition
- K4: LX | LXS | GT-Line | EX
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
- Only answer questions about Kia vehicles. If asked about any other brand, respond: "I can only assist with Kia vehicles. Would you like to know about a specific Kia model?"
- When answering price questions, present the range clearly and note the trim level.
- When answering feature questions, cite the brochure context returned by search_cars.
- If a customer expresses interest in a model, suggest scheduling a test drive for **that exact model** — never substitute or mention a different model.
- If the search results returned by a tool are about a different model than what the customer asked, disregard them and tell the customer you don't have information on that specific model.
- If a tool returns no data, say so — never fabricate information.

## Closing your response
End each response with a natural, context-aware follow-up — vary it based on what was just discussed:
- After a comparison: ask which model resonates more, or what other factors matter to them.
- After a pricing answer: ask if that budget range works or if they'd like to explore a specific trim.
- After a features/specs answer: ask if that feature is a must-have or if they'd like to know about another aspect.
- Only suggest a test drive after the customer has asked at least 2 questions and seems genuinely interested — not after every response.
- Never repeat the same closing two responses in a row."""

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
                    "Use exact model names: Seltos, K4, Forte, Sportage, Telluride, Sorento, EV6, EV9, K5, Carnival. "
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

    PHONE_ADDENDUM = (
        "\n\nIMPORTANT: You are responding on a live phone call. "
        "You MUST follow these rules strictly:\n"
        "- Speak in plain natural English sentences only\n"
        "- NEVER use markdown, asterisks, dashes, bullet points, numbered lists, or hashtags\n"
        "- NEVER include URLs or website links\n"
        "- NEVER use special characters like ®, ™, ©, or emoji\n"
        "- Keep the response to 2 to 4 natural spoken sentences\n"
        "- End with a simple follow-up question to keep the conversation going"
    )

    def run(self, conversation_history: list[dict], context: dict = None, mode: str = "chat") -> str:
        from config import PHONE_LLM_MODEL, LLM_MODEL
        prompt = self.system_prompt + (self.PHONE_ADDENDUM if mode == "phone" else "")
        messages = [{"role": "system", "content": prompt}] + conversation_history
        model = PHONE_LLM_MODEL if mode == "phone" else LLM_MODEL
        return self._run_loop(messages, model=model)
