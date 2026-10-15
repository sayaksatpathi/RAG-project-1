"""Fault-injection generation providers for controlled reliability experiments.

These implement the same generate() contract as the real providers, so they can
be swapped onto a pipeline to simulate provider failures and latency without any
network. They are test/experiment tooling, not part of the production factory.
"""

from __future__ import annotations

import time

from ragbench.generation.provider import GenerationOutput, MockProvider
from ragbench.models import RetrievalResult


class FailingProvider:
    """Always raises, to exercise the pipeline's graceful-degradation path."""

    name = "failing"

    def __init__(self, exc: Exception | None = None) -> None:
        self._exc = exc or RuntimeError("simulated provider outage")

    def generate(self, query: str, evidence: list[RetrievalResult]) -> GenerationOutput:
        raise self._exc


class SlowProvider:
    """Delegates to the mock provider after a fixed delay, to measure latency
    under a slow provider. The delay is bounded and explicit."""

    name = "slow"

    def __init__(self, delay_s: float = 0.05) -> None:
        self.delay_s = delay_s
        self._inner = MockProvider()

    def generate(self, query: str, evidence: list[RetrievalResult]) -> GenerationOutput:
        time.sleep(self.delay_s)
        out = self._inner.generate(query, evidence)
        return GenerationOutput(text=out.text, cited_passage_ids=out.cited_passage_ids,
                                model=f"{self.name}:{out.model}")
