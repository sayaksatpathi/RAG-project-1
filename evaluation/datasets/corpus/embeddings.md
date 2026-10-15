# Text Embeddings

A text embedding maps a piece of text to a fixed-length vector of real numbers
such that texts with similar meaning have nearby vectors. Embeddings are
produced by a neural encoder trained so that semantic similarity corresponds to
cosine similarity in the vector space. Embedding dimensionality, the training
data, and the pooling strategy all affect quality. Vectors from two different
embedding models are not comparable and must never be mixed in one index.
