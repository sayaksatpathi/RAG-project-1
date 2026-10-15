from ragbench.generation.citations import validate_citations
from ragbench.models import RetrievalResult


def _r(cid, iv="v1"):
    return RetrievalResult(chunk_id=cid, document_id="d1", rank=1, score=1.0,
                           strategy="hybrid", text="t", index_version=iv)


def test_valid_citation():
    retrieved = [_r("c1"), _r("c2")]
    cits = validate_citations(["c1"], retrieved, "v1")
    assert cits[0].valid and cits[0].document_id == "d1"


def test_citation_to_unretrieved_passage_is_invalid():
    cits = validate_citations(["ghost"], [_r("c1")], "v1")
    assert not cits[0].valid


def test_citation_wrong_index_version_is_invalid():
    cits = validate_citations(["c1"], [_r("c1", iv="v2")], "v1")
    assert not cits[0].valid
