import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from tools.car_search import search_cars
from tools.appointment import schedule_appointment
from tools.notifications import send_notifications

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are a helpful Kia sales assistant. Your job is to:
1. Answer customer questions about Kia cars using the search_cars tool.
2. Help interested customers schedule a test drive or dealership appointment.
3. Once an appointment is scheduled, send confirmations via email and WhatsApp.

Guidelines:
- Always use search_cars before answering questions about specific models, prices, or features.
- To schedule an appointment, collect: customer name, email, phone number, car model of interest, preferred date, and preferred time.
- After scheduling, always call send_notifications to confirm via email and WhatsApp.
- Be friendly, concise, and professional.
- If you don't know something, say so — do not make up car details.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_cars",
            "description": "Search the Kia car catalog for information about models, prices, features, and availability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query, e.g. 'Kia EV6 price' or 'Telluride seating capacity'",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_appointment",
            "description": "Schedule a test drive or dealership appointment for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Full name of the customer"},
                    "email": {"type": "string", "description": "Customer's email address"},
                    "phone": {"type": "string", "description": "Customer's phone number with country code, e.g. +12025551234"},
                    "car_model": {"type": "string", "description": "The Kia model they are interested in"},
                    "preferred_date": {"type": "string", "description": "Preferred appointment date, e.g. 2025-05-10"},
                    "preferred_time": {"type": "string", "description": "Preferred appointment time, e.g. 10:00 AM"},
                },
                "required": ["customer_name", "email", "phone", "car_model", "preferred_date", "preferred_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_notifications",
            "description": "Send appointment confirmation to the customer via email and WhatsApp.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment": {
                        "type": "object",
                        "description": "The full appointment object returned by schedule_appointment",
                    }
                },
                "required": ["appointment"],
            },
        },
    },
]

TOOL_HANDLERS = {
    "search_cars": lambda args: search_cars(args["query"]),
    "schedule_appointment": lambda args: schedule_appointment(**args),
    "send_notifications": lambda args: send_notifications(args["appointment"]),
}


def run_agent(conversation_history: list[dict]) -> str:
    """
    Run one turn of the agent loop.
    Handles tool calls automatically until the model returns a final text response.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

    while True:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )

        message = response.choices[0].message

        # No tool calls — final answer
        if not message.tool_calls:
            return message.content

        # Append assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ],
        })

        # Execute each tool call and append results
        for tc in message.tool_calls:
            tool_name = tc.function.name
            tool_args = json.loads(tc.function.arguments)

            print(f"  [Tool] {tool_name}({json.dumps(tool_args, indent=2) if len(str(tool_args)) < 200 else '...'})")

            handler = TOOL_HANDLERS.get(tool_name)
            if handler:
                result = handler(tool_args)
            else:
                result = f"Unknown tool: {tool_name}"

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result) if not isinstance(result, str) else result,
            })
