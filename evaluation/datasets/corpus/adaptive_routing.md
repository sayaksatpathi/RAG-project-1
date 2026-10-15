# Adaptive Retrieval Routing

Adaptive retrieval routing chooses a retrieval strategy per query instead of
using one fixed method for every query. A router inspects query characteristics
such as the presence of exact identifiers, rare terms, length, or paraphrase
style, and selects sparse, dense, or hybrid retrieval accordingly. The goal is
to improve the quality, latency, and cost trade-off over a single fixed
baseline. A robust router falls back to a strong default such as fixed hybrid
retrieval whenever it is uncertain or sees an unfamiliar query.
