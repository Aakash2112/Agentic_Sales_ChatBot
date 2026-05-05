from agents.base import BaseAgent
from tools.appointment import schedule_appointment


class AppointmentAgent(BaseAgent):
    name = "AppointmentAgent"

    system_prompt = (
        "You are a Kia dealership appointment coordinator. "
        "Your job is to collect the following details from the customer and schedule a test drive:\n"
        "  1. Full name\n"
        "  2. Email address\n"
        "  3. Phone number (with country code, e.g. +1...)\n"
        "  4. Kia model they are interested in\n"
        "  5. Preferred date (YYYY-MM-DD)\n"
        "  6. Preferred time (e.g. 10:00 AM)\n\n"
        "Ask for missing details naturally in conversation. "
        "Once you have ALL details, call schedule_appointment immediately. "
        "Confirm the booking to the customer after the tool call."
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "schedule_appointment",
                "description": "Book a test drive or dealership visit once all customer details are collected.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {"type": "string"},
                        "email": {"type": "string"},
                        "phone": {"type": "string", "description": "With country code, e.g. +12025551234"},
                        "car_model": {"type": "string"},
                        "preferred_date": {"type": "string", "description": "Format: YYYY-MM-DD"},
                        "preferred_time": {"type": "string", "description": "e.g. 10:00 AM"},
                    },
                    "required": [
                        "customer_name", "email", "phone",
                        "car_model", "preferred_date", "preferred_time",
                    ],
                },
            },
        }
    ]

    tool_handlers = {
        "schedule_appointment": lambda args: schedule_appointment(**args),
    }

    def run(self, conversation_history: list[dict], context: dict = None) -> tuple[str, dict | None]:
        """
        Returns (response_text, appointment_dict_or_None).
        If an appointment was scheduled, the appointment dict is returned so the
        orchestrator can trigger the NotificationAgent.
        """
        import json

        messages = [{"role": "system", "content": self.system_prompt}] + conversation_history
        appointment = None

        # Patch tool handler to capture the appointment result
        captured = {}

        def _schedule_and_capture(args):
            result = schedule_appointment(**args)
            captured["appointment"] = result
            return result

        original_handlers = self.tool_handlers.copy()
        self.tool_handlers = {"schedule_appointment": lambda args: _schedule_and_capture(args)}

        response = self._run_loop(messages)

        self.tool_handlers = original_handlers
        appointment = captured.get("appointment")

        return response, appointment
