import uuid
from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding, SparseTextEmbedding

COLLECTION_NAME = "documind"
DENSE_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
SPARSE_MODEL_NAME = "Qdrant/bm25"

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

dense_embedder = TextEmbedding(model_name=DENSE_MODEL_NAME)
sparse_embedder = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)

# Determine dense vector size from a probe embedding
_probe = list(dense_embedder.embed(["probe"]))[0]
DENSE_DIM = len(_probe)

# ---------------------------------------------------------------------------
# Client + collection
# ---------------------------------------------------------------------------

client = QdrantClient(location=":memory:")

client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config={
        "dense": models.VectorParams(
            size=DENSE_DIM,
            distance=models.Distance.COSINE,
        )
    },
    sparse_vectors_config={
        "sparse": models.SparseVectorParams(
            modifier=models.Modifier.IDF,
        )
    },
)


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

def add_chunks(chunks: list) -> None:
    """
    Embed and upsert chunks produced by ingest.process_pdf().

    Each chunk: {"text": str, "metadata": {"source": str, "page": int}}
    """
    texts = [chunk["text"] for chunk in chunks]

    dense_vecs = list(dense_embedder.embed(texts))
    sparse_vecs = list(sparse_embedder.embed(texts))

    points = []
    for chunk, dvec, svec in zip(chunks, dense_vecs, sparse_vecs):
        points.append(
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    "dense": dvec.tolist(),
                    "sparse": models.SparseVector(
                        indices=svec.indices.tolist(),
                        values=svec.values.tolist(),
                    ),
                },
                payload={
                    "text": chunk["text"],
                    "metadata": chunk["metadata"],
                },
            )
        )

    client.upsert(collection_name=COLLECTION_NAME, points=points)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def hybrid_search(query: str, top_k: int = 5) -> list:
    """
    Hybrid search: fuse dense (semantic) + sparse (BM25) results via RRF.

    Returns a list of {"text": str, "metadata": dict} dicts.
    """
    dense_vec = list(dense_embedder.embed([query]))[0].tolist()
    sparse_vec = list(sparse_embedder.embed([query]))[0]

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            models.Prefetch(
                query=dense_vec,
                using="dense",
                limit=top_k * 2,
            ),
            models.Prefetch(
                query=models.SparseVector(
                    indices=sparse_vec.indices.tolist(),
                    values=sparse_vec.values.tolist(),
                ),
                using="sparse",
                limit=top_k * 2,
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=top_k,
    )

    return [
        {
            "text": point.payload["text"],
            "metadata": point.payload["metadata"],
        }
        for point in results.points
    ]
