import re
import sys
from datetime import datetime, timezone

from quro_notebook.reader import list_documents, get_document
from quro_notebook.renderer import render_page
try:
    from quro_notebook.embedder import generate_embeddings
    _embedder_available = True
except ImportError:
    generate_embeddings = None
    _embedder_available = False
from quro_notebook.writer import (
    write_index,
    write_page,
    write_embeddings,
    write_static_assets,
    write_config,
    write_index_html,
)
from quro_notebook.schemas import SCHEMA_VERSION


def _resolve_title(full_doc: dict, body: str, topic: str | None, doc_id: str) -> str:
    meta = full_doc.get("meta", {})
    if isinstance(meta, dict):
        title = meta.get("title")
        if title and str(title).strip():
            return str(title).strip()

    if body:
        m = re.match(r'^#\s+(.+)$', body, re.MULTILINE)
        if m:
            return m.group(1).strip()

    if topic:
        return topic

    return doc_id


def build(
    project_root: str,
    output_dir: str,
    project: str | None = None,
    model_name: str = "BAAI/bge-small-en-v1.5",
    skip_embeddings: bool = False,
    embed_api_url: str = "",
    quro_search_url: str = "",
    no_fonts: bool = False,
    style_name: str = "default",
) -> None:
    docs = list_documents(project_root)

    pages = []
    pages_html: dict[str, str] = {}
    for entry in docs:
        doc_id = entry["doc_id"]
        full_doc = get_document(doc_id)
        body = full_doc.get("body", "") or ""

        source_path = entry.get("source_path", "")

        title = _resolve_title(full_doc, body, entry.get("topic"), doc_id)
        entry["title"] = title

        metadata = {
            "doc_id": doc_id,
            "title": title,
            "created_at": entry["created_at"],
            "intent": entry.get("intent"),
            "tags": entry.get("tags", []),
            "source_path": source_path,
        }

        html = render_page(body, metadata)
        write_page(doc_id, html, output_dir)
        pages_html[doc_id] = html

        pages.append(entry)

    build_time = datetime.now(timezone.utc).isoformat()

    index = {
        "project": project or project_root,
        "pages": pages,
        "total_count": len(pages),
        "build_time": build_time,
        "schema_version": SCHEMA_VERSION,
    }
    write_index(index, output_dir)

    if not skip_embeddings and _embedder_available:
        try:
            documents_for_embedding = [
                {"doc_id": p["doc_id"], "title": p["title"], "body": get_document(p["doc_id"])["body"]}
                for p in pages
            ]
            embeddings = generate_embeddings(documents_for_embedding, model_name, api_url=embed_api_url)
            write_embeddings(embeddings, output_dir)
        except Exception as e:
            print(f"Warning: embedding generation skipped ({e})")

    config = {
        "quro_search_url": quro_search_url if quro_search_url else None,
        "build_time": build_time,
    }
    write_config(config, output_dir)

    write_static_assets(output_dir, skip_fonts=no_fonts, style_name=style_name)
    write_index_html(output_dir, index, pages_html, skip_fonts=no_fonts)


def main() -> None:
    from quro_notebook.cli import _load_env

    _load_env()

    if len(sys.argv) < 3:
        print("Usage: python -m quro_notebook.build <project_root> <output_dir> [model_name] [--embed-api URL] [--skip-embeddings] [--no-fonts] [--quro-search URL] [--style NAME]")
        sys.exit(1)

    project_root = sys.argv[1]
    output_dir = sys.argv[2]

    model_name = "BAAI/bge-small-en-v1.5"
    skip_embeddings = False
    embed_api_url = ""
    quro_search_url = ""
    no_fonts = False
    style_name = "default"

    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--embed-api" and i + 1 < len(args):
            embed_api_url = args[i + 1]
            i += 2
        elif args[i] == "--quro-search" and i + 1 < len(args):
            quro_search_url = args[i + 1]
            i += 2
        elif args[i] == "--skip-embeddings":
            skip_embeddings = True
            i += 1
        elif args[i] == "--no-fonts":
            no_fonts = True
            i += 1
        elif args[i] == "--style" and i + 1 < len(args):
            style_name = args[i + 1]
            i += 2
        else:
            model_name = args[i]
            i += 1

    build(project_root, output_dir, model_name=model_name, skip_embeddings=skip_embeddings,
          embed_api_url=embed_api_url, quro_search_url=quro_search_url, no_fonts=no_fonts,
          style_name=style_name)
    print(f"Build complete: {output_dir}")


if __name__ == "__main__":
    main()
