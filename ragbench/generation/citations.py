"""Citation validation.

We measure distinct, non-collapsible things:
  * identifier validity: does each cited passage ID exist among the passages
    actually retrieved for this query?
  * index-version consistency: does the cited passage belong to the expected
    index version?

Whether the cited passage *semantically supports* the claim, and overall answer
correctness, are separate measurements handled by the evaluation harness and
are NOT asserted here.
"""

from __future__ import annotations

from ragbench.models import Citation, RetrievalResult


def validate_citations(
    cited_ids: list[str], retrieved: list[RetrievalResult], index_version: str
) -> list[Citation]:
    retrieved_by_id = {r.chunk_id: r for r in retrieved}
    citations: list[Citation] = []
    for cid in cited_ids:
        r = retrieved_by_id.get(cid)
        valid = r is not None and r.index_version == index_version
        doc_id = r.document_id if r else ""
        citations.append(Citation(chunk_id=cid, document_id=doc_id, valid=valid))
    return citations
