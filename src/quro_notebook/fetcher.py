import re
import urllib.request
import urllib.error

from quro_notebook.assets import ASSET_MANIFEST, fetch_asset, is_asset_cached

_FONT_URL_RE = re.compile(r"url\((https://fonts\.gstatic\.com/[^)]+)\)")


class FetchError(Exception):
    pass


def fetch_minisearch() -> str:
    try:
        return fetch_asset(ASSET_MANIFEST["minisearch"], timeout=30).decode("utf-8")
    except (urllib.error.URLError, OSError, KeyError) as e:
        raise FetchError(f"Failed to download MiniSearch: {e}") from e


def fetch_transformers_js() -> bytes:
    try:
        return fetch_asset(ASSET_MANIFEST["transformers_js"], timeout=60)
    except (urllib.error.URLError, OSError, KeyError) as e:
        raise FetchError(f"Failed to download Transformers.js: {e}") from e


def fetch_google_fonts_css() -> str:
    try:
        return fetch_asset(ASSET_MANIFEST["google_fonts_css"], timeout=10).decode("utf-8")
    except (urllib.error.URLError, OSError, KeyError) as e:
        raise FetchError(f"Failed to download Google Fonts CSS: {e}") from e


def fetch_font_file(url: str) -> bytes:
    try:
        return fetch_asset(url, timeout=30)
    except (urllib.error.URLError, OSError) as e:
        raise FetchError(f"Failed to download font file {url}: {e}") from e


def localize_google_fonts_css(css: str, font_dir: str) -> tuple[str, list[tuple[str, bytes]]]:
    fonts: list[tuple[str, bytes]] = []

    def _replace_url(match: re.Match) -> str:
        font_url = match.group(1)
        filename = font_url.rsplit("/", 1)[-1]
        try:
            data = fetch_font_file(font_url)
        except FetchError:
            return match.group(0)
        fonts.append((filename, data))
        return f"url('{font_dir}{filename}')"

    localized_css = _FONT_URL_RE.sub(_replace_url, css)
    return localized_css, fonts
