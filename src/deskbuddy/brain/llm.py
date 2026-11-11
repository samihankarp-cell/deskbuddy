"""The two AI models: a small fast one for the instant reply, a big one for the work."""
import json
import re

from langchain_openai import ChatOpenAI


def fast_model(settings) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.fast_model, base_url=settings.base_url, api_key=settings.api_key,
        temperature=0, timeout=20, max_retries=1, max_tokens=300,
    )


def agent_model(settings) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.agent_model, base_url=settings.base_url, api_key=settings.api_key,
        temperature=0, timeout=90, max_retries=2, max_tokens=1500,
    )


def text_of(message) -> str:
    content = message.content
    if isinstance(content, list):
        content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
    return (content or "").strip()


def parse_json(text: str) -> dict | None:
    """Pull the first JSON object out of a model reply. None if there is none."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        return None
