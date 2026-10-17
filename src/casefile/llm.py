"""LLM wiring (any OpenAI-compatible endpoint)."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)  # .env must beat any globally exported vars


def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "MISSING"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )


def get_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
