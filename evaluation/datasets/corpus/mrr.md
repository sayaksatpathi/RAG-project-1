# Mean Reciprocal Rank

Mean Reciprocal Rank (MRR) measures how high the first relevant result appears
in a ranked list. For a single query the reciprocal rank is one divided by the
position of the first relevant result, or zero if no relevant result is
retrieved. MRR is the mean of these reciprocal ranks across all queries. MRR is
well suited to tasks where the user wants a single correct answer quickly, such
as question answering, because it only cares about the first relevant hit.
