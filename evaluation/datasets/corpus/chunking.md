# Document Chunking

Chunking splits a long document into smaller passages before indexing so that
retrieval returns focused, relevant spans rather than entire documents. Common
strategies use a fixed window of tokens or words with some overlap between
adjacent chunks so that a sentence spanning a boundary is not lost. The chunk
size and overlap are tuning parameters: chunks that are too large dilute
relevance, while chunks that are too small lose context. Chunk configuration
should be versioned so that re-indexing is deliberate.
