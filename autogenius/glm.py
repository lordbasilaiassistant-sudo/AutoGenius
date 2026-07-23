"""GLM client for AutoGenius.

Thin, dependency-light wrapper over z.ai's OpenAI-compatible endpoint. Encodes
the hard-won knobs that make glm-4.5-flash actually usable:

  * thinking:{type:disabled}   -> WITHOUT this, flash returns EMPTY content.
  * <think>...</think> stripping (stray reasoning sometimes leaks through).
  * 429 / 5xx retry with exponential backoff + jitter.
  * optional JSON mode with a brace-slice fallback extractor, so a verdict that
    arrives wrapped in prose still parses.

Reasoning `temperature` defaults low (0.3) because this agent's job is rigor,
not creativity; the CONJECTURE stage bumps it up deliberately.
"""
from __future__ import annotations

import json
import random
import re
import time

import requests

from . import config

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class GLMError(RuntimeError):
    pass


def _backoff(attempt: int) -> None:
    time.sleep(min(30.0, 2.0 * (2 ** attempt)) + random.uniform(0, 1.5))


def raw_chat(messages: list[dict], *, temperature: float = 0.3,
             max_tokens: int = 2000, json_mode: bool = False,
             retries: int = 4, api_key: str | None = None) -> str:
    """Return the model's text for a full messages array."""
    key = api_key or config.get_api_key()
    body = {
        "model": config.GLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        # The one line that makes flash work at all:
        "thinking": {"type": "disabled"},
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(
                config.GLM_URL, timeout=120,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"},
                json=body,
            )
            if r.status_code == 429 or r.status_code >= 500:
                last_err = GLMError(f"HTTP {r.status_code}: {r.text[:200]}")
                if attempt < retries:
                    _backoff(attempt)
                    continue
                raise last_err
            r.raise_for_status()
            content = (r.json()["choices"][0]["message"]["content"] or "")
            content = _THINK_RE.sub("", content).strip()
            if not content and attempt < retries:
                # Empty despite thinking:disabled -> transient; retry once or twice.
                last_err = GLMError("empty content")
                _backoff(attempt)
                continue
            return content
        except (requests.RequestException, KeyError, ValueError) as e:
            last_err = e
            if attempt < retries:
                _backoff(attempt)
                continue
            raise GLMError(str(e)) from e
    raise GLMError(str(last_err))


def chat(system: str, user: str, **kw) -> str:
    """Convenience: single system+user turn -> text."""
    return raw_chat(
        [{"role": "system", "content": system},
         {"role": "user", "content": user}], **kw)


def extract_json(text: str) -> dict:
    """Best-effort JSON object out of a model response.

    Tries a straight parse, then a brace-slice (handles prose-wrapped JSON),
    then a ```json fenced block.
    """
    text = _THINK_RE.sub("", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except Exception:
            pass
    a, b = text.find("{"), text.rfind("}")
    if a >= 0 and b > a:
        try:
            return json.loads(text[a:b + 1])
        except Exception:
            pass
    raise GLMError(f"no JSON object found in response: {text[:200]!r}")


def chat_json(system: str, user: str, **kw) -> dict:
    """single system+user turn -> parsed JSON object (with fallback extractor)."""
    kw.setdefault("json_mode", True)
    return extract_json(chat(system, user, **kw))
