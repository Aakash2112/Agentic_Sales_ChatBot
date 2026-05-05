"""
Kia Agentic Sales ChatBot — Chainlit UI
Run: chainlit run src/app.py
"""

import sys
import os

# Project root (contains agents/, tools/, rag/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# src/ (contains orchestrator.py, config.py)
_SRC = os.path.dirname(os.path.abspath(__file__))

for _p in (_PROJECT_ROOT, _SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import asyncio
import chainlit as cl
from orchestrator import handle

WELCOME_MESSAGE = """👋 **Welcome to Kia Sales Assistant!**

I can help you with:
- 🚗 Questions about Kia models, features, and pricing
- 📅 Scheduling a test drive or dealership visit

How can I assist you today?
"""

AGENT_ICONS = {
    "Router":              "🔀",
    "CarInfoAgent":        "🚗",
    "AppointmentAgent":    "📅",
    "NotificationAgent":   "📨",
    "GeneralAgent":        "💬",
}


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("history", [])
    await cl.Message(content=WELCOME_MESSAGE, author="Kia Assistant").send()


@cl.on_message
async def on_message(message: cl.Message):
    history: list[dict] = cl.user_session.get("history", [])
    history.append({"role": "user", "content": message.content})

    # Collect step updates from the orchestrator
    step_log: list[tuple[str, str]] = []

    def step_callback(agent_name: str, detail: str = ""):
        step_log.append((agent_name, detail))

    # Run the blocking orchestrator in a thread so we don't block the event loop
    response = await asyncio.to_thread(handle, history, step_callback)

    # Show agent steps as collapsible elements
    if step_log:
        steps_text = "\n".join(
            f"{AGENT_ICONS.get(name, '⚙️')} **{name}**" + (f" — {detail}" if detail else "")
            for name, detail in step_log
        )
        await cl.Message(
            content=steps_text,
            author="Agent Pipeline",
            indent=1,
        ).send()

    # Send the final response
    await cl.Message(content=response, author="Kia Assistant").send()

    history.append({"role": "assistant", "content": response})
    cl.user_session.set("history", history)
