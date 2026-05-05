"""
Kia Agentic Sales ChatBot — Chainlit UI
Run: chainlit run app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))                    # src/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))   # project root

import asyncio
import chainlit as cl
from orchestrator import handle

WELCOME_MESSAGE = """**Welcome to Kia Sales Assistant!**

I can help you with:
- Questions about Kia models, features, and pricing
- Scheduling a test drive or dealership visit

How can I assist you today?
"""

THINKING_MESSAGES = [
    "Looking that up for you...",
    "On it...",
    "Let me check that...",
    "Pulling that together...",
    "Give me a moment...",
]

_thinking_index = 0


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("history", [])
    await cl.Message(content=WELCOME_MESSAGE, author="Kia Assistant").send()


@cl.on_message
async def on_message(message: cl.Message):
    global _thinking_index

    history: list[dict] = cl.user_session.get("history", [])
    history.append({"role": "user", "content": message.content})

    # Show a thinking indicator while the agent works
    thinking_text = THINKING_MESSAGES[_thinking_index % len(THINKING_MESSAGES)]
    _thinking_index += 1

    async with cl.Step(name=thinking_text, show_input=False) as step:
        response = await asyncio.to_thread(handle, history)
        step.output = ""

    await cl.Message(content=response, author="Kia Assistant").send()

    history.append({"role": "assistant", "content": response})
    cl.user_session.set("history", history)
