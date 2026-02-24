from __future__ import annotations

from openai import OpenAI

from .settings import settings


openai_client = OpenAI(api_key=settings.openai_api_key)
