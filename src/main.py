"""
CLI fallback for the Kia Sales ChatBot.
For the UI, run: chainlit run app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))                    # src/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))   # project root

from orchestrator import handle


def main():
    print("=" * 52)
    print("   Kia Sales Assistant (CLI Mode)")
    print("   For the full UI run: chainlit run app.py")
    print("   Type 'quit' to exit.")
    print("=" * 52)
    print()

    history = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Assistant: Thank you for visiting Kia. Have a great day!")
            break

        history.append({"role": "user", "content": user_input})
        response = handle(history)
        print(f"\nAssistant: {response}\n")
        history.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
