import hashlib
import os
import re
import urllib.request
import urllib.error
from pathlib import Path

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_FONT_URL_RE = re.compile(r"url\((https://fonts\.gstatic\.com/[^)]+)\)")

ASSET_MANIFEST: dict[str, str] = {
    "minisearch": "https://cdn.jsdelivr.net/npm/minisearch@7.1.2/dist/umd/index.min.js",
    "transformers_js": "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.5.0/dist/transformers.min.js",
    "google_fonts_css": (
        "https://fonts.googleapis.com/css2"
        "?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;0,6..72,700;1,6..72,400"
        "&family=Roboto:wght@300;400;500;700"
        "&family=JetBrains+Mono:wght@400;500"
        "&display=swap"
    ),
}

STYLE_FONT_MAP: dict[str, str] = {
    "default": ASSET_MANIFEST["google_fonts_css"],
    "warm-editorial": (
        "https://fonts.googleapis.com/css2"
        "?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700"
        "&family=JetBrains+Mono:wght@400;500"
        "&display=swap"
    ),
}


def get_cache_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    cache_dir = base / "quro-notebook" / "cdn"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def fetch_asset(url: str, timeout: int = 15) -> bytes:
    cache_file = get_cache_dir() / _url_hash(url)
    if cache_file.exists():
        return cache_file.read_bytes()

    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()

    cache_file.write_bytes(data)
    return data


def is_asset_cached(url: str) -> bool:
    return (get_cache_dir() / _url_hash(url)).exists()


def fetch_all_assets() -> list[tuple[str, str]]:
    errors: list[tuple[str, str]] = []
    font_file_urls: set[str] = set()
    for name, url in ASSET_MANIFEST.items():
        print(f"[{name}] {url}")
        try:
            data = fetch_asset(url)
            print(f"  -> {len(data)} bytes")
        except (urllib.error.URLError, OSError) as e:
            errors.append((name, str(e)))
            continue

        if name == "google_fonts_css":
            css = data.decode("utf-8")
            for font_url in _FONT_URL_RE.findall(css):
                if font_url not in font_file_urls:
                    font_file_urls.add(font_url)
                    filename = font_url.rsplit("/", 1)[-1]
                    print(f"  [font] {filename}")
                    try:
                        fetch_asset(font_url)
                    except (urllib.error.URLError, OSError) as e:
                        errors.append((f"font:{filename}", str(e)))
    return errors


def main() -> None:
    import sys
    if "--list" in sys.argv:
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


if __name__ == "__main__":
    main()
