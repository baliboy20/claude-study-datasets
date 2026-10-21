"""Helpers for the HTML documents: page shell, header band, tables and the standard footer.

Every page links docs/theme.css (copied there by the build from generator/common/theme.css).
"""

import re
from html import escape

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800'
         '&amp;family=JetBrains+Mono:wght@400;600&amp;display=swap" rel="stylesheet">')

HEAD_LINKS = FONTS + '\n<link rel="stylesheet" href="theme.css">'

# The landing page is index.html at the project root. The dataset's Worker serves documents at addresses
# without .html (such as /docs/about) and cannot reach the landing page, so the link is removed there.
LANDING_SCRIPT = (r"<script>if (!/\.html$/.test(location.pathname)) document.querySelectorAll('[data-landing]')"
                  r".forEach(function (a) { a.remove() })</script>")

_LEADING = re.compile(
    r'^\s*(<h1>.*?</h1>)((?:\s*(?:<p class="lead">.*?</p>|<p><span class="status[^"]*">.*?</span></p>'
    r'|<nav class="toc">.*?</nav>))*)', re.S)


def e(x):
    return escape("" if x is None else str(x))


def masthead(dataset_title, doc_label, inner):
    crumbs = (f'<div class="crumbs"><a data-landing href="../../../index.html">All datasets</a>'
              f'<span>›</span><span>{e(dataset_title)}</span><span>›</span><span>{e(doc_label)}</span></div>')
    return f'<header class="masthead"><div class="wrap">{crumbs}{inner}</div></header>'


def split_masthead(body):
    """Moves the leading title, lead, status and contents links of a page body into the header band."""
    m = _LEADING.match(body)
    if not m:
        return "", body
    return m.group(1) + m.group(2), body[m.end():]


def table(headers, rows, num_cols=()):
    head = "".join(f"<th>{e(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f'<td class="num">{c}</td>' if i in num_cols else f"<td>{c}</td>" for i, c in enumerate(r)) + "</tr>"
        for r in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def footer(name, version, date, purpose, dataset):
    """Standard footer for every document: name, version, date, purpose, dataset."""
    rows = [("Document", name), ("Version", version), ("Date", date), ("Purpose", purpose), ("Dataset", dataset)]
    items = "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in rows)
    return f'<footer class="doc-footer"><dl>{items}</dl></footer>'


def md_footer(name, version, date, purpose, dataset):
    """The same footer for Markdown documents."""
    return ("\n\n---\n\n"
            f"| Document | Version | Date | Purpose | Dataset |\n|---|---|---|---|---|\n"
            f"| {name} | {version} | {date} | {purpose} | {dataset} |\n")


def page(title, body, foot="", dataset_title="", doc_label=""):
    head_inner, rest = split_masthead(body)
    band = masthead(dataset_title, doc_label, head_inner) if head_inner else ""
    return (f'<!doctype html>\n<html lang="en-GB">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>{e(title)}</title>\n'
            f"{HEAD_LINKS}\n</head>\n<body>\n{band}\n<main>\n{rest}\n</main>\n{foot}\n{LANDING_SCRIPT}\n</body>\n</html>\n")
