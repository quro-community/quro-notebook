from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

SCHEMA_VERSION = "1.0.0"
PAGE_INDEX_SCHEMA_ID = "quro-notebook:page-index"
EMBEDDING_INDEX_SCHEMA_ID = "quro-notebook:embedding-index"


@dataclass
class PageEntrySchema:
    doc_id: str
    title: str
    created_at: str
    intent: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    topic: Optional[str] = None
    source_path: str = ""
    summary: str = ""


@dataclass
class PageIndexSchema:
    project: str
    pages: list[PageEntrySchema]
    total_count: int
    build_time: str
    schema_version: str = SCHEMA_VERSION


@dataclass
class EmbeddingEntrySchema:
    doc_id: str
    embedding: list[float]
    title: str = ""


@dataclass
class EmbeddingIndexSchema:
    model: str
    dim: int
    docs: list[EmbeddingEntrySchema]
    build_time: str
    schema_version: str = SCHEMA_VERSION


@dataclass
class PageFragmentSchema:
    doc_id: str
    title: str
    created_at: str
    body_html: str
    toc_html: str
    intent: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    source_path: str = ""
    build_time: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
