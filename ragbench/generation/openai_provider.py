"""Optional OpenAI-compatible generation provider.

Uses an OpenAI-compatible Chat Completions endpoint (configurable base URL, so it
also works with local servers such as Ollama's OpenAI shim). Built on httpx,
which RAGBench already depends on for tests, so no extra package is required.

Reliability properties required by the design:
  * a bounded request timeout (no hanging);
  * meaningful errors surfaced to the caller (the pipeline degrades gracefully);
  * retries ONLY for transient statuses (429/5xx), bounded to a small count with
    backoff — never an unbounded retry loop.

The module imports cleanly with no network or credential access; the client is
constructed lazily and a missing API key raises a clear error.
"""

from __future__ import annotations

import time

from ragbench.config import Config
from ragbench.generation.provider import GenerationOutput
from ragbench.models import RetrievalResult

PROMPT_VERSION = "openai-grounded-1.0.0"
_SYSTEM = (
    "You answer strictly from the provided numbered evidence passages. If the "
    "evidence is insufficient, say so. Cite the passages you use with their "
    "bracketed numbers, e.g. [1] [3]. Do not use outside knowledge."
)
_TRANSIENT = {429, 500, 502, 503, 504}


class OpenAIProvider:
    name = "openai"

    def __init__(self, config: Config, timeout_s: float = 30.0, max_retries: int = 2) -> None:
        if not config.openai_api_key:
            raise RuntimeError(
                "RAGBENCH_LLM_PROVIDER=openai requires RAGBENCH_OPENAI_API_KEY to be "
                "set in the environment. Use the default mock provider for offline runs."
            )
        self._key = config.openai_api_key
        self._base = config.openai_base_url.rstrip("/")
        self._model = config.llm_model
        self._timeout = timeout_s
        self._max_retries = max_retries

    def _build_prompt(self, query: str, evidence: list[RetrievalResult]) -> tuple[str, list[str]]:
        lines, ids = [], []
        for i, r in enumerate(evidence, start=1):
            lines.append(f"[{i}] {r.text}")
            ids.append(r.chunk_id)
        context = "\n".join(lines) if lines else "(no evidence)"
        user = f"Evidence:\n{context}\n\nQuestion: {query}\n\nAnswer with citations:"
        return user, ids

    @staticmethod
    def _parse_citations(text: str, ordered_ids: list[str]) -> list[str]:
        import re

        cited: list[str] = []
        for m in re.findall(r"\[(\d+)\]", text):
            idx = int(m) - 1
            if 0 <= idx < len(ordered_ids) and ordered_ids[idx] not in cited:
                cited.append(ordered_ids[idx])
        return cited

    def generate(self, query: str, evidence: list[RetrievalResult]) -> GenerationOutput:
        import httpx

        user, ordered_ids = self._build_prompt(query, evidence)
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
        }
        headers = {"Authorization": f"Bearer {self._key}"}
        url = f"{self._base}/chat/completions"

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = httpx.post(url, json=payload, headers=headers, timeout=self._timeout)
                if resp.status_code in _TRANSIENT and attempt < self._max_retries:
                    time.sleep(min(2 ** attempt, 4))  # bounded backoff
                    continue
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                cited = self._parse_citations(text, ordered_ids)
                return GenerationOutput(
                    text=text, cited_passage_ids=cited,
                    model=f"{self.name}:{self._model}:{PROMPT_VERSION}",
                )
            except Exception as exc:  # noqa: BLE001 - surfaced after bounded retries
                last_exc = exc
                if attempt < self._max_retries:
                    time.sleep(min(2 ** attempt, 4))
                    continue
                break
        raise RuntimeError(f"OpenAI-compatible generation failed: {last_exc}")
