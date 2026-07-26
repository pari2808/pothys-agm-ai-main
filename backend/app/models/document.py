import uuid
from sqlalchemy import String, ForeignKey, DateTime, func, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.compiler import compiles
from pgvector.sqlalchemy import Vector
from app.db.base_class import Base

@compiles(Vector, "sqlite")
def compile_vector_sqlite(type_, compiler, **kw):
    return "TEXT"

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), nullable=True)
    uploader_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("daily_reports.id"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "PDF", "EXCEL", "WORD"
    extracted_text: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    branch: Mapped["Branch"] = relationship(back_populates="documents")
    uploader: Mapped["User"] = relationship(back_populates="uploaded_documents")
    report: Mapped["DailyReport"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index('ix_document_chunks_embedding', 'embedding', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=True)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("daily_reports.id"), nullable=True)
    meeting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meetings.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "DOCUMENT", "REPORT", "MEETING"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="chunks")
    report: Mapped["DailyReport"] = relationship(back_populates="document_chunks")
    meeting: Mapped["Meeting"] = relationship(back_populates="document_chunks")
