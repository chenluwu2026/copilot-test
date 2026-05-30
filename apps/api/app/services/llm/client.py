"""OpenAI 兼容 API 客户端（结构化 JSON 输出）。"""
import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def is_llm_available() -> bool:
    return bool(settings.openai_api_key)


def use_llm_agents() -> bool:
    return settings.agent_mode == "llm" and is_llm_available()


def complete_json(system: str, user: str) -> dict:
    if not settings.openai_api_key:
        raise RuntimeError("未配置 OPENAI_API_KEY")
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
        timeout=settings.llm_timeout_s,
    )
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    text = resp.choices[0].message.content or "{}"
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("LLM JSON parse failed: %s", text[:500])
        raise RuntimeError("LLM 返回非合法 JSON") from e
