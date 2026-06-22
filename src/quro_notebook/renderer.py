import re
import html as html_mod
from datetime import datetime
from mistune import create_markdown
from jinja2 import Template

PAGE_TEMPLATE = Template("""\
<article class="notebook-page" data-doc-id="{{ doc_id }}">
  <header class="page-header">
    <h1 class="page-title">{{ title }}</h1>
    <div class="page-meta">
      <time datetime="{{ created_at }}">{{ formatted_date }}</time>
      {% if intent %}<span class="page-intent">{{ intent }}</span>{% endif %}
    </div>
    {% if tags %}
    <div class="page-tags">
      {% for tag in tags %}<span class="tag">{{ tag }}</span>{% endfor %}
    </div>
    {% endif %}
    {% if toc_html %}
    <nav class="page-toc" aria-label="Table of contents">
      {{ toc_html }}
    </nav>
    {% endif %}
  </header>
	  <div class="page-actions">
	    {% if source_path %}
	    <a class="btn-edit" href="vscode://file/{{ source_path }}" title="Open source file in VS Code">
	      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
	      Edit
	    </a>
	    {% endif %}
	    <button class="btn-ask-ai" data-doc-id="{{ doc_id }}" title="Copy article content for AI chat">
	      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
	      Ask AI
	    </button>
	  </div>
  <div class="page-body markdown-body">
    {{ body_html }}
  </div>
</article>""")

_markdown_renderer = create_markdown(
    escape=False,
    plugins=["strikethrough", "table", "task_lists", "def_list"],
)


def _build_toc(body_markdown: str) -> str:
    heading_pattern = re.compile(r'^(#{2,3})\s+(.+)$', re.MULTILINE)
    items: list[dict] = []
    for m in heading_pattern.finditer(body_markdown):
        level = len(m.group(1))
        text = m.group(2).strip()
        slug = _slugify(text)
        items.append({"level": level, "text": text, "slug": slug})

    if len(items) < 2:
        return ""

    parts = ['<ol class="toc-list">']
    stack = [1]
    for item in items:
        level = item["level"]
        while level > stack[-1]:
            parts.append('<ol>')
            stack.append(level)
        while level < stack[-1]:
            parts.append('</ol></li>')
            stack.pop()
        parts.append(
            f'<li class="toc-item toc-h{level}">'
            f'<a href="#{item["slug"]}">{html_mod.escape(item["text"])}</a>'
        )
    while len(stack) > 1:
        parts.append('</ol></li>')
        stack.pop()
    parts.append('</ol>')
    return "".join(parts)


def _slugify(text: str) -> str:
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[\s]+', '-', slug)
    return slug.strip('-')


def _add_heading_ids(html_str: str, body_markdown: str) -> str:
    heading_map: dict[str, str] = {}
    heading_pattern = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
    for m in heading_pattern.finditer(body_markdown):
        heading_map[m.group(2).strip()] = _slugify(m.group(2).strip())

    def replacer(m: re.Match) -> str:
        tag = m.group(1)
        attrs = m.group(2)
        inner = m.group(3)
        text = re.sub(r'<[^>]+>', '', inner).strip()
        slug = heading_map.get(text)
        if slug:
            return f'<{tag} id="{slug}"{attrs}>{inner}</{tag}>'
        return m.group(0)

    heading_re = re.compile(r'<(h[1-3])([^>]*)>(.+?)</\1>', re.DOTALL)
    return heading_re.sub(replacer, html_str)


def _format_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y")
    except (ValueError, TypeError):
        return date_str[:10] if len(date_str) >= 10 else date_str


def render_page(body_markdown: str, metadata: dict) -> str:
    title = metadata.get("title", "Untitled")
    doc_id = metadata.get("doc_id", "")
    created_at = metadata.get("created_at", "")
    intent = metadata.get("intent")
    tags = metadata.get("tags", [])
    source_path = metadata.get("source_path", "")

    body_html = _markdown_renderer(body_markdown)
    body_html = _add_heading_ids(body_html, body_markdown)

    toc_html = _build_toc(body_markdown)
    formatted_date = _format_date(created_at)

    return PAGE_TEMPLATE.render(
        doc_id=doc_id,
        title=title,
        created_at=created_at,
        formatted_date=formatted_date,
        intent=intent,
        tags=tags,
        source_path=source_path,
        toc_html=toc_html,
        body_html=body_html,
    )
