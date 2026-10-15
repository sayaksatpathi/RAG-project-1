# Abstention in RAG

Abstention is the behavior of a retrieval-augmented generation system declining
to answer when the indexed corpus does not contain enough supporting evidence.
Abstention reduces unsupported or hallucinated answers on unanswerable
questions. A naive fixed similarity threshold is fragile; thresholds should be
calibrated on validation data, and the trade-off between abstention precision
and recall should be reported explicitly.
