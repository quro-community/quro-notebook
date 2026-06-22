"""quro-notebook CLI — unified entry point with subcommands."""

import argparse
import os
import sys

DEFAULT_STORAGE_ROOT = os.getcwd()


def _load_env() -> None:
    """Load .env files matching quro-doc's config loading order.

    quro-doc loads .env from two locations (in order):
    1. CWD .env — cli/__init__.py:36
    2. quro-doc package root .env — config.py:102-107

    python-dotenv does NOT override already-set env vars, so whichever
    runs first wins. We follow the same order so that quro-notebook
    and quro-doc derive QURO_STORAGE_ROOT from the same source.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    cwd_env = os.path.join(os.getcwd(), ".env")
    if os.path.exists(cwd_env):
        load_dotenv(cwd_env)

    import quro_doc
    pkg_root = os.path.abspath(os.path.join(
        os.path.dirname(quro_doc.__file__), "..", ".."
    ))
    pkg_env = os.path.join(pkg_root, ".env")
    if os.path.exists(pkg_env) and os.path.abspath(pkg_env) != os.path.abspath(cwd_env):
        load_dotenv(pkg_env)


def resolve_storage_root(project: str | None) -> str:
    base = os.environ.get("QURO_STORAGE_ROOT", DEFAULT_STORAGE_ROOT)
    if project:
        project_segment = os.path.join("projects", project)
        if base.endswith(project_segment):
            root = base
        else:
            root = os.path.join(base, "projects", project)
    else:
        root = base
    os.environ["QURO_STORAGE_ROOT"] = root
    return root


def _cmd_build(args: argparse.Namespace) -> None:
    from quro_notebook.build import build

    root = resolve_storage_root(args.project)
    project_root = args.project_root or root
    output_dir = args.output_dir or os.path.join(project_root, "_output")

    print(f"QURO_STORAGE_ROOT: {root}")
    print(f"Output directory: {output_dir}")

    build(
        project_root=project_root,
        output_dir=output_dir,
        project=args.project,
        model_name=args.model_name,
        skip_embeddings=args.skip_embeddings,
        embed_api_url=args.embed_api or "",
        quro_search_url=args.quro_search or "",
        no_fonts=args.no_fonts,
        style_name=args.style,
    )
    print(f"Build complete: {output_dir}")


def _cmd_fetch_assets(args: argparse.Namespace) -> None:
    from quro_notebook.assets import ASSET_MANIFEST, fetch_all_assets, is_asset_cached

    if args.list:
        for name, url in ASSET_MANIFEST.items():
            cached = " [cached]" if is_asset_cached(url) else ""
            print(f"{name}: {url}{cached}")
    else:
        errors = fetch_all_assets()
        if errors:
            print(f"\n{len(errors)} asset(s) failed to fetch (blocked or unreachable):")
            for name, err in errors:
                print(f"  [{name}] {err}")
            print("Build will proceed without these assets.")
        else:
            print("All assets cached.")


def _cmd_search_server(args: argparse.Namespace) -> None:
    resolve_storage_root(args.project)
    from quro_notebook.search_server import run_server

    run_server(args.port)


def main() -> None:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    _load_env()

    parser = argparse.ArgumentParser(
        prog="quro-notebook",
        description="Static site generator that builds a searchable notebook from quro-doc documents",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Project namespace for multi-tenant setups (sets QURO_STORAGE_ROOT to .../projects/<name>)",
    )

    sub = parser.add_subparsers(dest="command")

    p_build = sub.add_parser("build", help="Build the static notebook site")
    p_build.add_argument("project_root", nargs="?", help="Project root directory (default: QURO_STORAGE_ROOT)")
    p_build.add_argument("output_dir", nargs="?", help="Output directory (default: <project_root>/_output)")
    p_build.add_argument("--model-name", default="BAAI/bge-small-en-v1.5", help="Embedding model name or URL")
    p_build.add_argument("--skip-embeddings", action="store_true", help="Skip embedding generation")
    p_build.add_argument("--embed-api", help="Embedding API endpoint URL")
    p_build.add_argument("--quro-search", dest="quro_search", help="Quro search API URL for config.json")
    p_build.add_argument("--no-fonts", action="store_true", help="Skip Google Fonts download")
    p_build.add_argument("--style", default="default", help="Visual style: 'default' or 'warm-editorial' (default: default)")

    p_fetch = sub.add_parser("fetch-assets", help="Pre-fetch CDN assets")
    p_fetch.add_argument("--list", action="store_true", help="Show cached status of each asset")

    p_search = sub.add_parser("search-server", help="Run the HTTP search bridge")
    p_search.add_argument("--port", type=int, default=8765, help="Port to listen on (default: 8765)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "build":
        _cmd_build(args)
    elif args.command == "fetch-assets":
        _cmd_fetch_assets(args)
    elif args.command == "search-server":
        _cmd_search_server(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
