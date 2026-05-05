import anthropic
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import base64, json, os, pickle, pytz, re

CLAUDE_API_KEY = "YOUR_CLAUDE_API_KEY_HERE"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar"
]
TIMEZONE = "America/Los_Angeles"
LOCATION = "2440 Santa Monica Blvd, Santa Monica, CA 90404"
AVAILABLE_HOURS = [9, 10, 11, 12, 14, 15, 16, 17]
ORGANIZER_EMAIL = "siddharthsaravanan27@gmail.com"

# ============ AUTH ============
def get_services():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if os.path.exists("token.pickle"):
                os.remove("token.pickle")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    gmail = build("gmail", "v1", credentials=creds)
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
    for fmt in ["%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%B %d %Y"]:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    return datetime.now() + timedelta(days=1)

# ============ CALENDAR - GET FREE SLOTS ============
def get_free_slots(calendar, date_str, days_to_check=3):
    tz = pytz.timezone(TIMEZONE)
    free_slots = []
    start_date = parse_date(date_str)

    for day_offset in range(days_to_check):
        check_date = start_date + timedelta(days=day_offset)
        if check_date.weekday() == 6:
            continue

        day_start = tz.localize(check_date.replace(hour=0, minute=0, second=0))
        day_end = tz.localize(check_date.replace(hour=23, minute=59, second=59))

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
    tz = pytz.timezone(TIMEZONE)
    start_date = parse_date(date_str)
    hour = normalize_time(time_str)

    start_dt = tz.localize(start_date.replace(hour=hour, minute=0, second=0))
    end_dt = start_dt + timedelta(hours=1)

    event = {
        "summary": f"Test Drive — Kia {model} ({name})",
        "location": LOCATION,
        "description": f"Customer: {name}\nEmail: {email}\nCar: Kia {model}",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": TIMEZONE},
        "attendees": [{"email": email}],
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},
                {"method": "popup", "minutes": 30}
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

# ============ EMAIL WITH ICAL ============
def send_confirmation_email(gmail, to_email, name, model, date, time_str):
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"✅ Test Drive Confirmed — Kia {model}"
    msg["From"] = "me"
    msg["To"] = to_email

    html = f"""
    <html><body>
    <h2>Hi {name}! Your Test Drive is Confirmed 🚗</h2>
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
    tz = pytz.timezone(TIMEZONE)
    start_date = parse_date(date)
    hour = normalize_time(time_str)
    start_dt = tz.localize(start_date.replace(hour=hour, minute=0, second=0))
    end_dt = start_dt + timedelta(hours=1)

    fmt = "%Y%m%dT%H%M%S"
    start_utc = start_dt.astimezone(pytz.utc).strftime(fmt) + "Z"
    end_utc = end_dt.astimezone(pytz.utc).strftime(fmt) + "Z"
    now_utc = datetime.utcnow().strftime(fmt) + "Z"

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
    print(f"  📧 Email + calendar invite sent to {to_email}")

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
        print(f"\n🎉 Booking Confirmed!")
        print(f"   👤 {data['name']} | 🚗 Kia {data['model']}")
        print(f"   📅 {data['date']} at {data['time']}")
        print(f"   📧 Confirmation sent to {data['email']}")
        return True, None
    else:
        suggestions = free_slots[:3]
        suggestion_text = "\n".join([f"  • {s['date']} at {s['time']}" for s in suggestions])
        print(f"  ❌ {data['date']} at {data['time']} is not available!")
        print(f"  📅 Next available:\n{suggestion_text}\n")
        return False, suggestions

# ============ BOOKING AGENT ============
def booking_agent():
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    gmail, calendar = get_services()
    conversation = []
    booking_done = False

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%B %d, %Y")

    system_prompt = f"""You are a friendly Kia car booking agent for Kia Santa Monica.

Today is {datetime.now().strftime("%B %d, %Y")}.
Tomorrow is {tomorrow}.
Available slots: 9am, 10am, 11am, 12pm, 2pm, 3pm, 4pm, 5pm (Mon-Sat only)
Location: {LOCATION}

Collect these details one at a time:
- Customer name
- Car model (from: K4, K5, Seltos, Sportage, Sorento, Niro, EV6, EV9, Telluride)
- Preferred date (suggest {tomorrow} as default)
- Preferred time
- Customer email

IMPORTANT RULES:
- If customer already mentioned car model DO NOT ask again
- If customer wants to change email update ONLY the email in JSON
- NEVER say booking is confirmed — system handles that
- When all details ready output JSON first then stop

When ALL details collected output ONLY this JSON:
{{
  "name": "...",
  "model": "...",
  "date": "...",
  "time": "...",
  "email": "...",
  "ready": true
}}"""

    print("🚗 Kia Santa Monica Booking Agent")
    print("=" * 40)
    print("Type 'quit' to exit\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "quit":
            break

        conversation.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system=system_prompt,
            messages=conversation
        )

        reply = response.content[0].text
        conversation.append({"role": "assistant", "content": reply})

        data = extract_json(reply)

        if data and data.get("ready") and not booking_done:
            success, suggestions = complete_booking(gmail, calendar, data)

            if success:
                booking_done = True
                break
            else:
                alt_text = "\n".join([f"{s['date']} at {s['time']}" for s in suggestions])
                conversation.append({
                    "role": "user",
                    "content": f"System: That slot is taken. Tell customer only these slots are available: {alt_text}"
                })
                response2 = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=500,
                    system=system_prompt,
                    messages=conversation
                )
                reply2 = response2.content[0].text
                conversation.append({"role": "assistant", "content": reply2})
                print(f"\nAgent: {reply2}\n")
        else:
            display_reply = re.sub(r'\{[^{}]*"ready"[^{}]*\}', '', reply, flags=re.DOTALL).strip()
            if display_reply:
                print(f"\nAgent: {display_reply}\n")

booking_agent()