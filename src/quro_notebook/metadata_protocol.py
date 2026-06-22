"""quro-doc metadata protocol — caller-side field declaration.

Design Philosophy
-----------------
quro-doc stores metadata as opaque key-value pairs. It does not interpret,
validate, or enforce metadata schema — callers declare their own
requirements via a metadata_set. quro-doc's MetadataInspector accepts
metadata_set as an optional parameter in get_metadata() and
list_metadata_keys() to filter and describe fields on behalf of the caller.

This module defines the metadata contract between quro-notebook (caller)
and quro-doc (callee). Each field declaration specifies what quro-notebook
expects to find in quro-doc document metadata, forming a protocol layer
that decouples caller requirements from callee storage.

Protocol Structure
------------------
Each entry in the metadata_set is a dict with:

    key         — metadata field name as stored in quro-doc
    description — human-readable field description for documentation
    domain      — value domain hint (e.g. "string", "array[string]", "object")
    map_to      — internal field name used within quro-notebook

This structure is the standard declaration format consumed by quro-doc's
MetadataInspector APIs. It is NOT an API-specific data structure — it is
a caller→callee protocol unit that travels across the boundary.

Maintenance
-----------
When quro-notebook requires a new metadata field from quro-doc, add an
entry here. When a field is no longer needed, remove it. This module
serves as the single source of truth for quro-notebook's metadata
requirements.
"""

from typing import Final

QURO_NOTEBOOK_METADATA_SET: Final[list[dict[str, str]]] = [
    {
        "key": "title",
        "description": "Document title — preferred display name for the article",
        "domain": "string",
        "map_to": "title",
    },
    {
        "key": "topic",
        "description": "Subject area or topic category of the document",
        "domain": "string",
        "map_to": "topic",
    },
    {
        "key": "intent",
        "description": "Purpose of the document (e.g. specification, analysis, how-to)",
        "domain": "string",
        "map_to": "intent",
    },
    {
        "key": "tags",
        "description": "List of categorization and search tags",
        "domain": "array[string]",
        "map_to": "tags",
    },
    {
        "key": "created_at",
        "description": "Document creation timestamp in ISO 8601 format",
        "domain": "string",
        "map_to": "created_at",
    },
    {
        "key": "path",
        "description": "Filesystem path to the original document source file",
        "domain": "string",
        "map_to": "source_path",
    },
    {
        "key": "source",
        "description": "Source provenance information for the document",
        "domain": "object",
        "map_to": "source",
    },
]
