"""
Phone agent for Kia Santa Monica.

Flow:
  Customer calls Twilio number
      -> POST /voice        (greet + start recording)
      -> POST /transcribe   (Whisper STT -> Orchestrator -> gTTS -> play back -> record again)
      -> POST /status       (cleanup on call end)

Run:
  uvicorn phone_app:app --host 0.0.0.0 --port 8001

Expose publicly for Twilio:
  ngrok http 8001
  Then set Twilio webhook to: https://<ngrok-url>/voice
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from fastapi import FastAPI, Form
from fastapi.responses import Response, FileResponse
import uvicorn

from orchestrator import handle
from voice_utils import transcribe, synthesize, AUDIO_DIR
import re
import html


def _clean_for_speech(text: str) -> str:
    """Strip markdown so Twilio <Say> reads cleanly."""
    # Remove markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove bold/italic
    text = re.sub(r'\*{1,2}([^\*]+)\*{1,2}', r'\1', text)
    # Remove headers
    text = re.sub(r'#{1,6}\s*', '', text)
    # Remove bullet points
    text = re.sub(r'^\s*[-*•]\s+', '', text, flags=re.MULTILINE)
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove extra whitespace
    text = re.sub(r'\n+', ' ', text).strip()
    return text

app = FastAPI()

# CallSid -> conversation_history
sessions: dict[str, list] = {}


@app.on_event("startup")
async def warmup():
    """Pre-load FAISS index and embedding model so first call is fast."""
    print("[Warmup] Loading FAISS index and embedding model...")
    try:
        from rag.retriever import _load
        _load()
        print("[Warmup] Done.")
    except Exception as e:
        print(f"[Warmup] Failed: {e}")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8001")

HANGUP_PHRASES = {"bye", "goodbye", "that's all", "no thanks", "hang up", "end call"}


def _twiml(*, say: str = None, play_url: str = None, record: bool = True, hangup: bool = False) -> Response:
    transcribe_url = f"{BASE_URL}/transcribe"
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n'
    if say:
        safe = say.replace("&", "and").replace("<", "").replace(">", "")
        xml += f'  <Say voice="alice">{safe}</Say>\n'
    if play_url:
        xml += f'  <Play>{play_url}</Play>\n'
    if record:
        xml += (
            f'  <Record action="{transcribe_url}" maxLength="10" '
            f'playBeep="false" trim="trim-silence" timeout="2"/>\n'
        )
    if hangup:
        xml += '  <Hangup/>\n'
    xml += '</Response>'
    return Response(content=xml, media_type="application/xml")


@app.post("/voice")
async def voice(CallSid: str = Form(...)):
    """Incoming call — greet and start listening."""
    sessions[CallSid] = []
    print(f"[Call {CallSid}] Started")
    return _twiml(
        say="Welcome to Kia Santa Monica! I'm your virtual assistant. How can I help you today?",
    )


@app.post("/transcribe")
async def transcribe_handler(
    CallSid: str = Form(...),
    RecordingUrl: str = Form(None),
    RecordingSid: str = Form(None),
):
    """Receive recording, transcribe, get agent response, play back."""

    if not RecordingUrl or not RecordingSid:
        return _twiml(say="Sorry, I didn't catch that. Could you please repeat?")

    # Transcribe with Whisper
    try:
        user_text = transcribe(RecordingUrl, RecordingSid)
    except Exception as e:
        print(f"[Whisper error] {e}")
        return _twiml(say="Sorry, I had trouble hearing you. Could you repeat that?")

    if not user_text:
        return _twiml(say="I didn't hear anything. Are you still there?")

    print(f"[Call {CallSid}] User: {user_text}")

    # Check for hangup intent
    if any(phrase in user_text.lower() for phrase in HANGUP_PHRASES):
        sessions.pop(CallSid, None)
        return _twiml(
            say="Thank you for calling Kia Santa Monica. Have a great day!",
            record=False,
            hangup=True,
        )

    # Run orchestrator and respond
    history = sessions.get(CallSid, [])
    history.append({"role": "user", "content": user_text})

    try:
        agent_response = handle(history, mode="phone")
        print(f"[Call {CallSid}] Agent: {agent_response}")
    except Exception as e:
        print(f"[Orchestrator error] {e}")
        agent_response = "I'm having a technical issue. Please try again in a moment."

    history.append({"role": "assistant", "content": agent_response})
    sessions[CallSid] = history

    return _twiml(say=_clean_for_speech(agent_response))


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated TTS audio files to Twilio."""
    filepath = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(filepath):
        return Response(status_code=404)
    return FileResponse(filepath, media_type="audio/mpeg")


@app.post("/status")
async def call_status(CallSid: str = Form(...), CallStatus: str = Form(...)):
    """Clean up session when call ends."""
    if CallStatus in ("completed", "failed", "busy", "no-answer"):
        sessions.pop(CallSid, None)
        print(f"[Call {CallSid}] Ended — status: {CallStatus}")
    return Response(status_code=200)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
