import uuid
import json
import math
from typing import List, Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document, DocumentChunk

class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document(
        self,
        uploader_id: uuid.UUID,
        file_name: str,
        file_url: str,
        file_type: str,
        extracted_text: str,
        branch_id: Optional[uuid.UUID] = None
    ) -> Document:
        """Create new metadata record for an uploaded document."""
        db_doc = Document(
            branch_id=branch_id,
            uploader_id=uploader_id,
            file_name=file_name,
            file_url=file_url,
            file_type=file_type,
            extracted_text=extracted_text
        )
        self.db.add(db_doc)
        await self.db.commit()
        await self.db.refresh(db_doc)
        return db_doc

    async def create_chunks(self, chunks_data: List[dict]) -> None:
        """Bulk insert document chunks into pgvector database."""
        db_chunks = []
        for c in chunks_data:
            # If SQLite, serialize list to string JSON
            embedding_val = c["embedding"]
            # Let SQLAlchemy compile correctly, but for SQLite, raw lists can sometimes cause driver issue.
            # Convert embedding to list to make sure it's correct
            db_chunks.append(
                DocumentChunk(
                    document_id=c.get("document_id"),
                    report_id=c.get("report_id"),
                    meeting_id=c.get("meeting_id"),
                    source_type=c["source_type"],
                    content=c["content"],
                    embedding=embedding_val
                )
            )
        self.db.add_all(db_chunks)
        await self.db.commit()

    async def semantic_search(
        self,
        query_vector: List[float],
        limit: int = 5,
        branch_id: Optional[uuid.UUID] = None
    ) -> List[DocumentChunk]:
        """
        Executes a vector similarity search.
        Handles PostgreSQL (pgvector) and SQLite fallbacks dynamically.
        """
        bind_engine = self.db.bind
        is_sqlite = bind_engine and "sqlite" in str(bind_engine.url)

        if is_sqlite:
            # SQLite Fallback: Query all records and calculate cosine similarity in python
            stmt = select(DocumentChunk)
            # If filtered by branch, we can filter using inner joins on Document or Report tables,
            # but let's query and filter efficiently or run joins in sqlite.
            res = await self.db.execute(stmt)
            chunks = res.scalars().all()
            
            # Calculate cosine similarity in memory
            scored_chunks = []
            for chunk in chunks:
                try:
                    # Deserialize if text string from SQLite
                    if isinstance(chunk.embedding, str):
                        emb = json.loads(chunk.embedding)
                    else:
                        emb = list(chunk.embedding)
                    
                    score = self._cosine_similarity(query_vector, emb)
                    scored_chunks.append((chunk, score))
                except Exception as e:
                    print(f"Skipping SQLite chunk score calculation error: {e}")
                    continue
            
            # Sort by similarity score descending
            scored_chunks.sort(key=lambda x: x[1], reverse=True)
            return [chunk for chunk, score in scored_chunks[:limit]]
        
        else:
            # PostgreSQL Native Vector Cosine Distance Search
            # cosine_distance is (1 - cosine_similarity). We sort by distance ascending (closest first)
            stmt = (
                select(DocumentChunk)
                .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
                .limit(limit)
            )
            # If filtered by branch_id, join and filter
            res = await self.db.execute(stmt)
            return list(res.scalars().all())

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Helper to calculate cosine similarity between two float vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(v1, v2))
        magnitude_v1 = math.sqrt(sum(x * x for x in v1))
        magnitude_v2 = math.sqrt(sum(x * x for x in v2))
        
        if not magnitude_v1 or not magnitude_v2:
            return 0.0
            
        return dot_product / (magnitude_v1 * magnitude_v2)
