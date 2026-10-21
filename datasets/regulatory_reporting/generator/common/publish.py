"""Final publishing step, run by generator/build.py after the dataset's own write_docs.

It makes a dataset readable wherever a reader meets it:
  - marks every answer file with the canary (see dataset.CANARY);
  - writes an HTML version of each Markdown document, so pages work when downloaded or on GitHub Pages
    (the .md files stay: GitHub renders them and AI tools read them);
  - links the HTML versions from docs/about.html;
  - writes the dataset's README.md, which GitHub shows when a reader opens the folder.
"""

import json
import os
import re
from html import escape

from generator.common import firm
from generator.common.dataset import CANARY
from generator.common.html import footer, page

# Markdown documents that get an HTML version: (path in the dataset, label in the header band).
MARKDOWN_DOCS = [
    ("docs/spec.md", "Specification"),
    ("docs/planted-cases.md", "Planted cases"),
    ("packs/ai-eval/prompts.md", "Test questions"),
]
# Files that hold answers, or test items whose leak would spoil a test. Each must carry the canary.
CANARY_FILES = ["docs/planted-cases.md", "packs/ai-eval/prompts.md", "packs/ai-eval/expected-answers.json"]


# ------------------------------------------------------------------ canary

def add_canary(root):
    for rel in CANARY_FILES:
        path = os.path.join(root, rel)
        if rel.endswith(".json"):
            data = json.load(open(path, encoding="utf-8"))
            if isinstance(data, list):
                data = {"canary": CANARY, "questions": data}
            data["canary"] = CANARY
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            continue
        text = open(path, encoding="utf-8").read()
        if CANARY in text:
            continue
        first, _, rest = text.partition("\n")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{first}\n\n> {CANARY}\n{rest}")


def canary_errors(root):
    errors = []
    for rel in CANARY_FILES:
        path = os.path.join(root, rel)
        if not os.path.exists(path) or CANARY not in open(path, encoding="utf-8").read():
            errors.append(f"canary missing from {rel}")
    return errors


# ------------------------------------------------------------------ Markdown to HTML

def _inline(text):
    """Escapes text, then applies `code`, **bold**, *italic* and [links](url)."""
    parts = re.split(r"(`[^`]+`)", text)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            out.append(f"<code>{escape(part[1:-1])}</code>")
            continue
        s = escape(part, quote=False)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
        out.append(s)
    return "".join(out)


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def md_to_html(md):
    """Converts the Markdown the generators write: headings, paragraphs, lists, tables, quotes, code blocks, rules."""
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>" + escape("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
        elif re.match(r"^#{1,6} ", line):
            level = len(line) - len(line.lstrip("#"))
            out.append(f"<h{level}>{_inline(line[level:].strip())}</h{level}>")
            i += 1
        elif line.strip() == "---":
            out.append("<hr>")
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            head, body = rows[0], [r for r in rows[1:] if not re.match(r"^\|[\s:|-]+\|$", r.strip())]
            th = "".join(f"<th>{_inline(c)}</th>" for c in _cells(head))
            tb = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in _cells(r)) + "</tr>" for r in body)
            out.append(f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>')
        elif line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip(">").strip())
                i += 1
            out.append(f'<div class="note">{_inline(" ".join(quote))}</div>')
        elif re.match(r"^(- |\d+\. )", line):
            ordered = bool(re.match(r"^\d+\. ", line))
            items = []
            while i < len(lines) and re.match(r"^(- |\d+\. |  +\S)", lines[i]):
                item = re.sub(r"^(- |\d+\. )", "", lines[i])
                if lines[i].startswith("  ") and items:
                    items[-1] += " " + item.strip()
                else:
                    items.append(item)
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + f"</{tag}>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,6} |```|\||>|- |\d+\. |---$)", lines[i]):
                para.append(lines[i].strip())
                i += 1
            out.append(f"<p>{_inline(' '.join(para))}</p>")
    return "\n".join(out)


_MD_FOOTER = re.compile(r"\n---\s*\n+\| Document \| Version \| Date \| Purpose \| Dataset \|\n\|[-|]+\|\n\| (.+?) \|\s*$", re.S)


def write_html_versions(root, dataset_title):
    for rel, label in MARKDOWN_DOCS:
        path = os.path.join(root, rel)
        md = open(path, encoding="utf-8").read()
        foot = ""
        m = _MD_FOOTER.search(md)
        if m:
            name, version, date, purpose, dataset = [c.strip() for c in m.group(1).split(" | ")]
            md = md[:m.start()]
            foot = footer(os.path.basename(rel)[:-3] + ".html", version, date, purpose, dataset)
        body = md_to_html(md)
        title = re.search(r"<h1>(.*?)</h1>", body)
        html = page(re.sub(r"<[^>]+>", "", title.group(1)) if title else label, body, foot, dataset_title, label)
        # Pages outside docs/ point back to docs/theme.css and to the landing page from where they sit.
        if not rel.startswith("docs/"):
            ups = rel.count("/")  # folders between the page and the dataset folder
            html = html.replace('href="theme.css"', 'href="' + "../" * ups + 'docs/theme.css"')
            html = html.replace('href="../../../index.html"', 'href="' + "../" * (ups + 2) + 'index.html"')
        with open(path[:-3] + ".html", "w", encoding="utf-8") as f:
            f.write(html)


