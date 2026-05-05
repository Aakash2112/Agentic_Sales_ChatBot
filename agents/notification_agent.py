from agents.base import BaseAgent
from tools.notifications import send_notifications


class NotificationAgent(BaseAgent):
    name = "NotificationAgent"

    def run(self, conversation_history: list[dict], context: dict = None) -> str:
        """
        Sends appointment confirmation via email and WhatsApp.
        Expects context = {"appointment": {...}}
        """
        appointment = context.get("appointment") if context else None
        if not appointment:
            return "No appointment data provided to NotificationAgent."

        print(f"  [NotificationAgent] Sending notifications for {appointment['id']}")
        status = send_notifications(appointment)

        parts = []
        if status.get("email_sent"):
            parts.append(f"email ({appointment['email']})")
        if status.get("whatsapp_sent"):
            parts.append(f"WhatsApp ({appointment['phone']})")

        if parts:
            return f"Confirmation sent via {' and '.join(parts)}."
        return "Failed to send confirmations. Please check your Twilio and email settings."
