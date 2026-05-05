import json
from agents.base import BaseAgent, llm_client
from config import LLM_MODEL

INTENTS = {
    "car_inquiry": "Customer is asking about Kia car models, prices, features, specs, or comparisons.",
    "schedule_appointment": "Customer wants to book a test drive, visit the dealership, or schedule an appointment.",
    "general": "General greeting, small talk, or unclear intent.",
}


class RouterAgent(BaseAgent):
    name = "RouterAgent"

    def run(self, conversation_history: list[dict], context: dict = None) -> str:
        """
        Classify the user's latest message into one of the defined intents.
        Returns the intent string.
        """
        last_message = conversation_history[-1]["content"]

        system = (
            "You are an intent classifier for a Kia car dealership chatbot. "
            "Given the user's message, return ONLY a JSON object with this exact format:\n"
            '{"intent": "<intent_name>", "summary": "<one line summary>"}\n\n'
            "Available intents:\n"
            + "\n".join(f"- {k}: {v}" for k, v in INTENTS.items())
        )

        response = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": last_message},
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
