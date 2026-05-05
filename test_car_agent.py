"""
Quick test for BaseAgent + CarInfoAgent.
Run: python3 test_car_agent.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.dirname(__file__))

from agents.car_info_agent import CarInfoAgent

agent = CarInfoAgent()

questions = [
    "Tell me about the Kia EV6?",
    "How much does the Kia Telluride cost?",
]

for q in questions:
    print(f"\nQ: {q}")
    print("-" * 50)
    history = [{"role": "user", "content": q}]
    response = agent.run(history)
    print(f"A: {response}")
    print()
