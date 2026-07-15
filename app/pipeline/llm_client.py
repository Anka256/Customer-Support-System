import json
import re

from openai import OpenAI

from app.config import get_settings

_settings = get_settings()

# Single OpenAI-compatible client pointed at OpenRouter. Every pipeline node
# picks its model from config — swapping models is an env var change, not a
# code change.
client = OpenAI(
    base_url=_settings.openrouter_base_url,
    api_key=_settings.openrouter_api_key,
)


class LLMCallError(Exception):
    """Raised when an LLM call fails or returns unparseable output."""


def call_llm(model: str, system_prompt: str, user_prompt: str) -> str:
    """One chat completion call. Raises LLMCallError on any failure."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
    except Exception as exc:  # noqa: BLE001 — normalize all SDK/network errors
        raise LLMCallError(f"LLM request failed for model {model}: {exc}") from exc

    content = response.choices[0].message.content
    if not content:
        raise LLMCallError(f"LLM returned empty content for model {model}")
    return content


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json(text: str) -> dict:
    """Parse a JSON object out of an LLM response, tolerating markdown fences
    and leading/trailing prose the model may add despite instructions."""
    candidate = text.strip()
    fence_match = _JSON_FENCE_RE.search(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Last resort: grab the widest {...} span in the text.
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMCallError(f"Could not parse JSON from LLM output: {exc}") from exc

    raise LLMCallError("LLM output contained no parseable JSON object")


def call_llm_json(model: str, system_prompt: str, user_prompt: str) -> dict:
    raw = call_llm(model, system_prompt, user_prompt)
    return extract_json(raw)
