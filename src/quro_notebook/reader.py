from quro_doc.ext.inspector import MetadataInspector
from quro_doc.ext.reader import MarkdownReader

from quro_notebook.metadata_protocol import QURO_NOTEBOOK_METADATA_SET

_DECLARED_KEYS = frozenset(item["key"] for item in QURO_NOTEBOOK_METADATA_SET)


def list_documents(project_root: str) -> list[dict]:
    """List all documents with lightweight summaries.

    Uses MetadataInspector.list_doc_ids() which returns summaries built by
    quro-doc's internal _build_doc_summary(). The fields extracted here
    MUST align with the metadata protocol declared in metadata_protocol.py.
    """
    inspector = MetadataInspector()
    all_docs: list[dict] = []
    offset = 0
    while True:
        result = inspector.list_doc_ids(limit=100, offset=offset)
        summaries = result.get("doc_ids", [])
        for s in summaries:
            all_docs.append({
                "doc_id": s["doc_id"],
                "title": s.get("title") or s.get("topic") or s["doc_id"],
                "tags": s.get("tags", []),
                "created_at": s.get("created_at", ""),
                "intent": s.get("intent"),
                "topic": s.get("topic"),
                "summary": "",
                "source_path": s.get("path", ""),
            })
        if not result.get("has_more"):
            break
        offset += len(summaries)
    all_docs.sort(key=lambda d: d["created_at"], reverse=True)
    return all_docs


def get_document(doc_id: str) -> dict:
    """Retrieve full document body and declared metadata.

    Metadata is filtered through QURO_NOTEBOOK_METADATA_SET so that
    only fields declared in the protocol are returned. See
    metadata_protocol.py for the design philosophy.
    """
    reader = MarkdownReader()
    result = reader.get(doc_id)
    if result.get("status") == "not_found":
        return {"doc_id": doc_id, "body": "", "meta": {}}

    raw_meta = result.get("meta", {}) or {}
    if isinstance(raw_meta, dict):
        meta = {k: v for k, v in raw_meta.items() if k in _DECLARED_KEYS}
    else:
        meta = {}

    return {
        "doc_id": result.get("doc_id", doc_id),
        "body": result.get("body", "") or "",
        "meta": meta,
    }
