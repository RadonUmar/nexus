from __future__ import annotations

from anthropic import Anthropic
from openai import OpenAI

from .settings import settings


anthropic_client = Anthropic(api_key=settings.anthropic_api_key)
openai_client = OpenAI(api_key=settings.openai_api_key or "unset")

