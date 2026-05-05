import json
from agents.base import BaseAgent, llm_client
from config import LLM_MODEL

INTENTS = {
    "car_inquiry": "Customer is asking about Kia car models, prices, features, specs, or comparisons — with no intent to book.",
    "schedule_appointment": (
        "Customer wants to book or schedule a test drive, dealership visit, or appointment. "
        "ALSO use this if a booking is already in progress (e.g. customer is providing their name, "
        "email, phone, preferred date/time, or any other detail needed to complete a booking)."
    ),
    "general": "General greeting, small talk, unclear intent, OR questions about non-Kia brands/competitors.",
}

# Keywords that strongly indicate a booking is in progress
_BOOKING_KEYWORDS = {
    "name is", "my name", "email is", "my email", "phone is", "my phone",
    "number is", "my number", "tomorrow", "next week", "monday", "tuesday",
    "wednesday", "thursday", "friday", "saturday", "9am", "10am", "11am",
    "12pm", "2pm", "3pm", "4pm", "5pm", "@", ".com",
}


def _booking_in_progress(conversation_history: list[dict]) -> bool:
    """Return True if the assistant has already started collecting booking details."""
    booking_triggers = {"name", "email", "phone", "date", "time", "model", "test drive", "book", "schedule"}
    for turn in reversed(conversation_history[:-1]):  # skip last user message
        if turn["role"] == "assistant":
            text = turn["content"].lower()
            if any(kw in text for kw in booking_triggers):
                return True
            break
    return False


class RouterAgent(BaseAgent):
    name = "RouterAgent"

    def run(self, conversation_history: list[dict], context: dict = None) -> str:
        """
        Classify the user's latest message into one of the defined intents.
        Returns the intent string.
        """
        last_message = conversation_history[-1]["content"].lower()

        # Fast-path: if booking is already in progress and the user message looks
        # like they're providing details, skip the LLM call.
        if _booking_in_progress(conversation_history) and any(
            kw in last_message for kw in _BOOKING_KEYWORDS
        ):
            print("  [Router] intent=schedule_appointment | booking in progress (fast-path)")
            return "schedule_appointment"

        # Build recent context (last 4 turns) for the LLM classifier
        recent = conversation_history[-4:]
        context_text = "\n".join(
            f"{t['role'].upper()}: {t['content']}" for t in recent
        )

        system = (
            "You are an intent classifier for a Kia car dealership chatbot. "
            "Given the conversation context, return ONLY a JSON object:\n"
            '{"intent": "<intent_name>", "summary": "<one line summary>"}\n\n'
            "IMPORTANT: If the customer mentions booking OR a test drive, even alongside a car model, "
            "always classify as schedule_appointment — not car_inquiry.\n\n"
            "Available intents:\n"
            + "\n".join(f"- {k}: {v}" for k, v in INTENTS.items())
        )

        response = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Conversation:\n{context_text}"},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        try:
            result = json.loads(raw)
            intent = result.get("intent", "general")
            print(f"  [Router] intent={intent} | {result.get('summary', '')}")
            return intent
        except Exception:
            return "general"
