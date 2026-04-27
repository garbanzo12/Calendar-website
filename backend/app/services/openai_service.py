import json
import time

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


class OpenAIService:
    embeddings_url = "https://api.openai.com/v1/embeddings"
    chat_completions_url = "https://api.openai.com/v1/chat/completions"

    @classmethod
    async def get_embedding(cls, text: str) -> list[float]:
        cls._ensure_api_key()

        payload = {
            "model": settings.openai_embedding_model,
            "input": text,
        }

        async with httpx.AsyncClient(timeout=settings.openai_timeout_seconds) as client:
            response = await client.post(
                cls.embeddings_url,
                headers=cls._headers(),
                json=payload,
            )

        cls._raise_for_status(response, "Failed to generate embedding")

        data = response.json().get("data") or []
        if not data or "embedding" not in data[0]:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Embedding response was empty",
            )

        return data[0]["embedding"]

    @classmethod
    async def generate_chat_payload(cls, prompt: str) -> tuple[dict, dict]:
        cls._ensure_api_key()

        system_prompt = (
            "You are a helpful assistant that remembers the user's context. "
            "Use the supplied context only when it is relevant. "
            "Do not repeat prior context unless it directly helps answer the user. "
            "When the user is asking to create or schedule something, decide if there is enough "
            "information to create a task. "
            "Return JSON only with this shape: "
            '{"reply":"string","task":{"should_create":true,"title":"string or null",'
            '"start_iso":"ISO-8601 datetime or null","description":"string or null"}}. '
            "If no task should be created, set task.should_create to false and the other task fields to null."
        )

        payload = {
            "model": settings.openai_chat_model,
            "temperature": settings.chat_temperature,
            "max_tokens": settings.chat_max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        }

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=settings.openai_timeout_seconds) as client:
            response = await client.post(
                cls.chat_completions_url,
                headers=cls._headers(),
                json=payload,
            )
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        cls._raise_for_status(response, "Failed to generate chat response")

        body = response.json()
        message = ((body.get("choices") or [{}])[0].get("message") or {}).get("content", "")
        if not message:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Chat response was empty",
            )

        try:
            parsed = json.loads(message)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Model returned invalid JSON",
            ) from exc

        usage = body.get("usage") or {}
        usage["duration_ms"] = duration_ms
        return parsed, usage

    @staticmethod
    def _ensure_api_key() -> None:
        if settings.openai_api_key:
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API key is not configured",
        )

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _raise_for_status(response: httpx.Response, detail: str) -> None:
        if response.status_code < 400:
            return

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        message = payload.get("error", {}).get("message") or detail
        raise HTTPException(status_code=response.status_code, detail=message)
