// Vector indexes used by RecommendationsReader (db.index.vector.queryNodes).
// Page.text_embedding  — S-BERT all-MiniLM-L6-v2 (384 dims)
// Page.hybridEmbedding — GraphSAGE output (128 dims)
CREATE VECTOR INDEX page_text_index IF NOT EXISTS
FOR (p:Page) ON (p.text_embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX page_hybrid_index IF NOT EXISTS
FOR (p:Page) ON (p.hybridEmbedding)
OPTIONS {indexConfig: {`vector.dimensions`: 128, `vector.similarity_function`: 'cosine'}};
