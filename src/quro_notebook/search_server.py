"""
Standalone HTTP bridge for quro-doc semantic search.

Usage:
    python -m quro_notebook.search_server --port 8765

Then configure the notebook to use it:
    search.js reads QURO_SEARCH_URL from config.json (or discovers it).

The bridge is stateless — each POST /search is an independent quro_doc_search() call.
"""

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

from quro_doc.api import quro_doc_search


class SearchHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/search":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400)
            return

        query = request.get("query", "")
        top_k = request.get("top_k", 10)

        result = quro_doc_search({"query": query, "top_k": top_k})

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass


def run_server(port: int = 8765) -> None:
    server = HTTPServer(("127.0.0.1", port), SearchHandler)
    print(f"quro-doc search bridge: http://127.0.0.1:{port}/search")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


def main() -> None:
    port = 8765
    if len(sys.argv) > 2 and sys.argv[1] == "--port":
        port = int(sys.argv[2])

    run_server(port)


if __name__ == "__main__":
    main()
