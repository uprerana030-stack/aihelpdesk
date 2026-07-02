"""LLM provider abstraction — Gemini only (design doc Section 8.1).

The pipeline calls `llm_complete(...)`. It uses Google Gemini via the
`google-genai` SDK. If Gemini is not configured/available or errors, it
returns an `LLMResult` with `available=False` so callers can degrade gracefully
— e.g. fall back to manual routing rather than failing the request
(NFR: Availability / graceful degradation).

The SDK is imported lazily so the backend runs even when `google-genai`
is not installed.
"""
from __future__ import annotations

import concurrent.futures
import logging
import time
from dataclasses import dataclass

from app.core.config import get_settings

logger = logging.getLogger("helpdesk.llm")
settings = get_settings()

# Hard wall-clock bound so a network/auth hang can never stall a request.
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="gemini")
_GEMINI_TIMEOUT_S = 15
_RETRIES = 2  # retry transient 429/503/timeout before degrading this one call

# Only PERMANENT failures (bad/absent API key, permission denied) disable Gemini
# for the process. Transient errors (rate limit, high demand, timeout) must NOT
# permanently disable it — otherwise one blip kills auto-resolution until restart.
_gemini_disabled = False


def _is_permanent_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(s in msg for s in (
        "api key not valid", "api_key_invalid", "permission_denied", "unauthenticated",
        "invalid api key", "401", "403",
    ))


@dataclass
class LLMResult:
    text: str
    provider: str            # "gemini" | "none"
    model: str               # model id used, for AI-governance logging
    available: bool          # False => caller should degrade gracefully


def _call_gemini(prompt: str, system: str | None) -> LLMResult | None:
    global _gemini_disabled
    if not settings.gemini_api_key or _gemini_disabled:
        return None

    def _do() -> str:
        from google.genai import types

        from app.core.gemini import get_client

        client = get_client()
        config = types.GenerateContentConfig(
            system_instruction=system or None,
            http_options=types.HttpOptions(timeout=_GEMINI_TIMEOUT_S * 1000),  # ms
        )
        resp = client.models.generate_content(
            model=settings.gemini_model, contents=prompt, config=config
        )
        return (resp.text or "").strip()

    for attempt in range(1, _RETRIES + 2):  # initial try + _RETRIES retries
        try:
            text = _EXECUTOR.submit(_do).result(timeout=_GEMINI_TIMEOUT_S + 3)
            return LLMResult(text=text, provider="gemini", model=settings.gemini_model, available=True)
        except Exception as exc:  # noqa: BLE001
            if _is_permanent_error(exc):
                logger.error("Gemini permanently unavailable (%s); disabling for this process.", exc)
                _gemini_disabled = True
                return None
            logger.warning("Gemini call %d/%d failed transiently (%s).", attempt, _RETRIES + 1, exc or "timeout")
            if attempt <= _RETRIES:
                time.sleep(1.0 * attempt)
    # Transient failure after retries: degrade THIS call only; next call retries.
    return None


def llm_complete(prompt: str, system: str | None = None) -> LLMResult:
    """Call Gemini. Never raises — returns available=False on failure."""
    result = _call_gemini(prompt, system)
    if result is not None:
        return result
    logger.info("Gemini unavailable; caller should degrade gracefully.")
    return LLMResult(text="", provider="none", model="none", available=False)


def llm_configured() -> bool:
    return bool(settings.gemini_api_key)
