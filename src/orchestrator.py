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
  │   → AppointmentAgent            │
  │       ↓ (if booked)             │
  │   → NotificationAgent           │
  │ general → direct LLM reply      │
  └─────────────────────────────────┘
"""

from agents.base import llm_client
from config import LLM_MODEL
from agents.router import RouterAgent
from agents.car_info_agent import CarInfoAgent
from agents.appointment_agent import AppointmentAgent
from agents.notification_agent import NotificationAgent

router = RouterAgent()
car_info_agent = CarInfoAgent()
appointment_agent = AppointmentAgent()
notification_agent = NotificationAgent()

GENERAL_SYSTEM = (
    "You are a friendly Kia dealership assistant. "
    "You only assist with Kia vehicles and dealership services. "
    "For greetings or general questions, respond warmly and guide the customer toward Kia models or booking a test drive. "
    "If the customer asks about any other car brand or an unrelated topic, politely decline and redirect: "
    "\"I'm only able to help with Kia vehicles and our dealership services. Is there a Kia model I can tell you about?\""
)


def handle(conversation_history: list[dict], step_callback=None) -> str:
    """
    Process the latest user message and return the assistant's response.

    Args:
        conversation_history: Full chat history (user + assistant turns).
        step_callback: Optional callable(agent_name, detail) for UI progress updates.
    """
    def notify(agent_name, detail=""):
        if step_callback:
            step_callback(agent_name, detail)
        else:
            print(f"  [Orchestrator] → {agent_name} {detail}")

    intent = router.run(conversation_history)
    notify("Router", f"intent={intent}")

    if intent == "car_inquiry":
        notify("CarInfoAgent")
        return car_info_agent.run(conversation_history)

    elif intent == "schedule_appointment":
        notify("AppointmentAgent")
        response, appointment = appointment_agent.run(conversation_history)

        if appointment:
            notify("NotificationAgent", f"ref={appointment['id']}")
            notif_status = notification_agent.run(
                conversation_history,
                context={"appointment": appointment},
            )
            response = f"{response}\n\n{notif_status}"

        return response

    else:
        notify("GeneralAgent")
        messages = [{"role": "system", "content": GENERAL_SYSTEM}] + conversation_history
        resp = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.5,
        )
        return resp.choices[0].message.content
