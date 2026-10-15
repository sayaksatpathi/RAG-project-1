# Dense Retrieval

Dense retrieval represents queries and passages as embedding vectors in a shared
semantic space and ranks passages by vector similarity, usually cosine
similarity. Unlike lexical methods such as BM25, dense retrieval can match
paraphrases and synonyms that share no exact words with the query. Its quality
depends heavily on the embedding model, and it can struggle with rare exact
tokens such as identifiers. Hybrid retrieval combines dense and sparse methods
to capture the strengths of both.
