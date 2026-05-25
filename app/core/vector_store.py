import chromadb

from app.core.config import settings
from app.core.embeddings import embed_texts, embed_query


def get_chroma_collection():
    client = chromadb.PersistentClient(path=settings.vector_db_dir)

    collection = client.get_or_create_collection(
        name="documents"
    )

    return collection


def add_chunks_to_vector_store(chunks: list[dict]) -> int:
    collection = get_chroma_collection()

    texts = [chunk["text"] for chunk in chunks]
    embeddings = embed_texts(texts)

    ids = [chunk["chunk_id"] for chunk in chunks]

    metadatas = [
    {
        "source": chunk["source"],
        "page": chunk.get("page") if chunk.get("page") is not None else -1,
        "section": chunk.get("section") if chunk.get("section") is not None else "",
        "extraction_method": chunk.get("extraction_method") if chunk.get("extraction_method") is not None else "",
        "chunk_index": chunk["chunk_index"]
    }
    for chunk in chunks
]

    collection.upsert(
    ids=ids,
    documents=texts,
    embeddings=embeddings,
    metadatas=metadatas
)

    return len(chunks)


def search_vector_store(query: str, top_k: int = 5, source: str | None = None) -> list[dict]:
    collection = get_chroma_collection()

    query_embedding = embed_query(query)

    query_kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": top_k
    }

    if source is not None:
        query_kwargs["where"] = {
            "source": source
        }

    results = collection.query(**query_kwargs)

    retrieved_chunks = []

    if not results["ids"] or not results["ids"][0]:
        return retrieved_chunks

    for i in range(len(results["ids"][0])):
        retrieved_chunks.append(
            {
                "chunk_id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            }
        )

    return retrieved_chunks


def delete_document_from_vector_store(source: str) -> int:
    collection = get_chroma_collection()

    existing = collection.get(
        where={
            "source": source
        }
    )

    ids = existing.get("ids", [])

    if not ids:
        return 0

    collection.delete(ids=ids)

    return len(ids)

def get_all_chunks_from_vector_store(source: str | None = None) -> list[dict]:
    collection = get_chroma_collection()

    if source is not None:
        results = collection.get(
            where={
                "source": source
            }
        )
    else:
        results = collection.get()

    ids = results.get("ids", [])
    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])

    chunks = []

    for chunk_id, text, metadata in zip(ids, documents, metadatas):
        chunks.append(
            {
                "chunk_id": chunk_id,
                "text": text,
                "source": metadata.get("source"),
                "page": metadata.get("page"),
                "section": metadata.get("section"),
                "extraction_method": metadata.get("extraction_method"),
                "chunk_index": metadata.get("chunk_index", 0)
            }
        )

    return chunks