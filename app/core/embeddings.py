from sentence_transformers import SentenceTransformer

from app.core.config import settings


_model = None


def get_embedding_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)

    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    model = get_embedding_model()
    embedding = model.encode(query, convert_to_numpy=True)
    return embedding.tolist()