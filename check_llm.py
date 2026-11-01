"""Run: python check_llm.py   Shows exactly why the language model works or fails."""
from dotenv import load_dotenv
load_dotenv()
from core import agent

info = agent.diagnose()
for k, v in info.items():
    print(f"{k}: {v}")
print("\nRESULT:", "language model works" if info["ok"] else "language model FAILED, read the error line above")
