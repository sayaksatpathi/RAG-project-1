"""Generation providers behind a Protocol.

The default `MockProvider` is deterministic and offline: it produces an
extractive answer from the supplied evidence and emits citations to the passage
IDs it used. It never invents a citation to a passage it was not given, so it
exercises the grounded-generation and citation-validation paths faithfully.

An OpenAI-compatible provider is available optionally; it is bounded by a
timeout and surfaces provider errors rather than retrying unboundedly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ragbench.config import Config
from ragbench.models import RetrievalResult

# Versioned prompt template (kept here so changes are traceable).
PROMPT_VERSION = "mock-extractive-1.0.0"


@dataclass
class GenerationOutput:
    text: str
    cited_passage_ids: list[str]
    model: str


class GenerationProvider(Protocol):
    name: str

    def generate(self, query: str, evidence: list[RetrievalResult]) -> GenerationOutput: ...


class MockProvider:
    """Deterministic extractive generator used for offline runs and tests."""

    name = "mock"

    def generate(self, query: str, evidence: list[RetrievalResult]) -> GenerationOutput:
        if not evidence:
            return GenerationOutput(
                text="I don't have enough evidence in the indexed corpus to answer that.",
                cited_passage_ids=[],
                model=f"{self.name}:{PROMPT_VERSION}",
            )
        # Use the top passages as the grounded answer; cite exactly those used.
        used = evidence[: min(2, len(evidence))]
        snippets = [r.text.strip().split("\n")[0] for r in used]
        body = " ".join(s[:400] for s in snippets if s)
        marks = " ".join(f"[{i + 1}]" for i in range(len(used)))
        text = f"{body} {marks}".strip()
        return GenerationOutput(
            text=text,
            cited_passage_ids=[r.chunk_id for r in used],
            model=f"{self.name}:{PROMPT_VERSION}",
        )


def build_generation_provider(config: Config) -> GenerationProvider:
    if config.llm_provider == "mock":
        return MockProvider()
    if config.llm_provider == "openai":  # pragma: no cover - optional / network
        from ragbench.generation.openai_provider import OpenAIProvider

        return OpenAIProvider(config)
    raise ValueError(f"unknown llm provider: {config.llm_provider}")
