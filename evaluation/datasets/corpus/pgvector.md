# pgvector

pgvector is an open-source extension for PostgreSQL that adds a vector column
type and vector similarity search. It lets an application store embeddings
alongside relational data and run nearest-neighbour queries using operators for
L2 distance, inner product, and cosine distance. pgvector supports approximate
indexes such as IVFFlat and HNSW to speed up search on large tables at the cost
of some recall. It is a convenient way to add dense retrieval to a system that
already uses PostgreSQL.
