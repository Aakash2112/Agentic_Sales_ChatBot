"""
Multi-agent orchestrator for the Kia Sales ChatBot.

Flow:
  User message
      ↓
  RouterAgent  — classifies intent
      ↓
  ┌─────────────────────────────────┐
  │ car_inquiry → CarInfoAgent      │
  │ schedule_appointment            │
  │   → BookingAgent (bookingagent) │
  │ general → direct LLM reply      │
  └─────────────────────────────────┘
"""

from agents.base import llm_client
from config import LLM_MODEL, PHONE_LLM_MODEL
from agents.router import RouterAgent
from agents.car_info_agent import CarInfoAgent
from bookingagent import run as booking_run

router = RouterAgent()
car_info_agent = CarInfoAgent()

GENERAL_SYSTEM = (
    "You are a friendly Kia dealership assistant. "
    "You only assist with Kia vehicles and dealership services. "
    "For greetings or general questions, respond warmly and guide the customer toward Kia models or booking a test drive. "
    "If the customer asks about any other car brand or an unrelated topic, politely decline and redirect: "
    "\"I'm only able to help with Kia vehicles and our dealership services. Is there a Kia model I can tell you about?\""
)

PHONE_ADDENDUM = (
    " You are responding on a live phone call. "
    "Speak in plain natural English sentences only. "
    "Never use markdown, bullet points, lists, URLs, or special characters. "
    "Keep it to 2 to 4 sentences and end with a follow-up question."
)


def handle(conversation_history: list[dict], step_callback=None, mode: str = "chat") -> str:
    """
    Process the latest user message and return the assistant's response.

    Args:
        conversation_history: Full chat history (user + assistant turns).
        step_callback: Optional callable(agent_name, detail) for UI progress updates.
        mode: "chat" for Chainlit UI, "phone" for voice calls.
    """
    def notify(agent_name, detail=""):
        if step_callback:
            step_callback(agent_name, detail)
        else:
            print(f"  [Orchestrator] → {agent_name} {detail}")

    # Phone mode: use fast keyword routing to skip LLM router call
    if mode == "phone":
        last = conversation_history[-1]["content"].lower()
        booking_keywords = {"book", "schedule", "appointment", "test drive", "reserve", "reschedule"}
        car_keywords = {"price", "cost", "feature", "spec", "model", "range", "mpg", "engine",
                        "ev6", "ev9", "telluride", "sorento", "sportage", "k4", "k5", "niro",
                        "carnival", "forte", "seltos", "tell me about", "how much", "compare"}
        if any(kw in last for kw in booking_keywords):
            intent = "schedule_appointment"
        elif any(kw in last for kw in car_keywords):
            intent = "car_inquiry"
        else:
            intent = "general"
        notify("Router", f"intent={intent} (keyword fast-path)")
    else:
        intent = router.run(conversation_history)
        notify("Router", f"intent={intent}")

    if intent == "car_inquiry":
        notify("CarInfoAgent")
        return car_info_agent.run(conversation_history, mode=mode)

    elif intent == "schedule_appointment":
        notify("BookingAgent")
        return booking_run(conversation_history, mode=mode)

    else:
        notify("GeneralAgent")
        system = GENERAL_SYSTEM + (PHONE_ADDENDUM if mode == "phone" else "")
        messages = [{"role": "system", "content": system}] + conversation_history
        resp = llm_client.chat.completions.create(
            model=PHONE_LLM_MODEL if mode == "phone" else LLM_MODEL,
            messages=messages,
            temperature=0.5,
        )
        return resp.choices[0].message.content