def link_html_versions(root):
    """In docs/about.html, links each mention of a Markdown document to its HTML version."""
    path = os.path.join(root, "docs", "about.html")
    html = open(path, encoding="utf-8").read()
    targets = {"docs/spec.md": "spec.html", "docs/planted-cases.md": "planted-cases.html",
               "packs/ai-eval/prompts.md": "../packs/ai-eval/prompts.html"}
    for rel, href in targets.items():
        html = re.sub(rf"(?<!\">)<code>{re.escape(rel)}</code>(?!</a>)", f'<a href="{href}"><code>{rel}</code></a>', html)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


# ------------------------------------------------------------------ README.md

def _port(root):
    m = re.search(r"^port = (\d+)", open(os.path.join(root, "api", "wrangler.toml"), encoding="utf-8").read(), re.M)
    return m.group(1) if m else "?"


def write_readme(con, root, release):
    name = os.path.basename(root)
    facts = dict(con.execute("SELECT key, value FROM _meta_dataset"))
    tables = con.execute("SELECT table_name, row_count, description FROM _meta_tables "
                         "WHERE kind IN ('business', 'lookup') ORDER BY kind, table_name").fetchall()
    genuine, benign = con.execute("SELECT sum(classification = 'Genuine exception'), sum(classification = 'Benign lookalike') "
                                  "FROM _truth_cases").fetchone()
    port = _port(root)
    online = f"{firm.SITE_URL.rstrip('/')}/datasets/{name}/docs/about.html" if firm.SITE_URL else ""
    start = (f"- **Online:** [{release.TITLE}]({online})\n" if online else "") + \
        "- **Downloaded:** open `docs/about.html` in a browser, or `index.html` at the project root for every dataset."
    rows = "\n".join(f"| `{t}` | {n} | {d} |" for t, n, d in tables)
    text = f"""# {release.TITLE}

{facts.get('scenario', '')} {facts.get('period', '')}. The data is synthetic: every person, firm and account is fictional.

It holds {genuine + benign} planted cases: {genuine} genuine problems and {benign} records that look suspicious but are legitimate. The test asks whether an AI can find the first without flagging the second.

## Start here

{start}

## What is in this folder

| Folder | Holds |
|---|---|
| `docs/` | The documents: `about.html` (start here), `spec.html` (the data and its rules, no answers), `planted-cases.html` (the answers, for reviewers), `roles.html`, `method.html`, `appraisal-types.html` |
| `db/` | The data: `{name}.sqlite` (open with any SQLite tool) and `seed.sql` (the same data as SQL) |
| `packs/ai-eval/` | Test questions (`prompts.md`) and expected answers (`expected-answers.json`) |
| `generator/` | The Python code that builds the data and documents. `build.py` is the one to run |
| `api/` | A small local web server for the data: a JSON API and a data browser |

## Tables

| Table | Rows | Holds |
|---|---|---|
{rows}

The full data dictionary is in `docs/spec.html`.

## Commands

You need Python 3.10 or later for the build, and Node.js 20 or later for the local server.

| Step | Run from | Command | What it does |
|---|---|---|---|
| 1. Rebuild the data (optional) | this folder | `python3 generator/build.py` | Regenerates `db/` and the documents from the code, runs every check, and prints a checksum. The data is already built, so you only need this after changing the code |
| 2. Install the server | `api/` | `npm install` | Downloads the web server's dependencies, once |
| 3. Load the data | `api/` | `npm run load` | Copies `db/seed.sql` into the server's local database |
| 4. Run the server | `api/` | `npm run dev` | Starts the data browser at http://localhost:{port}/ui and the JSON API at http://localhost:{port} |

The data browser has three roles. `public` sees the data; `analyst` adds the rules and data dictionary; `reviewer` adds the answers. The role keys are in `api/.dev.vars`, which is created from `api/.dev.vars.example` the first time you run step 3 or 4. They are example keys for local use only.

## Licence and test data

Data and documents: CC BY 4.0. Code: MIT. See `LICENSE-DATA.md` and `LICENSE` at the project root.

The answer files carry this marker so that AI developers can keep them out of training data:

> {CANARY}

---

| Document | Version | Date | Purpose | Dataset |
|---|---|---|---|---|
| README.md | {release.VERSION} | {release.RELEASE_DATE} | Explains what this folder holds and how to build and run the dataset | {release.TITLE} |
"""
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(text)


def publish(con, root, release):
    add_canary(root)
    write_html_versions(root, release.TITLE)
    link_html_versions(root)
    write_readme(con, root, release)
    return canary_errors(root)
