import json
import urllib.request
from datetime import datetime


def _encode_via_api(text: str, api_url: str, model_name: str, timeout: int = 60) -> list[float]:
    payload = json.dumps({"input": text, "model": model_name}).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["data"][0]["embedding"]


def _encode_via_local(model, text: str) -> list[float]:
    return model.encode(text).tolist()


def _is_url(model_name: str) -> bool:
    return model_name.startswith("http://") or model_name.startswith("https://")


def generate_embeddings(
    documents: list[dict],
    model_name: str,
    api_url: str = "",
) -> dict:
    use_api = bool(api_url) if api_url else _is_url(model_name)
    local_model = None

    if not use_api:
        from sentence_transformers import SentenceTransformer
        local_model = SentenceTransformer(model_name)

    docs: list[dict] = []
    dim = 0

    for doc in documents:
        doc_id = doc.get("doc_id", "")
        body = doc.get("body", "") or ""
        title = doc.get("title", "")

        if use_api:
            endpoint = api_url or model_name
            embedding = _encode_via_api(body, endpoint, model_name if api_url else "default")
        else:
            embedding = _encode_via_local(local_model, body)

        if dim == 0:
            dim = len(embedding)

        docs.append({
            "doc_id": doc_id,
            "title": title,
            "embedding": embedding,
        })

    display_model = api_url if use_api else model_name

    return {
        "model": display_model,
        "dim": dim,
        "docs": docs,
        "build_time": datetime.utcnow().isoformat() + "Z",
        "schema_version": "1.0.0",
    }
