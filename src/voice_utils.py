"""
STT: Google Speech Recognition via SpeechRecognition library (free)
TTS: gTTS via Google (free)
"""

import os
import ssl
import uuid
import requests
import urllib3
import speech_recognition as sr
from gtts import gTTS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)

_recognizer = sr.Recognizer()


def transcribe(recording_url: str, recording_sid: str) -> str:
    """Download Twilio recording as WAV and transcribe with Google Speech Recognition."""
    wav_path = os.path.join(AUDIO_DIR, f"{recording_sid}.wav")

    # Download directly as WAV — skips MP3→WAV conversion step
    response = requests.get(
        recording_url + ".wav",
        auth=(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")),
        timeout=15,
        verify=False,
    )
    response.raise_for_status()

    with open(wav_path, "wb") as f:
        f.write(response.content)

    try:
        with sr.AudioFile(wav_path) as source:
            audio = _recognizer.record(source)

        text = _recognizer.recognize_google(audio)
        print(f"[STT] Transcribed: {text}")
        return text
    except sr.UnknownValueError:
        print("[STT] Could not understand audio")
        return ""
    except Exception as e:
        print(f"[STT error] {e}")
        raise
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


def synthesize(text: str) -> str:
    """Convert text to MP3 using gTTS. Returns the filename (not full path)."""
    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(filepath)
    print(f"[gTTS] Saved: {filename}")
    return filename
