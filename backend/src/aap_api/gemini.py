import os

from dotenv import load_dotenv
from google import genai

load_dotenv()


def get_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return api_key


def get_client() -> genai.Client:
    return genai.Client(api_key=get_api_key())