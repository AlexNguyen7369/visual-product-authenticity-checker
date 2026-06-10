"""M11 — First Gemini call (text only).

Goal: the request/response lifecycle and where latency lives; secrets from the environment.
Learn: load GEMINI_API_KEY from .env (never in code/git); a network call BLOCKS your thread;
       know what auth errors / timeouts / 429 rate limits look like.
Maps to: the VisionClient wrapper; Step 0.3; every Gemini call in Phases 2-4.

Setup: create a .env file at the repo root containing:  GEMINI_API_KEY=your_key_here
Get a free key at https://aistudio.google.com . See ../src/notes/roadmap.md (M11).
"""
import os

from dotenv import load_dotenv
from google import genai


def get_api_key() -> str:
    """Load the key, failing FAST with a clear message if it's missing."""
    load_dotenv()  # reads .env from cwd / parents into os.environ
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set — create a .env at the repo root.")
    return key


def ask(prompt: str) -> str:
    """Send a text prompt to Gemini and return the text reply."""
    # TODO:
    #   from google import genai
    #   client = genai.Client(api_key=get_api_key())
    #   resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    #   return resp.text
    client = genai.Client(api_key=get_api_key())
    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return resp.text    
    raise NotImplementedError


def main() -> None:
    print(ask("Reply with the single word: OK"))


if __name__ == "__main__":
    main()
