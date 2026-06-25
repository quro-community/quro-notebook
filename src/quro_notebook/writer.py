import base64
import json
import os
import shutil
import urllib.error
from pathlib import Path
from typing import Any

from quro_notebook.assets import ASSET_MANIFEST, STYLE_FONT_MAP, fetch_asset
from quro_notebook.fetcher import (
    FetchError,
    fetch_minisearch,
    fetch_transformers_js,
    fetch_google_fonts_css,
    localize_google_fonts_css,
)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_index(index: dict[str, Any], output_dir: str) -> None:
    data_dir = Path(output_dir) / "data"
    _ensure_dir(data_dir)
    filepath = data_dir / "index.json"
    filepath.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def write_page(doc_id: str, html: str, output_dir: str) -> None:
    pages_dir = Path(output_dir) / "pages"
    _ensure_dir(pages_dir)
    filepath = pages_dir / f"{doc_id}.html"
    filepath.write_text(html, encoding="utf-8")


def write_embeddings(embeddings: dict[str, Any], output_dir: str) -> None:
    data_dir = Path(output_dir) / "data"
    _ensure_dir(data_dir)
    filepath = data_dir / "embeddings.json"
    filepath.write_text(json.dumps(embeddings, ensure_ascii=False), encoding="utf-8")


_cdn_cache: dict[str, str] | None = None


def _resolve_templates_dir() -> Path:
    package_root = Path(__file__).resolve().parent
    # Wheel install: templates bundled inside quro_notebook/templates/
    wheel_candidate = package_root / "templates"
    if wheel_candidate.is_dir():
        return wheel_candidate
    # Editable install / dev: templates at project root
    project_candidate = package_root.parent.parent / "templates"
    if project_candidate.is_dir():
        return project_candidate
    return project_candidate


def _cdn_replacements(asset_dir: Path, *, skip_fonts: bool = False, style_name: str = "default") -> dict[str, str]:
    global _cdn_cache
    cache_key = ("cdn", skip_fonts, style_name)
    if _cdn_cache is not None and _cdn_cache.get("_key") == cache_key:
        return _cdn_cache

    minisearch_js = asset_dir / "js" / "minisearch.min.js"
    transformers_js = asset_dir / "js" / "transformers.min.js"
    fonts_css = asset_dir / "css" / "fonts" / "google-fonts.css"
    style_fonts_css = asset_dir / "css" / "fonts" / f"google-fonts-{style_name}.css"

    replacements = {
        "minisearch_url": ASSET_MANIFEST["minisearch"],
        "transformers_url": ASSET_MANIFEST["transformers_js"],
        "google_fonts_url": "",
        "style_google_fonts_url": "",
        "_key": cache_key,
    }

    try:
        content = fetch_minisearch()
        _ensure_dir(minisearch_js.parent)
        minisearch_js.write_text(content, encoding="utf-8")
        replacements["minisearch_url"] = "assets/js/minisearch.min.js"
    except FetchError:
        pass

    try:
        content = fetch_transformers_js()
        _ensure_dir(transformers_js.parent)
        transformers_js.write_bytes(content)
        replacements["transformers_url"] = "transformers.min.js"
    except FetchError:
        pass

    if not skip_fonts:
        try:
            css = fetch_google_fonts_css()
            fonts_dir = asset_dir / "css" / "fonts"
            _ensure_dir(fonts_dir)
            localized_css, font_files = localize_google_fonts_css(css, "")
            fonts_css.write_text(localized_css, encoding="utf-8")
            for filename, data in font_files:
                (fonts_dir / filename).write_bytes(data)
            replacements["google_fonts_url"] = "fonts/google-fonts.css"
        except FetchError:
            pass

        if style_name != "default" and style_name in STYLE_FONT_MAP:
            try:
                style_css = fetch_asset(STYLE_FONT_MAP[style_name], timeout=10).decode("utf-8")
                fonts_dir = asset_dir / "css" / "fonts"
                _ensure_dir(fonts_dir)
                localized_css, font_files = localize_google_fonts_css(style_css, "")
                style_fonts_css.write_text(localized_css, encoding="utf-8")
                for filename, data in font_files:
                    dest = fonts_dir / filename
                    if not dest.exists():
                        dest.write_bytes(data)
                replacements["style_google_fonts_url"] = f"fonts/google-fonts-{style_name}.css"
            except (FetchError, urllib.error.URLError, OSError):
                pass

    _cdn_cache = replacements
    return replacements


