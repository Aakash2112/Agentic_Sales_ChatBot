import json
import os
from datetime import datetime

APPOINTMENTS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "appointments.json")


def schedule_appointment(
    customer_name: str,
    email: str,
    phone: str,
    car_model: str,
    preferred_date: str,
    preferred_time: str,
) -> dict:
    """
    Tool: Schedule a test drive / dealership appointment.
    Saves appointment and returns confirmation details.
    """
    appointment = {
        "id": f"APT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "customer_name": customer_name,
        "email": email,
        "phone": phone,
        "car_model": car_model,
        "preferred_date": preferred_date,
        "preferred_time": preferred_time,
        "booked_at": datetime.now().isoformat(),
        "status": "confirmed",
    }

    # Load existing appointments
    appointments = []
    if os.path.exists(APPOINTMENTS_FILE):
        with open(APPOINTMENTS_FILE, "r") as f:
            appointments = json.load(f)

    appointments.append(appointment)

    os.makedirs(os.path.dirname(APPOINTMENTS_FILE), exist_ok=True)
    with open(APPOINTMENTS_FILE, "w") as f:
        json.dump(appointments, f, indent=2)

    return appointment
