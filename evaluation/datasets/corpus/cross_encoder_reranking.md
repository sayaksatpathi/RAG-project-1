# Cross-Encoder Reranking

A cross-encoder reranker takes a query and a candidate passage together as a
single input and outputs a relevance score. Because it attends jointly over the
query and passage, it is usually more accurate than the bi-encoder used for
first-stage dense retrieval, but it is far more expensive because every
candidate must be scored individually. Reranking is therefore applied only to a
small candidate set produced by a cheaper retriever. The accuracy gain must be
weighed against the added latency per query.
