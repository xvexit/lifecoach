import json
from typing import Optional

import httpx
from openai import AsyncOpenAI

import config


def _make_client() -> AsyncOpenAI:
    kwargs = {"api_key": config.OPENAI_API_KEY}
    if config.OPENAI_BASE_URL:
        kwargs["base_url"] = config.OPENAI_BASE_URL
    http_client = httpx.AsyncClient(
        proxy=config.BOT_PROXY,
        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
    )
    kwargs["http_client"] = http_client
    return AsyncOpenAI(**kwargs)


client = _make_client()


async def llm_chat(
    messages: list[dict],
    model: Optional[str] = None,
    response_format: Optional[dict] = None,
    temperature: float = 0.7,
) -> str:
    kwargs = dict(
        model=model or config.OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
    )
    if response_format:
        kwargs["response_format"] = response_format
    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


async def llm_chat_json(messages: list[dict], model: Optional[str] = None) -> dict:
    text = await llm_chat(
        messages=messages,
        model=model,
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return json.loads(text)
