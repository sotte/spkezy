"""LLM-based post-processing for transcripts."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from spkezy_config import load_toml_config

DEFAULT_PROMPT = """\
You are a cleanup assistant for live dictation.
Lightly clean the transcript: remove filler words, fix obvious ASR errors,
preserve meaning, keep the same tone, and do not add new content.
If the transcript is already clean, return it unchanged.
"""


@dataclass
class PostprocessConfig:
    enabled: bool = False
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    preferred_terms: list[str] = field(default_factory=list)
    prompt_override: str | None = None


def load_postprocess_config(log: Any | None = None) -> PostprocessConfig:
    data = load_toml_config(log)
    section = data.get("postprocess_llm", {})
    config = PostprocessConfig()

    if isinstance(section, dict):
        enabled = section.get("enabled")
        if isinstance(enabled, bool):
            config.enabled = enabled

        provider = section.get("provider")
        if isinstance(provider, str) and provider:
            config.provider = provider

        model = section.get("model")
        if isinstance(model, str) and model:
            config.model = model

        preferred_terms = section.get("preferred_terms")
        if isinstance(preferred_terms, list):
            config.preferred_terms = [term for term in preferred_terms if isinstance(term, str)]

        prompt_override = section.get("prompt_override")
        if isinstance(prompt_override, str) and prompt_override.strip():
            config.prompt_override = prompt_override

    return config


def _build_user_prompt(transcript: str, preferred_terms: list[str]) -> str:
    if preferred_terms:
        terms_block = "\n".join(f"- {term}" for term in preferred_terms)
        return f"Preferred terms (use when ambiguous):\n{terms_block}\n\nTranscript:\n{transcript}"
    return f"Transcript:\n{transcript}"


def postprocess_transcript(
    transcript: str, config: PostprocessConfig, log: Any | None = None
) -> str:
    if not config.enabled:
        return transcript

    if config.provider.lower() != "openai":
        if log:
            log.warning("postprocess_provider_unsupported", provider=config.provider)
        return transcript

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        if log:
            log.warning("postprocess_missing_api_key")
        return transcript

    if not transcript.strip():
        return transcript

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        system_prompt = config.prompt_override or DEFAULT_PROMPT
        user_prompt = _build_user_prompt(transcript, config.preferred_terms)
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        cleaned = response.choices[0].message.content if response.choices else None
        if cleaned and cleaned.strip():
            if log:
                log.info("postprocess_completed", length=len(cleaned))
            return cleaned.strip()
    except Exception as exc:
        if log:
            log.warning("postprocess_failed", error=str(exc))

    return transcript
