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

WELCOME_MESSAGE = """\
## Welcome to Kia Sales Assistant

I'm here to help you find your perfect Kia. Here's what I can do:

| | |
|---|---|
| **Explore Models** | Compare trims, specs, and features across the Kia lineup |
| **Get Pricing** | Instant MSRP and package pricing for any model |
| **Book a Visit** | Schedule a test drive or dealership appointment |

Use the suggestions below or just type your question to get started.
"""

STARTERS = [
    cl.Starter(
        label="Compare Kia models",
        message="What are the differences between the Kia Telluride, Sorento, and Sportage?",
        icon="/public/icons/car.svg",
    ),
    cl.Starter(
        label="Get pricing",
        message="What is the price of the 2025 Kia EV6?",
        icon="/public/icons/price.svg",
    ),
    cl.Starter(
        label="Schedule a test drive",
        message="I'd like to schedule a test drive for the Kia Telluride.",
        icon="/public/icons/calendar.svg",
    ),
    cl.Starter(
        label="Electric vehicles",
        message="Tell me about Kia's electric vehicle lineup.",
        icon="/public/icons/ev.svg",
    ),
]


@cl.set_starters
async def set_starters():
    return STARTERS


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("history", [])
    await cl.Message(content=WELCOME_MESSAGE, author="Kia Assistant").send()


@cl.on_message
async def on_message(message: cl.Message):
    history: list[dict] = cl.user_session.get("history", [])
    history.append({"role": "user", "content": message.content})

    async with cl.Step(name="Kia Assistant", show_input=False) as step:
        step.output = "Looking that up for you..."
        response = await asyncio.to_thread(handle, history)
        step.output = response

    await cl.Message(content=response, author="Kia Assistant").send()

    history.append({"role": "assistant", "content": response})
    cl.user_session.set("history", history)
