// Home page shown when a browser opens the Worker's base address. Programs still get JSON there.
// Uses the dataset's docs/theme.css, served at /docs/theme.css.

import { html } from 'hono/html'

const FONTS = 'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap'

export function homePage(facts: Record<string, string>, tables: { table: string; rows: number }[]) {
  const title = facts.title ?? facts.dataset ?? 'Dataset'
  return html`<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="${FONTS}" rel="stylesheet">
<link rel="stylesheet" href="/docs/theme.css">
</head>
<body>
<header class="masthead"><div class="wrap">
  <div class="crumbs"><span>Study datasets</span><span>›</span><span>${title}</span></div>
  <h1>${title}</h1>
  <p class="lead">${facts.firm} · ${facts.period} · extract taken ${facts.extract_date}</p>
  <nav class="toc"><a href="/ui">Open the data browser</a><a href="/docs/about">About this dataset</a></nav>
</div></header>
<main>
  <div class="grid">
    <section class="card">
      <div class="meta"><span class="chip green">Browse</span></div>
      <h3>Data browser</h3>
      <p class="q">Tables, filters, linked records, and — with the right role — the rules and the answer key.</p>
      <ul class="links"><li><a href="/ui">Open the data browser</a></li></ul>
    </section>
    <section class="card">
      <div class="meta"><span class="chip violet">Read</span></div>
      <h3>Documents</h3>
      <p class="q">What the dataset is, how it was built, who may see what, and the kinds of analysis it tests.</p>
      <ul class="links">
        <li><a href="/docs/about">About this dataset</a> <span class="who">· start here</span></li>
        <li><a href="/docs/method">How it was built</a></li>
        <li><a href="/docs/roles">Roles</a></li>
        <li><a href="/docs/appraisal-types">Appraisal types</a></li>
      </ul>
    </section>
    <section class="card">
      <div class="meta"><span class="chip coral">Build on it</span></div>
      <h3>JSON API</h3>
      <p class="q">Read-only access for apps and scripts. Send X-Role and X-Role-Key headers for the analyst or reviewer role.</p>
      <ul class="links">
        <li><a href="/api">Route list</a></li>
        <li><a href="/meta">Dataset facts and tables</a></li>
      </ul>
    </section>
  </div>
  <h2>Tables</h2>
  <div class="table-wrap"><table>
    <thead><tr><th>Table</th><th>Rows</th></tr></thead>
    <tbody>${tables.map((t) => html`<tr><td><a href="/ui/table/${t.table}"><code>${t.table}</code></a></td><td class="num">${t.rows}</td></tr>`)}</tbody>
  </table></div>
  <p class="muted">The landing page for all datasets is <code>index.html</code> in the project folder. Open it from there.</p>
</main>
</body>
</html>`
}
