"""LLM client abstraction — the only protocol in the project.

The spec explicitly plans to swap GPT-4.1 for Llama 3.1 in a later
phase. This protocol makes that swap possible without touching
retrieval or API code.

Phase 1: OpenAIClient (GPT-4.1)
Phase 2: LlamaClient — implements the same protocol, no other changes.
"""

from __future__ import annotations

import logging
from typing import Protocol

try:
    import groq
except ImportError:
    groq = None  # type: ignore[assignment]

try:
    import openai
except ImportError:
    openai = None  # type: ignore[assignment]

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]

from app.core.config import settings
from app.prompts.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Protocol for LLM backends.

    Any implementation must provide a ``generate`` method that takes
    a user prompt and a list of context strings, and returns a
    generated answer.
    """

    def generate(self, prompt: str, context: list[str]) -> str: ...


class OpenAIClient:
    """GPT-4.1 implementation of LLMClient.

    Calls the OpenAI Chat Completions API with:
    - System prompt enforcing grounding rules
    - Retrieved context injected as a system message
    - User question as the user message
    - temperature=0 for deterministic answers

    The OpenAI client is lazy-initialized on first ``generate()`` call
    so this module can be imported without ``OPENAI_API_KEY`` set.
    """

    def __init__(self) -> None:
        self._client: openai.OpenAI | None = None

    def _get_client(self) -> openai.OpenAI:
        """Lazy-initialize the OpenAI client."""
        if self._client is None:
            if not settings.openai_api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY is not set. Set it in .env or "
                    "as an environment variable before calling the LLM."
                )
            self._client = openai.OpenAI(api_key=settings.openai_api_key)
        return self._client

    def generate(self, prompt: str, context: list[str]) -> str:
        """Generate a grounded answer using GPT-4.1.

        Args:
            prompt: The user's question.
            context: List of retrieved chunk texts to ground the answer in.

        Returns:
            The generated answer text.

        Raises:
            openai.APIError: If the OpenAI API call fails.
        """
        # Build context block
        context_block = "\n\n---\n\n".join(
            f"[Context {i + 1}]\n{chunk}" for i, chunk in enumerate(context)
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": (
                    "RETRIEVED CONTEXT (answer ONLY from this — do not use "
                    "any knowledge outside these passages):\n\n"
                    f"{context_block}"
                ),
            },
            {"role": "user", "content": prompt},
        ]

        logger.info(
            "Calling GPT-4.1 (model=%s, context_chunks=%d, temperature=%s)",
            settings.model_name,
            len(context),
            settings.llm_temperature,
        )

        response = self._get_client().chat.completions.create(
            model=settings.model_name,
            messages=messages,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

        answer = response.choices[0].message.content.strip()

        logger.info(
            "GPT-4.1 response: %d chars, finish_reason=%s",
            len(answer),
            response.choices[0].finish_reason,
        )

        return answer


class GeminiClient:
    """Gemini implementation of LLMClient using official google-genai SDK.

    Calls Google Gen AI API with:
    - System prompt enforcing grounding rules
    - Context injected with identical prompt structure
    - temperature=0 for deterministic answers

    The Gemini client is lazy-initialized on first ``generate()`` call
    so this module can be imported without ``GEMINI_API_KEY`` set.
    """

    def __init__(self) -> None:
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        """Lazy-initialize the Gemini client."""
        if self._client is None:
            if not settings.gemini_api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. Set it in .env or "
                    "as an environment variable before calling the LLM."
                )
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    def generate(self, prompt: str, context: list[str]) -> str:
        """Generate a grounded answer using Gemini.

        Args:
            prompt: The user's question.
            context: List of retrieved chunk texts to ground the answer in.

        Returns:
            The generated answer text.
        """
        # Build context block (identical to OpenAIClient prompt structure)
        context_block = "\n\n---\n\n".join(
            f"[Context {i + 1}]\n{chunk}" for i, chunk in enumerate(context)
        )

        user_content = (
            "RETRIEVED CONTEXT (answer ONLY from this — do not use "
            "any knowledge outside these passages):\n\n"
            f"{context_block}\n\n"
            f"USER QUESTION: {prompt}"
        )

        logger.info(
            "Calling Gemini (model=%s, context_chunks=%d, temperature=%s)",
            settings.gemini_model,
            len(context),
            settings.llm_temperature,
        )

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_tokens,
        )

        response = self._get_client().models.generate_content(
            model=settings.gemini_model,
            contents=user_content,
            config=config,
        )

        answer = response.text.strip() if response.text else ""

        logger.info(
            "Gemini response: %d chars",
            len(answer),
        )

        return answer


class GroqClient:
    """Groq implementation of LLMClient using groq SDK.

    Calls Groq's Chat Completions API with:
    - System prompt enforcing grounding rules
    - Context injected into user prompt
    - llama-3.3-70b-versatile model
    - temperature=0 for deterministic answers

    The Groq client is lazy-initialized on first ``generate()`` call
    so this module can be imported without ``GROQ_API_KEY`` set.
    """

    def __init__(self) -> None:
        self._client: groq.Groq | None = None

    def _get_client(self) -> groq.Groq:
        """Lazy-initialize the Groq client."""
        if self._client is None:
            if not settings.groq_api_key:
                raise RuntimeError(
                    "GROQ_API_KEY is not set. Set it in .env or "
                    "as an environment variable before calling the LLM."
                )
            self._client = groq.Groq(api_key=settings.groq_api_key)
        return self._client

    def generate(self, prompt: str, context: list[str]) -> str:
        """Generate a grounded answer using Groq.

        Args:
            prompt: The user's question.
            context: List of retrieved chunk texts to ground the answer in.

        Returns:
            The generated answer text.
        """
        # Build context block (identical to OpenAIClient prompt structure)
        context_block = "\n\n---\n\n".join(
            f"[Context {i + 1}]\n{chunk}" for i, chunk in enumerate(context)
        )

        user_content = (
            "RETRIEVED CONTEXT (answer ONLY from this — do not use "
            "any knowledge outside these passages):\n\n"
            f"{context_block}\n\n"
            f"USER QUESTION: {prompt}"
        )

        logger.info(
            "Calling Groq (model=%s, context_chunks=%d, temperature=%s)",
            settings.groq_model,
            len(context),
            settings.llm_temperature,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        # Ordered fallback list — verified active as of 2026-08 via GET /openai/v1/models.
        # Primary model is first; smaller/cheaper models follow for rate-limit recovery.
        fallback_models = [
            settings.groq_model,              # llama-3.3-70b-versatile (primary)
            "llama-3.1-8b-instant",           # fast low-latency fallback
            "openai/gpt-oss-20b",             # OpenAI-weight compact model
            "qwen/qwen3.6-27b",               # Alibaba multilingual
            "openai/gpt-oss-120b",            # largest available
            "allam-2-7b",                     # smallest — last resort
        ]
        # De-duplicate in case settings.groq_model matches a hardcoded entry
        seen: set[str] = set()
        unique_fallbacks = []
        for m in fallback_models:
            if m not in seen:
                seen.add(m)
                unique_fallbacks.append(m)

        last_exception = None

        for model_name in unique_fallbacks:
            try:
                logger.info(
                    "Calling Groq (model=%s, context_chunks=%d, temperature=%s)",
                    model_name,
                    len(context),
                    settings.llm_temperature,
                )
                response = self._get_client().chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=settings.llm_temperature,
                    max_tokens=settings.llm_max_tokens,
                )
                answer = response.choices[0].message.content or ""
                answer = answer.strip()

                logger.info(
                    "Groq response from %s: %d chars",
                    model_name,
                    len(answer),
                )
                return answer
            except Exception as exc:
                err_str = str(exc)
                logger.warning(
                    "Groq model '%s' failed: %s. Trying next fallback model...",
                    model_name,
                    exc,
                )
                last_exception = exc
                # For decommissioned models there is no point waiting; continue immediately.
                # For rate limits the next model in the list should work.
                # Both cases: just continue to next model.
                continue

        if last_exception:
            raise last_exception
        return ""

