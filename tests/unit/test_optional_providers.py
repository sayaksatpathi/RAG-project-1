"""Optional providers fail gracefully and clearly when their dependency or
credential is absent — verified offline, without the heavy packages or network."""

import dataclasses
import importlib.util

import pytest

from ragbench.config import Config
from ragbench.embeddings import build_embedding_provider
from ragbench.generation.openai_provider import OpenAIProvider
from ragbench.generation.provider import build_generation_provider

_HAS_ST = importlib.util.find_spec("sentence_transformers") is not None


def test_openai_requires_api_key():
    cfg = dataclasses.replace(Config(), llm_provider="openai", openai_api_key=None)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_generation_provider(cfg)


@pytest.mark.skipif(_HAS_ST, reason="sentence-transformers is installed here")
def test_sentence_transformers_absent_gives_clear_error():
    cfg = dataclasses.replace(Config(), embedding_provider="sentence-transformers")
    with pytest.raises(RuntimeError, match="sentence-transformers"):
        build_embedding_provider(cfg)


def test_unknown_providers_raise():
    with pytest.raises(ValueError):
        build_embedding_provider(dataclasses.replace(Config(), embedding_provider="nope"))
    with pytest.raises(ValueError):
        build_generation_provider(dataclasses.replace(Config(), llm_provider="nope"))


def test_openai_citation_parser_maps_bracket_markers():
    ids = ["c1", "c2", "c3"]
    # cites [1] and [3]; [9] is out of range and ignored; order preserved, deduped
    assert OpenAIProvider._parse_citations("answer [1] more [3] and [1] again [9]", ids) == [
        "c1", "c3"
    ]


def test_openai_prompt_numbers_evidence():
    from ragbench.models import RetrievalResult

    cfg = dataclasses.replace(Config(), openai_api_key="test-key")
    prov = OpenAIProvider(cfg)
    ev = [
        RetrievalResult("c1", "d1", 1, 1.0, "bm25", text="alpha"),
        RetrievalResult("c2", "d1", 2, 0.9, "bm25", text="beta"),
    ]
    prompt, ids = prov._build_prompt("q?", ev)
    assert "[1] alpha" in prompt and "[2] beta" in prompt
    assert ids == ["c1", "c2"]