def write_static_assets(output_dir: str, *, skip_fonts: bool = False, style_name: str = "default") -> None:
    templates_dir = _resolve_templates_dir()
    print(f"[write_static_assets] templates_dir={templates_dir} exists={templates_dir.is_dir()}")
    assets_dir = Path(output_dir) / "assets"
    _ensure_dir(assets_dir)

    replacements = _cdn_replacements(assets_dir, skip_fonts=skip_fonts, style_name=style_name)

    css_dir = assets_dir / "css"
    _ensure_dir(css_dir)
    js_dir = assets_dir / "js"
    _ensure_dir(js_dir)

    css_files = list(templates_dir.glob("*.css"))
    print(f"[write_static_assets] css_files={[f.name for f in css_files]}")
    for f in css_files:
        shutil.copy2(str(f), str(css_dir / f.name))

    js_files = list(templates_dir.glob("*.js"))
    print(f"[write_static_assets] js_files={[f.name for f in js_files]}")
    for f in js_files:
        shutil.copy2(str(f), str(js_dir / f.name))

    index_html = templates_dir / "index.html"
    print(f"[write_static_assets] index_html={index_html} exists={index_html.exists()}")
    if index_html.exists():
        shutil.copy2(str(index_html), str(Path(output_dir) / "index.html"))
    else:
        print("[write_static_assets] WARNING: index.html template not found, _output/index.html not created")

    for js_file in js_files:
        dest = js_dir / js_file.name
        text = dest.read_text(encoding="utf-8")
        text = text.replace("__TRANSFORMERS_URL__", replacements["transformers_url"])
        dest.write_text(text, encoding="utf-8")

    for css_file in css_files:
        dest = css_dir / css_file.name
        text = dest.read_text(encoding="utf-8")
        text = text.replace("__GOOGLE_FONTS_URL__", replacements["google_fonts_url"])
        dest.write_text(text, encoding="utf-8")

    style_src = templates_dir / "styles" / f"{style_name}.css"
    style_dest = css_dir / "style.css"
    if style_src.exists() and style_name != "default":
        text = style_src.read_text(encoding="utf-8")
        text = text.replace("__STYLE_GOOGLE_FONTS_URL__", replacements["style_google_fonts_url"])
        style_dest.write_text(text, encoding="utf-8")
    else:
        style_dest.write_text("/* " + style_name + " style — using theme.css defaults */\n", encoding="utf-8")

def write_index_html(output_dir: str, index: dict[str, Any], pages_html: dict[str, str], *, skip_fonts: bool = False, style_name: str = "default") -> None:
    templates_dir = _resolve_templates_dir()
    template_path = templates_dir / "index.html"
    print(f"[write_index_html] templates_dir={templates_dir} exists={templates_dir.is_dir()}")
    print(f"[write_index_html] template_path={template_path} exists={template_path.exists()}")

    if template_path.exists():
        html = template_path.read_text(encoding="utf-8")
        print("[write_index_html] read template from source")
    else:
        index_path = Path(output_dir) / "index.html"
        print(f"[write_index_html] template not found, checking fallback: index_path={index_path} exists={index_path.exists()}")
        if not index_path.exists():
            print("[write_index_html] WARNING: no template and no fallback, index.html not written")
            return
        html = index_path.read_text(encoding="utf-8")
        print("[write_index_html] read template from fallback (_output/index.html)")

    index_json = json.dumps(index, ensure_ascii=False)
    html = html.replace("__QURO_INDEX_DATA__", index_json)

    project_display = os.path.basename(str(index.get("project", "")).rstrip("/")) or "Notebook"
    html = html.replace("__QURO_PROJECT_NAME__", project_display)

    fragments = []
    for doc_id, page_html in pages_html.items():
        b64 = base64.b64encode(page_html.encode("utf-8")).decode("ascii")
        fragments.append(f'<script type="text/x-quro-page" id="quro-page-{doc_id}" data-encoding="base64">{b64}</script>')
    html = html.replace("__QURO_PAGE_FRAGMENTS__", "\n".join(fragments))

    replacements = _cdn_replacements(Path(output_dir) / "assets", skip_fonts=skip_fonts, style_name=style_name)
    html = html.replace("__MINISEARCH_URL__", replacements["minisearch_url"])

    _ensure_dir(Path(output_dir))
    index_path = Path(output_dir) / "index.html"
    index_path.write_text(html, encoding="utf-8")


def write_config(config: dict[str, Any], output_dir: str) -> None:
    data_dir = Path(output_dir) / "data"
    _ensure_dir(data_dir)
    filepath = data_dir / "config.json"
    filepath.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
