import json
from pathlib import Path

from quro_doc.ext.inspector import MetadataInspector
from quro_doc.ext.reader import MarkdownReader
from quro_doc.storage import get_storage_root

from quro_notebook.metadata_protocol import QURO_NOTEBOOK_METADATA_SET

_DECLARED_KEYS = frozenset(item["key"] for item in QURO_NOTEBOOK_METADATA_SET)


def _unwrap_meta(raw_meta: dict) -> dict:
    """Unwrap quro-doc's double-wrapped meta structure.

    quro-doc stores metadata as {"meta": {"title": ..., "topic": ...}}
    in the JSON file, and read_raw_doc() returns the whole file content
    as the result["meta"] value.  We need the inner dict.
    """
    if isinstance(raw_meta, dict) and "meta" in raw_meta:
        inner = raw_meta["meta"]
        if isinstance(inner, dict):
            return inner
    return raw_meta


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


def _find_doc_on_filesystem(doc_id: str) -> dict | None:
    """Fallback: search subdirectories for documents not in root docs/.

    quro_doc's read_raw_doc() only looks in docs/ and raw/ at the
    storage root, but project documents are nested in subdirectories
    like projects/<name>/docs/.  Walk the full storage tree to find
    the JSON + TXT pair.
    """
    root = Path(get_storage_root())
    matches = list(root.rglob(f"{doc_id}.json"))
    if not matches:
        return None
    json_path = matches[0]
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    txt_path = json_path.parent / f"{doc_id}.txt"
    body = ""
    if txt_path.exists():
        try:
            body = txt_path.read_text(encoding="utf-8")
        except Exception:
            pass
    return {"doc_id": doc_id, "body": body, "meta": data}


def get_document(doc_id: str) -> dict:
    """Retrieve full document body and declared metadata.

    Metadata is filtered through QURO_NOTEBOOK_METADATA_SET so that
    only fields declared in the protocol are returned. See
    metadata_protocol.py for the design philosophy.
    """
    reader = MarkdownReader()
    result = reader.get(doc_id)
    if result.get("status") == "not_found":
        result = _find_doc_on_filesystem(doc_id) or {}

    raw_meta = result.get("meta", {}) or {}
    raw_meta = _unwrap_meta(raw_meta)
    if isinstance(raw_meta, dict):
        meta = {k: v for k, v in raw_meta.items() if k in _DECLARED_KEYS}
    else:
        meta = {}

    return {
        "doc_id": result.get("doc_id", doc_id),
        "body": result.get("body", "") or "",
        "meta": meta,
    }
