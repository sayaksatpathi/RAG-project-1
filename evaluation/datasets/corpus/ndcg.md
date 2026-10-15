# nDCG

Normalized Discounted Cumulative Gain (nDCG) is a ranking metric that rewards
placing highly relevant results near the top of a ranked list. Discounted
Cumulative Gain sums each result's graded relevance divided by a logarithmic
discount based on its position, so a relevant item lower in the list
contributes less. nDCG divides DCG by the ideal DCG of the best possible
ordering, producing a score between 0 and 1. nDCG requires graded relevance
labels, unlike recall, which needs only binary relevance.
