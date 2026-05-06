from openai import OpenAI
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from twilio.rest import Client as TwilioClient
from dotenv import load_dotenv
import base64, json, os, pickle, pytz, re

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

# ============ CREDENTIALS ============

APPOINTMENTS_FILE = "appointments.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar"
]
TIMEZONE        = "America/Los_Angeles"
LOCATION        = "2440 Santa Monica Blvd, Santa Monica, CA 90404"
AVAILABLE_HOURS = [9, 10, 11, 12, 14, 15, 16, 17]

# ============ DATE HELPERS ============
def get_next_7_days():
    """Returns next 7 days with correct day names for the agent"""
    days = []
    for i in range(1, 8):
        d = datetime.now() + timedelta(days=i)
        days.append(d.strftime("%A, %B %d, %Y"))  # e.g. "Thursday, May 7, 2026"
    return days

def get_today_str():
    return datetime.now().strftime("%A, %B %d, %Y")

def get_tomorrow_str():
    return (datetime.now() + timedelta(days=1)).strftime("%A, %B %d, %Y")

# ============ APPOINTMENTS JSON ============
def load_appointments():
    if os.path.exists(APPOINTMENTS_FILE):
        with open(APPOINTMENTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_appointment(data, status="confirmed"):
    appointments = load_appointments()
    appointment = {
        "id": f"KIA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "status": status,
        "name": data.get("name"),
        "model": data.get("model"),
        "date": data.get("date"),
        "time": data.get("time"),
        "email": data.get("email"),
        "phone": data.get("phone", "N/A"),
        "location": LOCATION,
        "booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    appointments.append(appointment)
    with open(APPOINTMENTS_FILE, "w") as f:
        json.dump(appointments, f, indent=2)
    print(f"  💾 Appointment saved to {APPOINTMENTS_FILE} (ID: {appointment['id']})")
    return appointment["id"]

def update_appointment_status(appointment_id, new_status, new_data=None):
    appointments = load_appointments()
    for apt in appointments:
        if apt["id"] == appointment_id:
            apt["status"] = new_status
            apt["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if new_data:
                apt.update(new_data)
            break
    with open(APPOINTMENTS_FILE, "w") as f:
        json.dump(appointments, f, indent=2)
    print(f"  💾 Appointment {appointment_id} updated to '{new_status}'")

# ============ AUTH ============
def get_services():
    creds = None
    _src_dir = os.path.dirname(__file__)
    _token_path = os.path.join(_src_dir, "token.pickle")
    _creds_path = os.path.join(_src_dir, "credentials.json")
    if os.path.exists(_token_path):
        with open(_token_path, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if os.path.exists(_token_path):
                os.remove(_token_path)
            flow = InstalledAppFlow.from_client_secrets_file(_creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(_token_path, "wb") as token:
            pickle.dump(creds, token)
    gmail    = build("gmail", "v1", credentials=creds)
    calendar = build("calendar", "v3", credentials=creds)
    return gmail, calendar

# ============ EXTRACT JSON ============
def extract_json(text):
    try:
        match = re.search(r'\{[^{}]*"ready"\s*:\s*true[^{}]*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return None

# ============ TIME NORMALIZER ============
def normalize_time(time_str):
    time_str = time_str.upper().strip().replace(".", "").replace(" ", "")
    for fmt in ["%I:%M%p", "%I%p", "%H:%M", "%H"]:
        try:
            return datetime.strptime(time_str, fmt).hour
        except:
            continue
    mapping = {
        "9AM": 9,  "9": 9,
        "10AM": 10, "10": 10,
        "11AM": 11, "11": 11,
        "12PM": 12, "12": 12,
        "1PM": 13,  "1": 13,
        "2PM": 14,  "2": 14,
        "3PM": 15,  "3": 15,
        "4PM": 16,  "4": 16,
        "5PM": 17,  "5": 17,
    }
    return mapping.get(time_str, -1)

# ============ PARSE DATE ============
def parse_date(date_str):
    # Remove ordinal suffixes and day names
    clean = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
    clean = re.sub(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*', '', clean)
    for fmt in ["%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%B %d %Y", "%B %d,%Y"]:
        try:
            return datetime.strptime(clean.strip(), fmt)
        except:
            continue
    return datetime.now() + timedelta(days=1)

# ============ CALENDAR - GET FREE SLOTS ============
def get_free_slots(calendar, date_str, days_to_check=3):
    tz         = pytz.timezone(TIMEZONE)
    free_slots = []
    start_date = parse_date(date_str)

    for day_offset in range(days_to_check):
        check_date = start_date + timedelta(days=day_offset)
        if check_date.weekday() == 6:  # Skip Sundays
            continue

        day_start = tz.localize(check_date.replace(hour=0,  minute=0,  second=0))
        day_end   = tz.localize(check_date.replace(hour=23, minute=59, second=59))

        events_result = calendar.events().list(
            calendarId="primary",
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        busy_hours = []
        for event in events_result.get("items", []):
            start = event["start"].get("dateTime", "")
            if start:
                busy_hours.append(datetime.fromisoformat(start).hour)

        day_slots = []
        for hour in AVAILABLE_HOURS:
            if hour not in busy_hours:
                time_str = datetime.strptime(f"{hour}:00", "%H:%M").strftime("%I:%M %p").lstrip("0")
                day_slots.append({
                    "date": check_date.strftime("%B %d, %Y"),
                    "time": time_str,
                    "hour": hour,
                })

        free_slots.extend(day_slots)
        if day_offset == 0 and day_slots:
            return free_slots

    return free_slots

# ============ CALENDAR - BOOK ============
def book_appointment(calendar, name, model, date_str, time_str, email):
    tz         = pytz.timezone(TIMEZONE)
    start_date = parse_date(date_str)
    hour       = normalize_time(time_str)

    start_dt = tz.localize(start_date.replace(hour=hour, minute=0, second=0))
    end_dt   = start_dt + timedelta(hours=1)

    event = {
        "summary": f"Test Drive — Kia {model} ({name})",
        "location": LOCATION,
        "description": f"Customer: {name}\nEmail: {email}\nCar: Kia {model}",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": TIMEZONE},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": TIMEZONE},
        "attendees": [{"email": email}],
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email",  "minutes": 24 * 60},
                {"method": "popup",  "minutes": 30}
            ]
        }
    }
    created = calendar.events().insert(
        calendarId="primary",
        body=event,
        sendUpdates="all"
    ).execute()
    print(f"  📅 Calendar event created!")
    return created

# ============ WHATSAPP ============
def send_whatsapp(to_number, name, model, date, time_str):
    try:
        client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(
            from_=TWILIO_FROM,
            to=f"whatsapp:{to_number}",
            body=f"""🚗 *Kia Santa Monica — Test Drive Confirmed!*

Hi {name}! Your booking is confirmed ✅

🚗 *Car:* Kia {model}
📅 *Date:* {date}
⏰ *Time:* {time_str}
📍 *Location:* {LOCATION}

Please arrive 10 minutes early.
See you soon! — Kia Santa Monica Team 🏎️"""
        )
        print(f"  💬 WhatsApp sent to {to_number}")
        return True
    except Exception as e:
        print(f"  ⚠️ WhatsApp failed: {e}")
        return False

def send_whatsapp_reschedule(to_number, name, old_date, old_time, new_date, new_time, model):
    try:
        client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(
            from_=TWILIO_FROM,
            to=f"whatsapp:{to_number}",
            body=f"""🔄 *Kia Santa Monica — Test Drive Rescheduled!*

Hi {name}! Your test drive has been rescheduled ✅

🚗 *Car:* Kia {model}
~~Old:~~ {old_date} at {old_time}
✅ *New:* {new_date} at {new_time}
📍 *Location:* {LOCATION}

Please arrive 10 minutes early.
See you soon! — Kia Santa Monica Team 🏎️"""
        )
        print(f"  💬 Reschedule WhatsApp sent to {to_number}")
        return True
    except Exception as e:
        print(f"  ⚠️ WhatsApp reschedule failed: {e}")
        return False

# ============ EMAIL WITH ICAL ============
def send_confirmation_email(gmail, to_email, name, model, date, time_str, is_reschedule=False):
    subject = f"{'🔄 Test Drive Rescheduled' if is_reschedule else '✅ Test Drive Confirmed'} — Kia {model}"
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = "me"
    msg["To"]      = to_email

    heading = "Your Test Drive has been Rescheduled 🔄" if is_reschedule else "Your Test Drive is Confirmed 🚗"

    html = f"""
    <html><body>
    <h2>Hi {name}! {heading}</h2>
    <hr>
    <p><b>🚗 Car:</b> Kia {model}</p>
    <p><b>📅 Date:</b> {date}</p>
    <p><b>⏰ Time:</b> {time_str}</p>
    <p><b>📍 Location:</b> {LOCATION}</p>
    <br>
    <p>Your calendar invite is attached — tap to add it!</p>
    <p>Please arrive 10 minutes early.</p>
    <hr>
    <p><b>Kia Santa Monica Team</b></p>
    </body></html>
    """
    msg.attach(MIMEText(html, "html"))

    # Build iCal
    tz         = pytz.timezone(TIMEZONE)
    start_date = parse_date(date)
    hour       = normalize_time(time_str)
    start_dt   = tz.localize(start_date.replace(hour=hour, minute=0, second=0))
    end_dt     = start_dt + timedelta(hours=1)

    fmt       = "%Y%m%dT%H%M%S"
    start_utc = start_dt.astimezone(pytz.utc).strftime(fmt) + "Z"
    end_utc   = end_dt.astimezone(pytz.utc).strftime(fmt) + "Z"
    now_utc   = datetime.utcnow().strftime(fmt) + "Z"

    ical = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Kia Santa Monica//EN
METHOD:REQUEST
BEGIN:VEVENT
UID:{now_utc}-kia-booking@santamonica
DTSTAMP:{now_utc}
DTSTART:{start_utc}
DTEND:{end_utc}
SUMMARY:Test Drive — Kia {model}
DESCRIPTION:Customer: {name}\\nCar: Kia {model}\\nEmail: {to_email}
LOCATION:{LOCATION}
ORGANIZER:mailto:{ORGANIZER_EMAIL}
ATTENDEE;RSVP=TRUE:mailto:{to_email}
STATUS:CONFIRMED
BEGIN:VALARM
TRIGGER:-PT30M
ACTION:DISPLAY
DESCRIPTION:Test Drive Reminder
END:VALARM
END:VEVENT
END:VCALENDAR"""

    ical_attachment = MIMEBase("text", "calendar", method="REQUEST", charset="UTF-8")
    ical_attachment.set_payload(ical.encode("utf-8"))
    encoders.encode_base64(ical_attachment)
    ical_attachment.add_header("Content-Disposition", "attachment", filename="invite.ics")
    msg.attach(ical_attachment)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    gmail.users().messages().send(userId="me", body={"raw": raw}).execute()
    action = "Reschedule" if is_reschedule else "Confirmation"
    print(f"  📧 {action} email + calendar invite sent to {to_email}")

# ============ COMPLETE BOOKING ============
def complete_booking(gmail, calendar, data):
    print("\n⏳ Checking salesperson availability...\n")
    free_slots = get_free_slots(calendar, data["date"])

    requested_hour = normalize_time(data["time"])
    print(f"  🕐 Requested hour: {requested_hour}")
    print(f"  📅 Free slot hours: {[s['hour'] for s in free_slots]}")

    slot_available = any(s["hour"] == requested_hour for s in free_slots)

    if slot_available:
        print(f"  ✅ {data['date']} at {data['time']} is available!\n")
        book_appointment(calendar, data["name"], data["model"], data["date"], data["time"], data["email"])
        send_confirmation_email(gmail, data["email"], data["name"], data["model"], data["date"], data["time"])

        # Send WhatsApp if phone provided
        if data.get("phone"):
            send_whatsapp(data["phone"], data["name"], data["model"], data["date"], data["time"])

        # Save to JSON
        apt_id = save_appointment(data, status="confirmed")

        print(f"\n🎉 Booking Confirmed!")
        print(f"   👤 {data['name']} | 🚗 Kia {data['model']}")
        print(f"   📅 {data['date']} at {data['time']}")
        print(f"   📧 Confirmation sent to {data['email']}")
        if data.get("phone"):
            print(f"   💬 WhatsApp sent to {data['phone']}")
        print(f"   💾 Appointment ID: {apt_id}")
        return True, None, apt_id
    else:
        suggestions     = free_slots[:3]
        suggestion_text = "\n".join([f"  • {s['date']} at {s['time']}" for s in suggestions])
        print(f"  ❌ {data['date']} at {data['time']} is not available!")
        print(f"  📅 Next available:\n{suggestion_text}\n")
        return False, suggestions, None

# ============ RESCHEDULE ============
def reschedule_booking(gmail, calendar, data, old_data, appointment_id):
    print("\n⏳ Checking availability for new slot...\n")
    free_slots = get_free_slots(calendar, data["date"])

    requested_hour = normalize_time(data["time"])
    slot_available = any(s["hour"] == requested_hour for s in free_slots)

    if slot_available:
        print(f"  ✅ New slot {data['date']} at {data['time']} is available!\n")
        book_appointment(calendar, data["name"], data["model"], data["date"], data["time"], data["email"])
        send_confirmation_email(gmail, data["email"], data["name"], data["model"], data["date"], data["time"], is_reschedule=True)

        # Send reschedule WhatsApp
        if data.get("phone"):
            send_whatsapp_reschedule(
                data["phone"], data["name"],
                old_data["date"], old_data["time"],
                data["date"], data["time"],
                data["model"]
            )

        # Update JSON
        update_appointment_status(appointment_id, "rescheduled", {
            "date": data["date"],
            "time": data["time"]
        })

        print(f"\n🔄 Rescheduled Successfully!")
        print(f"   👤 {data['name']} | 🚗 Kia {data['model']}")
        print(f"   📅 New: {data['date']} at {data['time']}")
        return True, None
    else:
        suggestions     = free_slots[:3]
        suggestion_text = "\n".join([f"  • {s['date']} at {s['time']}" for s in suggestions])
        print(f"  ❌ New slot not available!")
        print(f"  📅 Try:\n{suggestion_text}\n")
        return False, suggestions

# ============ SESSION STATE ============
_booking_done = False
_appointment_id = None
_last_booking_data = None
_gmail = None
_calendar = None


def _get_cached_services():
    global _gmail, _calendar
    if _gmail is None or _calendar is None:
        _gmail, _calendar = get_services()
    return _gmail, _calendar


def _build_system_prompt():
    today_str    = get_today_str()
    tomorrow_str = get_tomorrow_str()
    next_7_days  = get_next_7_days()
    next_7_str   = "\n".join([f"- {d}" for d in next_7_days])

    return f"""You are a friendly Kia car booking agent for Kia Santa Monica.

Today is {today_str}.
Tomorrow is {tomorrow_str}.

Upcoming days (use EXACT day names from this list — NEVER guess):
{next_7_str}

Available time slots: 9am, 10am, 11am, 12pm, 2pm, 3pm, 4pm, 5pm (Mon-Sat only — closed Sundays)
Location: {LOCATION}

Collect these details one at a time:
- Customer name
- Car model (from: K4, K5, Seltos, Sportage, Sorento, Niro, EV6, EV9, Telluride)
- Preferred date (suggest {tomorrow_str} as default)
- Preferred time
- Customer email
- WhatsApp number with country code (e.g. +1 for USA)

IMPORTANT RULES:
- If customer already mentioned car model DO NOT ask again
- NEVER calculate or assume day names yourself — use ONLY the list above
- If customer wants to reschedule say "Sure! What new date and time works for you?"
- NEVER say booking is confirmed — system handles that
- When all details ready output JSON then stop

When ALL details collected output ONLY this JSON:
{{
  "name": "...",
  "model": "...",
  "date": "...",
  "time": "...",
  "email": "...",
  "phone": "...",
  "ready": true
}}

For rescheduling, collect new date and time then output:
{{
  "name": "...",
  "model": "...",
  "date": "...",
  "time": "...",
  "email": "...",
  "phone": "...",
  "reschedule": true,
  "ready": true
}}"""


# ============ ORCHESTRATOR ENTRY POINT ============
PHONE_ADDENDUM = (
    "\n\nIMPORTANT: You are responding on a live phone call. "
    "You MUST follow these rules strictly:\n"
    "- Speak in plain natural English sentences only\n"
    "- NEVER use markdown, asterisks, dashes, bullet points, or numbered lists\n"
    "- NEVER include URLs or special characters\n"
    "- Ask for one piece of information at a time\n"
    "- Keep each response to 1 to 2 sentences"
)


def run(conversation_history: list[dict], mode: str = "chat") -> str:
    """
    Called by orchestrator for schedule_appointment intent.
    Accepts full conversation history, returns assistant response string.
    """
    global _booking_done, _appointment_id, _last_booking_data

    from config import OLLAMA_BASE_URL, LLM_MODEL, PHONE_LLM_MODEL
    client = OpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL)
    model = PHONE_LLM_MODEL if mode == "phone" else LLM_MODEL
    gmail, calendar = _get_cached_services()
    system_prompt = _build_system_prompt() + (PHONE_ADDENDUM if mode == "phone" else "")

    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
    )

    reply = response.choices[0].message.content
    data  = extract_json(reply)

    if data and data.get("ready"):

        # ===== RESCHEDULE =====
        if data.get("reschedule") and _booking_done and _last_booking_data and _appointment_id:
            success, suggestions = reschedule_booking(gmail, calendar, data, _last_booking_data, _appointment_id)
            if success:
                _last_booking_data = data
                return f"Your test drive has been rescheduled to {data['date']} at {data['time']}! A new confirmation email and WhatsApp has been sent."
            else:
                alt_text = "\n".join([f"{s['date']} at {s['time']}" for s in suggestions])
                r2 = client.chat.completions.create(
                    model=model,
                    messages=messages + [
                        {"role": "assistant", "content": reply},
                        {"role": "user", "content": f"System: New slot taken. Tell customer these are available: {alt_text}"},
                    ],
                    temperature=0.3,
                )
                return r2.choices[0].message.content

        # ===== NEW BOOKING =====
        elif not _booking_done:
            success, suggestions, apt_id = complete_booking(gmail, calendar, data)
            if success:
                _booking_done      = True
                _appointment_id    = apt_id
                _last_booking_data = data
                return f"Your test drive is all set! Confirmation sent to {data['email']}. Let me know if you need to reschedule."
            else:
                alt_text = "\n".join([f"{s['date']} at {s['time']}" for s in suggestions])
                r2 = client.chat.completions.create(
                    model=model,
                    messages=messages + [
                        {"role": "assistant", "content": reply},
                        {"role": "user", "content": f"System: Slot taken. Tell customer only these are available: {alt_text}"},
                    ],
                    temperature=0.3,
                )
                return r2.choices[0].message.content

    # Normal conversational reply — strip any leaked JSON
    display_reply = re.sub(r'\{[^{}]*"ready"[^{}]*\}', '', reply, flags=re.DOTALL).strip()
    return display_reply if display_reply else reply