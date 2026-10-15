# Reciprocal Rank Fusion

Reciprocal Rank Fusion (RRF) is a method for combining multiple ranked result
lists into a single ranking. For each item, RRF sums a contribution of
1 / (k + rank) across every list in which the item appears, where rank is the
item's one-based position and k is a smoothing constant (commonly 60). Because
RRF uses only ranks, it avoids the problem of comparing incommensurable scores
such as BM25 weights and cosine similarities. It was introduced by Cormack,
Clarke, and Buettcher in 2009 and is widely used in hybrid retrieval systems.
