# Fully Autonomous Agentic Sales Chatbot

An AI-powered sales assistant for a Kia car dealership that handles customer inquiries, provides car information, and books test drives. Available as both a chat interface and an autonomous phone agent that answers and responds to real phone calls.

---

## Features

- **Car Information** — Answers questions about Kia models, features, specs, and pricing using RAG (retrieval-augmented generation) from the official Kia brochure, with Tavily web search for real-time information
- **Test Drive Booking** — Collects customer details conversationally, checks Google Calendar availability, books appointments, and sends confirmation via Gmail with a calendar invite and WhatsApp
- **Appointment Reminders** — Sends WhatsApp reminders and calendar invites to customers before their scheduled test drive
- **Autonomous Phone Agent** — Picks up real phone calls, understands speech, and responds in natural spoken English with no human needed
- **Multi-Agent Orchestration** — Router classifies intent and delegates to specialized agents
- **Dual Mode** — Chat and phone modes use different models and prompts optimized for each interface

---

## Architecture

```
User (Chat UI or Phone Call)
        |
  Orchestrator
        |
  RouterAgent -- classifies intent
        |
  +----------------------------------------------+
  | car_inquiry  -> CarInfoAgent                  |
  |                (RAG + FAISS + Tavily search)  |
  |                                               |
  | schedule_appointment -> BookingAgent          |
  |                (Google Calendar,              |
  |                 Gmail + iCal, WhatsApp)       |
  |                                               |
  | general -> Direct LLM reply                  |
  +----------------------------------------------+
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Chat UI | Chainlit |
| LLM (chat) | Ollama qwen2.5:3b |
| LLM (phone) | Ollama qwen2.5:1.5b |
| RAG / Vector Search | FAISS + sentence-transformers |
| Web Search | Tavily API |
| PDF Ingestion | pdfplumber |
| Phone Calls | Twilio Voice |
| Speech-to-Text | Google Speech Recognition |
| Calendar | Google Calendar API |
| Email | Gmail API + iCal invites |
| WhatsApp | Twilio WhatsApp |

---

## Project Structure

```
src/
    app.py              # Chainlit chat UI
    phone_app.py        # Autonomous phone agent (FastAPI + Twilio)
    orchestrator.py     # Multi-agent orchestrator
    bookingagent.py     # Test drive booking agent
    voice_utils.py      # Speech-to-text and text-to-speech
    config.py           # Configuration and env vars
    ingest.py           # PDF ingestion script
agents/
    base.py             # BaseAgent class
    router.py           # Intent classification
    car_info_agent.py   # Car info and pricing agent
rag/
    indexer.py          # Build FAISS index
    retriever.py        # Vector search
tools/
    car_search.py       # RAG search tool
    price_lookup.py     # Pricing tool
data/
    2026.pdf            # Kia brochure
    prices.json         # Fallback pricing data
    vector_store/       # FAISS index and chunks
.env                    # API keys and config
```

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/Aakash2112/Agentic_Sales_ChatBot.git
cd Agentic_Sales_ChatBot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Install and start Ollama

```bash
# Install Ollama from https://ollama.com
ollama pull qwen2.5:3b
ollama pull qwen2.5:1.5b
```

### 3. Configure environment variables

Create a `.env` file with your credentials:

```
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_PHONE_MODEL=qwen2.5:1.5b

TAVILY_API_KEY=your_tavily_key

TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_FROM=whatsapp:+your_number

BASE_URL=https://your-tunnel-url
```

### 4. Build the FAISS index

```bash
cd src && python ingest.py
```

### 5. Add Google credentials

Place your `credentials.json` (Google OAuth) in `src/`. On first run it will open a browser to authenticate for Google Calendar and Gmail access.

---

## Running

### Chat UI

```bash
cd src
chainlit run app.py
```

### Autonomous Phone Agent

**Terminal 1** — Start the phone server:
```bash
cd src
uvicorn phone_app:app --port 8001
```

**Terminal 2** — Expose locally to Twilio:
```bash
npx localtunnel --port 8001
```

Update `BASE_URL` in `.env` with the tunnel URL and set your Twilio phone number webhook to:
```
https://your-tunnel-url/voice  (POST)
```

Then call your Twilio number and the agent picks up automatically.

---

## Environment Variables

| Variable | Description |
|---|---|
| `OLLAMA_MODEL` | Model for chat mode (default: qwen2.5:3b) |
| `OLLAMA_PHONE_MODEL` | Model for phone mode (default: qwen2.5:1.5b) |
| `OLLAMA_BASE_URL` | Ollama server URL (default: http://localhost:11434/v1) |
| `TAVILY_API_KEY` | Tavily search API key |
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | Twilio WhatsApp sender number |
| `BASE_URL` | Public tunnel URL for phone agent webhooks |
