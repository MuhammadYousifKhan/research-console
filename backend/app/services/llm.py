import json
import re
from typing import Any

import httpx

from app.core.config import settings


class LLMError(Exception):
    """Raised when an LLM call cannot produce a usable result.

    The message carries the real cause (HTTP status + response body, a parse
    failure, or a missing key) so callers can surface it instead of pretending
    the call succeeded.
    """


class LLMClient:
    def __init__(self) -> None:
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/")
        self.model = settings.openai_model

    async def complete_json(self, system: str, user: str) -> dict[str, Any]:
        text = await self.complete_text(system=system, user=user)
        cleaned = self._strip_code_fences(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as error:
            raise LLMError(
                f"LLM returned output that is not valid JSON: {error}. "
                f"First 200 chars: {cleaned[:200]!r}"
            ) from error

    async def complete_text(self, system: str, user: str) -> str:
        if not self.api_key:
            raise LLMError(
                "LLM API key is not configured (OPENAI_API_KEY is empty in backend/.env)."
            )

        if "generativelanguage.googleapis.com" in self.base_url:
            return await self._complete_gemini(system=system, user=user)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }

        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as error:
            raise LLMError(self._http_status_message(error)) from error
        except httpx.HTTPError as error:
            raise LLMError(f"LLM request failed: {error}") from error
        except (KeyError, IndexError, TypeError) as error:
            raise LLMError(f"Unexpected LLM response shape: {error}") from error

        if content is None:
            raise LLMError(
                "LLM returned empty content (the response may have been filtered or truncated)."
            )
        return content

    async def _complete_gemini(self, system: str, user: str) -> str:
        model = self.model.removeprefix("models/")
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model}:generateContent"
        )
        payload = {
            "systemInstruction": {
                "parts": [{"text": system}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(
                    endpoint,
                    params={"key": self.api_key},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                parts = data["candidates"][0]["content"]["parts"]
                return "".join(part.get("text", "") for part in parts)
        except httpx.HTTPStatusError as error:
            raise LLMError(self._http_status_message(error)) from error
        except (httpx.HTTPError, KeyError, IndexError, TypeError) as error:
            raise LLMError(f"LLM request failed: {error}") from error

    @staticmethod
    def _http_status_message(error: httpx.HTTPStatusError) -> str:
        status_code = error.response.status_code
        try:
            body = error.response.text
        except Exception:  # pragma: no cover - body already consumed/streamed
            body = ""
        body = body.strip().replace("\n", " ")
        detail = f" Response: {body[:300]}" if body else ""
        return (
            f"LLM request failed with HTTP {status_code}. "
            f"Check API quota, billing, rate limits, region, or model access.{detail}"
        )

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```[a-zA-Z0-9]*\s*\n?", "", stripped)
            stripped = re.sub(r"\n?```$", "", stripped.strip())
        return stripped.strip()
