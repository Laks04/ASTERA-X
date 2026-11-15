"""pgvector helpers. KnowledgeChunk.embedding is JSON on SQLite and `vector(384)` on PostgreSQL (dialect variant),
so the ORM attribute has no distance operators; cast it explicitly for similarity queries (PostgreSQL only)."""
from pgvector.sqlalchemy import Vector
from sqlalchemy import cast

from app.models import KnowledgeChunk

EMBEDDING_DIM = 384


def cosine_distance(query_vec: list[float]):
    return cast(KnowledgeChunk.embedding, Vector(EMBEDDING_DIM)).cosine_distance(query_vec)
