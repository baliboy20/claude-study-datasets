// htmx pages for browsing a dataset, served by the same Worker as the JSON API.
// Every page is built from the database schema, so it works for any dataset.
// The role chosen in the page header is sent as X-Role / X-Role-Key on each htmx request,
// and the same access rules as the API apply (see db.ts and docs/roles.html).

import { Hono } from 'hono'
import { html, raw } from 'hono/html'
import { visiblePackFiles } from './packs'
import { allTables, allowed, columns, foreignKeys, quote, RANK, roleForTable, type Column, type Env, type Role, type Vars } from './db'

const ui = new Hono<{ Bindings: Env; Variables: Vars }>()

const PAGE_SIZE = 25
const HTMX = 'https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js'
const gbp = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' })
const num = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 })
const MONEY_COL = /(amount|price|value|limit|_gbp|_net)/i

type Row = Record<string, unknown>

function cell(col: Column, v: unknown) {
  if (v === null || v === undefined || v === '') return html`<span class="null">–</span>`
  if (typeof v === 'number') return col.type === 'REAL' && MONEY_COL.test(col.name) ? gbp.format(v) : num.format(v)
  return String(v)
}

const isNumeric = (col: Column) => col.type === 'REAL' || col.type === 'INTEGER'

function qs(params: Record<string, string | number | undefined>) {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') p.set(k, String(v))
  const s = p.toString()
  return s ? `?${s}` : ''
}

const refused = (need: Role) =>
  html`<div class="notice">This view needs the <strong>${need}</strong> role. Choose it at the top of the page and enter its key.</div>`

// ------------------------------------------------------------------ page shell

function shell(dataset: string, firstView: string) {
  return html`<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${dataset} data browser</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<script src="${HTMX}"></script>
<style>${raw(CSS)}</style>
</head>
<body hx-history="false">
<header class="top">
  <div class="brand"><strong>Study data</strong> <span class="ds">${dataset}</span></div>
  <form class="role" id="roleForm" onsubmit="return applyRole(event)">
    <label>Role
      <select id="roleSel">
        <option value="public">public</option><option value="analyst">analyst</option><option value="reviewer">reviewer</option>
      </select>
    </label>
    <input id="roleKey" type="password" placeholder="Key from api/.dev.vars" autocomplete="off">
    <button type="submit">Apply</button>
    <span id="roleNow" class="pill"></span>
  </form>
</header>
<div class="layout">
  <nav id="nav" hx-get="/ui/nav" hx-trigger="load, role-changed from:body"></nav>
  <main id="main" hx-get="${firstView}" hx-trigger="load"></main>
</div>
<aside id="detail" class="drawer" aria-live="polite"></aside>
<script>
  var current = ${raw(JSON.stringify(firstView))};
  function store(k, v) { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v) } catch (e) {} }
  function load(k) { try { return localStorage.getItem(k) } catch (e) { return null } }
  function showRole() { document.getElementById('roleNow').textContent = 'viewing as ' + (load('studyRole') || 'public') }
  document.getElementById('roleSel').value = load('studyRole') || 'public';
  showRole();
  document.body.addEventListener('htmx:configRequest', function (e) {
    var r = load('studyRole');
    if (r && r !== 'public') { e.detail.headers['X-Role'] = r; e.detail.headers['X-Role-Key'] = load('studyKey') || '' }
  });
  document.body.addEventListener('htmx:afterRequest', function (e) {
    var t = e.detail.target;
    if (t && t.id === 'main' && e.detail.requestConfig && e.detail.requestConfig.verb === 'get') {
      current = e.detail.pathInfo.finalRequestPath || current;
      try { history.replaceState(null, '', current) } catch (err) {}
    }
  });
  function applyRole(ev) {
    ev.preventDefault();
    var r = document.getElementById('roleSel').value, k = document.getElementById('roleKey');
    store('studyRole', r);
    if (r === 'public') store('studyKey', null); else if (k.value) store('studyKey', k.value);
    k.value = ''; showRole(); closeDetail();
    htmx.trigger(document.body, 'role-changed');
    htmx.ajax('GET', current, '#main');
    return false;
  }
  function closeDetail() { var d = document.getElementById('detail'); d.innerHTML = ''; d.classList.remove('open') }
  // The panel opens below the header so the role controls stay usable.
  function placeDetail() { var d = document.getElementById('detail'), h = document.querySelector('.top').offsetHeight;
    d.style.top = h + 'px'; d.style.height = 'calc(100vh - ' + h + 'px)' }
  window.addEventListener('resize', placeDetail);
  document.body.addEventListener('htmx:afterSwap', function (e) { if (e.detail.target.id === 'detail') { placeDetail(); e.detail.target.classList.add('open') } });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeDetail() });
</script>
</body>
</html>`
}

// A browser opening any /ui address directly gets the shell, which then loads that view through htmx.
ui.use('*', async (c, next) => {
  if (c.req.method === 'GET' && !c.req.header('HX-Request')) {
    const url = new URL(c.req.url)
    const view = url.pathname === '/ui' || url.pathname === '/ui/' ? '/ui/overview' : url.pathname + url.search
    return c.html(shell(c.env.DATASET, view))
  }
  await next()
})

// ------------------------------------------------------------------ navigation and overview

async function tableCounts(db: D1Database, tables: string[]) {
  const res = await db.batch(tables.map((t) => db.prepare(`SELECT count(*) AS n FROM ${quote(t)}`)))
  return Object.fromEntries(tables.map((t, i) => [t, (res[i].results[0] as { n: number }).n]))
}

async function kinds(db: D1Database) {
  const { results } = await db.prepare('SELECT table_name, kind, description FROM _meta_tables').all<Row>()
  return Object.fromEntries(results.map((r) => [r.table_name as string, r]))
}

const viewLink = (href: string, label: unknown, cls = '') =>
  html`<a href="${href}" class="${cls}" hx-get="${href}" hx-target="#main" hx-push-url="false">${label}</a>`

ui.get('/nav', async (c) => {
  const db = c.env.DB
  const role = c.get('role')
  const tables = (await allTables(db)).filter((t) => allowed(role, t))
  const counts = await tableCounts(db, tables)
  const k = await kinds(db)
  const group = (kind: string, title: string) => {
    const ts = tables.filter((t) => (k[t]?.kind ?? roleForTable(t)) === kind)
    if (!ts.length) return ''
    return html`<h4>${title}</h4><ul>${ts.map((t) => html`<li>${viewLink(`/ui/table/${t}`, html`${t}<span class="n">${counts[t]}</span>`)}</li>`)}</ul>`
  }
  return c.html(html`
    <ul class="views">
      <li>${viewLink('/ui/overview', 'Overview')}</li>
      ${RANK[role] >= RANK.analyst ? html`<li>${viewLink('/ui/rules', 'Business rules')}</li><li>${viewLink('/ui/dictionary', 'Data dictionary')}</li>` : ''}
      ${RANK[role] >= RANK.analyst ? html`<li>${viewLink('/ui/packs', 'Use packs')}</li>` : ''}
      ${role === 'reviewer' ? html`<li>${viewLink('/ui/cases', 'Planted cases')}</li>` : ''}
      <li><a href="/docs/about" target="_blank" rel="noopener">About this dataset ↗</a></li>
      <li><a href="/docs/method" target="_blank" rel="noopener">How it was built ↗</a></li>
      <li><a href="/docs/roles" target="_blank" rel="noopener">Roles document ↗</a></li>
      <li><a href="/docs/appraisal-types" target="_blank" rel="noopener">Appraisal types ↗</a></li>
    </ul>
    ${group('business', 'Business records')}
    ${group('lookup', 'Reference data')}
    ${group('meta', 'Documentation')}
    ${group('truth', 'Answer key')}`)
})

// Renders the business story: blank lines separate paragraphs; lines starting '- ' become a list.
function storyHtml(text: string) {
  const out: unknown[] = []
  let items: unknown[] = []
  for (const line of [...text.split('\n'), '']) {
    if (line.startsWith('- ')) {
      const body = line.slice(2)
      const cut = body.indexOf('. ')
      items.push(cut > 0 ? html`<li><strong>${body.slice(0, cut)}.</strong> ${body.slice(cut + 2)}</li>` : html`<li>${body}</li>`)
      continue
    }
    if (items.length) { out.push(html`<ul>${items}</ul>`); items = [] }
    if (line) out.push(html`<p>${line}</p>`)
  }
  return out
}

ui.get('/overview', async (c) => {
  const db = c.env.DB
  const role = c.get('role')
  const facts = Object.fromEntries(
    (await db.prepare('SELECT key, value FROM _meta_dataset').all<{ key: string; value: string }>()).results.map((f) => [f.key, f.value]),
  )
  const tables = (await allTables(db)).filter((t) => allowed(role, t))
  const counts = await tableCounts(db, tables)
  const k = await kinds(db)
  const showDesc = RANK[role] >= RANK.analyst
  return c.html(html`
    <h1>${facts.title ?? c.env.DATASET}</h1>
    <p class="lead">${facts.firm} · ${facts.period} · extract taken ${facts.extract_date}</p>
    <p class="muted">${facts.disclaimer}</p>
    ${facts.business_context ? html`<section class="story"><h2>Business context</h2>${storyHtml(facts.business_context)}</section>` : ''}
    <div class="cards">
      ${tables.map((t) => html`
        <a class="card" href="/ui/table/${t}" hx-get="/ui/table/${t}" hx-target="#main">
          <span class="kind ${k[t]?.kind}">${k[t]?.kind ?? ''}</span>
          <strong>${t}</strong>
          <span class="big">${counts[t]}</span><span class="muted">rows</span>
          ${showDesc ? html`<p>${k[t]?.description}</p>` : ''}
        </a>`)}
    </div>
    ${role === 'public' ? html`<p class="muted">The analyst role adds table descriptions, rules and the data dictionary. The reviewer role adds the answer key.</p>` : ''}`)
})

// ------------------------------------------------------------------ table view

ui.get('/table/:name', async (c) => {
  const db = c.env.DB
  const role = c.get('role')
  const name = c.req.param('name')
  if (!(await allTables(db)).includes(name)) return c.html(html`<div class="notice">No table called ${name}.</div>`)
  if (!allowed(role, name)) return c.html(refused(roleForTable(name)))

  const cols = await columns(db, name)
  const colNames = cols.map((x) => x.name)
  const pk = cols.find((x) => x.pk === 1)?.name ?? colNames[0]
  const q = c.req.query()
  const page = Math.max(parseInt(q.page ?? '1', 10) || 1, 1)
  const orderRaw = q.order && colNames.includes(q.order.replace(/^-/, '')) ? q.order : pk
  const desc = orderRaw.startsWith('-')
  const orderCol = orderRaw.replace(/^-/, '')

  const where: string[] = []
  const args: (string | number)[] = []
  const contains: Record<string, string> = {}
  const exact: Record<string, string> = {}
  for (const [k, v] of Object.entries(q)) {
    if (!v) continue
    if (k.startsWith('f_') && colNames.includes(k.slice(2))) {
      contains[k.slice(2)] = v
      where.push(`CAST(${quote(k.slice(2))} AS TEXT) LIKE ?`)
      args.push(`%${v}%`)
    } else if (k.startsWith('x_') && colNames.includes(k.slice(2))) {
      exact[k.slice(2)] = v
      where.push(`${quote(k.slice(2))} = ?`)
      args.push(v)
    }
  }
  const filter = where.length ? `WHERE ${where.join(' AND ')}` : ''
  const total = (await db.prepare(`SELECT count(*) AS n FROM ${quote(name)} ${filter}`).bind(...args).first<{ n: number }>())?.n ?? 0
  const pages = Math.max(Math.ceil(total / PAGE_SIZE), 1)
  const { results } = await db
    .prepare(`SELECT * FROM ${quote(name)} ${filter} ORDER BY ${quote(orderCol)} ${desc ? 'DESC' : 'ASC'} LIMIT ? OFFSET ?`)
    .bind(...args, PAGE_SIZE, (Math.min(page, pages) - 1) * PAGE_SIZE)
    .all<Row>()

  const base = `/ui/table/${name}`
  const keep = { ...Object.fromEntries(Object.entries(exact).map(([k, v]) => [`x_${k}`, v])), ...Object.fromEntries(Object.entries(contains).map(([k, v]) => [`f_${k}`, v])) }
  const sortLink = (col: string) => {
    const next = orderCol === col && !desc ? `-${col}` : col
    const arrow = orderCol === col ? (desc ? ' ↓' : ' ↑') : ''
    return html`<a href="${base}${qs({ ...keep, order: next })}" hx-get="${base}${qs({ ...keep, order: next })}" hx-target="#main">${col}${arrow}</a>`
  }
  const pageLink = (p: number, label: string) =>
    p < 1 || p > pages
      ? html`<span class="disabled">${label}</span>`
      : html`<a href="${base}${qs({ ...keep, order: orderRaw, page: p })}" hx-get="${base}${qs({ ...keep, order: orderRaw, page: p })}" hx-target="#main">${label}</a>`

  return c.html(html`
    <h1>${name}</h1>
    ${Object.keys(exact).length
      ? html`<p class="chips">Showing rows where ${Object.entries(exact).map(([k, v]) => html`<span class="chip">${k} = ${v}</span>`)}
          ${viewLink(base, 'clear')}</p>`
      : ''}
    <p id="count" class="muted">${total} row${total === 1 ? '' : 's'}${where.length ? ' match' : ''}. Click a row to see its details and linked records. Type in the boxes under the headings to filter.</p>
    <form id="tf" hx-get="${base}" hx-trigger="input delay:350ms" hx-target="#rows" hx-select="#rows"
          hx-swap="outerHTML" hx-select-oob="#count,#pager" hx-disinherit="*" onsubmit="return false">
      ${Object.entries(exact).map(([k, v]) => html`<input type="hidden" name="x_${k}" value="${v}">`)}
      <input type="hidden" name="order" value="${orderRaw}">
      <div class="scroll">
        <table class="data">
          <thead>
            <tr>${cols.map((col) => html`<th class="${isNumeric(col) ? 'num' : ''}">${sortLink(col.name)}</th>`)}</tr>
            <tr class="filters">${cols.map((col) => html`<th><input name="f_${col.name}" value="${contains[col.name] ?? ''}" aria-label="Filter ${col.name}"></th>`)}</tr>
          </thead>
          <tbody id="rows">
            ${results.map((r) => html`
              <tr class="click" hx-get="/ui/row/${name}/${encodeURIComponent(String(r[pk]))}" hx-target="#detail">
                ${cols.map((col) => html`<td class="${isNumeric(col) ? 'num' : ''}">${cell(col, r[col.name])}</td>`)}
              </tr>`)}
            ${results.length ? '' : html`<tr><td colspan="${cols.length}" class="muted">No rows match.</td></tr>`}
          </tbody>
        </table>
      </div>
    </form>
    <p id="pager" class="pager">${pageLink(page - 1, '‹ Previous')} <span>Page ${Math.min(page, pages)} of ${pages}</span> ${pageLink(page + 1, 'Next ›')}</p>`)
})

// ------------------------------------------------------------------ record view

ui.get('/row/:name/:id', async (c) => {
  const db = c.env.DB
  const role = c.get('role')
  const { name, id } = c.req.param()
  const tables = await allTables(db)
  if (!tables.includes(name)) return c.html(html`<div class="notice">No table called ${name}.</div>`)
  if (!allowed(role, name)) return c.html(refused(roleForTable(name)))
  const cols = await columns(db, name)
  const pk = cols.find((x) => x.pk === 1)?.name ?? cols[0].name
  const row = await db.prepare(`SELECT * FROM ${quote(name)} WHERE ${quote(pk)} = ?`).bind(id).first<Row>()
  if (!row) return c.html(html`<div class="notice">No ${name} record ${id}.</div>`)

  const fks = await foreignKeys(db, tables)
  const outbound = Object.fromEntries(fks.filter((f) => f.from_table === name).map((f) => [f.from_col, f]))
  const inbound = fks.filter((f) => f.to_table === name && allowed(role, f.from_table))

  const related = await Promise.all(
    inbound.map(async (f) => {
      const fcols = await columns(db, f.from_table)
      const fpk = fcols.find((x) => x.pk === 1)?.name ?? fcols[0].name
      const value = row[f.to_col]
      const { results } = await db
        .prepare(`SELECT * FROM ${quote(f.from_table)} WHERE ${quote(f.from_col)} = ? ORDER BY ${quote(fpk)} LIMIT 8`)
        .bind(value as string).all<Row>()
      const n = (await db.prepare(`SELECT count(*) AS n FROM ${quote(f.from_table)} WHERE ${quote(f.from_col)} = ?`)
        .bind(value as string).first<{ n: number }>())?.n ?? 0
      return { f, fcols, fpk, results, n, value }
    }),
  )

  let cases: Row[] = []
  if (role === 'reviewer' && tables.includes('_truth_case_records')) {
    cases = (await db.prepare(`SELECT r.case_id, r.role_in_case, c.title, c.classification FROM _truth_case_records r
              JOIN _truth_cases c USING (case_id) WHERE r.table_name = ? AND r.record_id = ?`).bind(name, id).all<Row>()).results
  }

  const rowLink = (table: string, value: unknown) =>
    html`<a href="/ui/row/${table}/${encodeURIComponent(String(value))}" hx-get="/ui/row/${table}/${encodeURIComponent(String(value))}" hx-target="#detail">${String(value)}</a>`

  return c.html(html`
    <div class="drawer-head"><span class="muted">${name}</span><button type="button" onclick="closeDetail()" aria-label="Close">✕</button></div>
    <h2>${id}</h2>
    ${cases.map((k) => html`<p class="case ${k.classification === 'Benign lookalike' ? 'benign' : 'genuine'}">
        ${k.case_id}: ${k.title} <span class="muted">(${k.role_in_case})</span></p>`)}
    <dl class="record">
      ${cols.map((col) => {
        const v = row[col.name]
        const fk = outbound[col.name]
        const shown = fk && v !== null && allowed(role, fk.to_table) ? rowLink(fk.to_table, v) : cell(col, v)
        return html`<dt>${col.name}</dt><dd class="${isNumeric(col) ? 'num' : ''}">${shown}</dd>`
      })}
    </dl>
    ${related.filter((r) => r.n > 0).map((r) => html`
      <h3>${r.f.from_table} <span class="muted">via ${r.f.from_col} · ${r.n}</span></h3>
      <ul class="refs">
        ${r.results.map((x) => html`<li>${rowLink(r.f.from_table, x[r.fpk])}
          <span class="muted">${r.fcols.filter((col) => col.name !== r.fpk && col.name !== r.f.from_col).slice(0, 2)
            .map((col) => html`${cell(col, x[col.name])} `)}</span></li>`)}
      </ul>
      ${r.n > r.results.length
        ? html`<p><a href="/ui/table/${r.f.from_table}${qs({ [`x_${r.f.from_col}`]: String(r.value) })}" hx-get="/ui/table/${r.f.from_table}${qs({ [`x_${r.f.from_col}`]: String(r.value) })}" hx-target="#main">All ${r.n} in the table view</a></p>`
        : ''}`)}`)
})

// ------------------------------------------------------------------ documentation and answer key

ui.get('/rules', async (c) => {
  if (RANK[c.get('role')] < RANK.analyst) return c.html(refused('analyst'))
  const { results } = await c.env.DB.prepare('SELECT * FROM _meta_rules ORDER BY rule_id').all<Row>()
  return c.html(html`
    <h1>Business rules</h1>
    <div class="scroll"><table class="data wrap">
      <thead><tr><th>Rule</th><th>Area</th><th>Rule</th><th>Applies to</th></tr></thead>
      <tbody>${results.map((r) => html`<tr><td>${r.rule_id}</td><td>${r.category}</td>
        <td><strong>${r.title}.</strong> ${r.statement}</td><td>${r.related_tables}</td></tr>`)}</tbody>
    </table></div>`)
})

ui.get('/dictionary', async (c) => {
  const role = c.get('role')
  if (RANK[role] < RANK.analyst) return c.html(refused('analyst'))
  const db = c.env.DB
  const tables = (await db.prepare('SELECT * FROM _meta_tables').all<Row>()).results.filter((t) => allowed(role, t.table_name as string))
  const cols = (await db.prepare('SELECT * FROM _meta_columns ORDER BY table_name, position').all<Row>()).results
  return c.html(html`
    <h1>Data dictionary</h1>
    ${tables.map((t) => html`
      <h2 id="d-${t.table_name}">${viewLink(`/ui/table/${t.table_name}`, t.table_name)} <span class="kind ${t.kind}">${t.kind}</span></h2>
      <p>${t.description}</p>
      <div class="scroll"><table class="data wrap">
        <thead><tr><th>Column</th><th>Type</th><th>Meaning</th><th>Points to</th></tr></thead>
        <tbody>${cols.filter((x) => x.table_name === t.table_name).map((x) => html`<tr>
          <td>${x.column_name}</td><td>${x.data_type}${x.nullable ? ' (optional)' : ''}</td><td>${x.description}</td><td>${x.references_column ?? ''}</td></tr>`)}</tbody>
      </table></div>`)}`)
})

ui.get('/packs', (c) => {
  const role = c.get('role')
  if (RANK[role] < RANK.analyst) return c.html(refused('analyst'))
  const files = visiblePackFiles(role)
  return c.html(html`
    <h1>Use packs</h1>
    <p class="muted">Material for one use of the data. ${role === 'reviewer'
      ? 'As reviewer you see every file, including answer files.'
      : 'Answer files are hidden from the analyst role; the reviewer role sees them.'}</p>
    ${files.map((f) => html`
      <section class="casecard benign">
        <h2>${f.pack} / ${f.file}</h2>
        <p class="meta"><span class="tag">${f.minRole === 'reviewer' ? 'Reviewer only' : 'Analyst and reviewer'}</span>
          <span class="muted">${f.description}</span> · <a href="/packs/${f.pack}/${f.file}" target="_blank" rel="noopener">raw file</a></p>
        <details><summary>Show contents</summary><pre>${f.body}</pre></details>
      </section>`)}`)
})

ui.get('/cases', async (c) => {
  if (c.get('role') !== 'reviewer') return c.html(refused('reviewer'))
  const db = c.env.DB
  const cases = (await db.prepare('SELECT * FROM _truth_cases ORDER BY case_id').all<Row>()).results
  const recs = (await db.prepare('SELECT * FROM _truth_case_records ORDER BY case_record_id').all<Row>()).results
  return c.html(html`
    <h1>Planted cases</h1>
    <p class="muted">The answer key. Genuine exceptions are real control failures; benign lookalikes look suspicious but are legitimate.</p>
    ${cases.map((k) => html`
      <section class="casecard ${k.classification === 'Benign lookalike' ? 'benign' : 'genuine'}">
        <h2>${k.case_id} · ${k.title}</h2>
        <p class="meta"><span class="tag">${k.classification}</span>
          ${k.severity !== 'None' ? html`<span class="tag sev-${String(k.severity).toLowerCase()}">${k.severity}</span>` : ''}
          <span class="muted">Rules ${k.rules_involved}</span></p>
        <p>${k.explanation}</p>
        <p><strong>Next step:</strong> ${k.expected_next_step}</p>
        <ul class="refs">${recs.filter((r) => r.case_id === k.case_id).map((r) => html`<li>
          <a href="/ui/row/${r.table_name}/${encodeURIComponent(String(r.record_id))}" hx-get="/ui/row/${r.table_name}/${encodeURIComponent(String(r.record_id))}" hx-target="#detail">${r.table_name} ${r.record_id}</a>
          <span class="muted">${r.role_in_case}${r.is_key_record ? ' · found by the query' : ''}</span></li>`)}</ul>
        <details><summary>Query that finds it</summary><pre>${k.detection_sql}</pre></details>
      </section>`)}`)
})

// ------------------------------------------------------------------ styles

const CSS = `
:root { --bg:#fffbf5; --surface:#fff; --text:#1c2233; --muted:#5d6478; --line:#ece4d8; --accent:#0e7c86;
  --accent-soft:#e1f4f3; --hover:#fdf3e6; --good:#23854f; --good-soft:#e2f4ea; --bad:#d2442f; --bad-soft:#fde7e3; --warn:#b97a00;
  --violet:#5b4bd6; --band:linear-gradient(120deg,#0e7c86 0%,#2f6fcf 58%,#6c5ce7 100%); }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#10131c; --surface:#181c28; --text:#ecebf2;
  --muted:#a2a8ba; --line:#2a3040; --accent:#4fd1c5; --accent-soft:#10302f; --hover:#20263a; --good:#6fd69b; --good-soft:#15301f;
  --bad:#ff8a78; --bad-soft:#3a1f1c; --warn:#ffc857; --violet:#a99cff; --band:linear-gradient(120deg,#0b5c63 0%,#24519b 58%,#4b3fae 100%); } }
:root[data-theme="dark"] { --bg:#10131c; --surface:#181c28; --text:#ecebf2; --muted:#a2a8ba; --line:#2a3040; --accent:#4fd1c5;
  --accent-soft:#10302f; --hover:#20263a; --good:#6fd69b; --good-soft:#15301f; --bad:#ff8a78; --bad-soft:#3a1f1c; --warn:#ffc857;
  --violet:#a99cff; --band:linear-gradient(120deg,#0b5c63 0%,#24519b 58%,#4b3fae 100%); }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--text); font:15px/1.55 "Plus Jakarta Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
a { color:var(--accent); text-decoration:none; } a:hover { text-decoration:underline; }
.top { display:flex; flex-wrap:wrap; gap:12px; align-items:center; justify-content:space-between; padding:10px 16px;
  background:var(--band); color:#fff; position:sticky; top:0; z-index:5; }
.brand strong { font-weight:800; letter-spacing:-.01em; } .brand .ds { color:rgba(255,255,255,.85); margin-left:6px; }
.role { display:flex; flex-wrap:wrap; gap:8px; align-items:center; font-size:14px; }
.role select, .role input, .role button { font:inherit; padding:5px 10px; border:1px solid rgba(255,255,255,.35); border-radius:999px;
  background:rgba(255,255,255,.16); color:#fff; }
.role input::placeholder { color:rgba(255,255,255,.75); }
.role select option { color:#1c2233; }
.role button { background:#fff; color:#0e7c86; border-color:#fff; font-weight:700; cursor:pointer; }
.top .pill { color:rgba(255,255,255,.85); }
.pill { font-size:12px; color:var(--muted); }
.layout { display:grid; grid-template-columns:230px minmax(0,1fr); }
#nav { border-right:1px solid var(--line); padding:12px 12px 40px; font-size:14px; min-height:calc(100vh - 56px); }
#nav h4 { margin:18px 0 4px; font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
#nav ul { list-style:none; margin:0; padding:0; }
#nav li a { display:flex; justify-content:space-between; padding:4px 8px; border-radius:6px; color:var(--text); }
#nav li a:hover { background:var(--hover); text-decoration:none; }
#nav .n { color:var(--muted); font-variant-numeric:tabular-nums; }
#nav .views { margin-bottom:6px; }
main { padding:16px 24px 64px; min-width:0; }
h1 { font-size:1.6rem; margin:4px 0 8px; font-weight:800; letter-spacing:-.02em; } h2 { font-size:1.15rem; margin:24px 0 6px; } h3 { font-size:1rem; margin:20px 0 6px; }
.lead { font-size:1.05rem; margin:0 0 4px; } .muted { color:var(--muted); }
.story { background:var(--surface); border:1px solid var(--line); border-left:4px solid var(--violet); border-radius:14px; padding:4px 18px 10px; margin:14px 0; max-width:900px; }
.story h2 { margin-top:12px; } .story li { margin:4px 0; }
.cards { display:grid; grid-template-columns:repeat(auto-fill,minmax(210px,1fr)); gap:12px; margin:16px 0; }
.card { display:block; background:var(--surface); border:1px solid var(--line); border-top:4px solid var(--accent); border-radius:14px; padding:12px 14px; color:var(--text); }
.card:hover { border-color:var(--accent); text-decoration:none; }
.card strong { display:block; margin:4px 0; } .card .big { font-size:1.6rem; font-weight:600; margin-right:4px; font-variant-numeric:tabular-nums; }
.card p { margin:6px 0 0; font-size:13px; color:var(--muted); }
.kind { font-size:11px; text-transform:uppercase; letter-spacing:.05em; padding:1px 7px; border-radius:999px; background:var(--hover); color:var(--muted); }
.kind.truth { background:var(--bad-soft); color:var(--bad); } .kind.meta { background:var(--accent-soft); color:var(--accent); }
.scroll { overflow-x:auto; border:1px solid var(--line); border-radius:8px; background:var(--surface); }
table.data { border-collapse:collapse; width:100%; font-size:13px; }
table.data th, table.data td { padding:6px 10px; border-bottom:1px solid var(--line); text-align:left; white-space:nowrap; vertical-align:top; }
table.data.wrap td { white-space:normal; }
table.data th { font-size:12px; background:var(--hover); position:sticky; top:0; }
table.data th a { color:var(--text); }
table.data .num { text-align:right; font-variant-numeric:tabular-nums; }
tr.filters th { padding:4px 6px; } tr.filters input { width:100%; min-width:70px; font:inherit; font-size:12px; padding:3px 6px;
  border:1px solid var(--line); border-radius:4px; background:var(--bg); color:var(--text); }
tr.click { cursor:pointer; } tr.click:hover td { background:var(--hover); }
.null { color:var(--muted); }
.pager { display:flex; gap:16px; align-items:center; } .pager .disabled { color:var(--muted); }
.chips .chip { background:var(--accent-soft); color:var(--accent); border-radius:999px; padding:1px 10px; margin-right:6px; }
.notice { background:var(--surface); border:1px solid var(--line); border-left:4px solid var(--warn); padding:10px 14px; border-radius:6px; margin:12px 0; }
.notice.error { border-left-color:var(--bad); }
.drawer { position:fixed; top:0; right:0; height:100vh; width:min(460px,100vw); background:var(--surface); border-left:1px solid var(--line);
  box-shadow:-8px 0 24px rgba(0,0,0,.12); padding:12px 18px 40px; overflow-y:auto; transform:translateX(105%); transition:transform .18s; z-index:10; }
.drawer.open { transform:none; }
.drawer-head { display:flex; justify-content:space-between; align-items:center; }
.drawer-head button { border:0; background:none; font-size:18px; cursor:pointer; color:var(--muted); }
.drawer h2 { margin:4px 0 10px; }
dl.record { display:grid; grid-template-columns:max-content 1fr; gap:4px 14px; font-size:13px; margin:0; }
dl.record dt { color:var(--muted); } dl.record dd { margin:0; word-break:break-word; }
ul.refs { list-style:none; padding:0; margin:0; font-size:13px; } ul.refs li { padding:3px 0; border-bottom:1px solid var(--line); }
.case { padding:6px 10px; border-radius:6px; font-size:13px; margin:0 0 8px; }
.case.genuine { background:var(--bad-soft); } .case.benign { background:var(--good-soft); }
.casecard { background:var(--surface); border:1px solid var(--line); border-left:4px solid var(--bad); border-radius:8px; padding:4px 16px 12px; margin:14px 0; }
.casecard.benign { border-left-color:var(--good); }
.tag { font-size:12px; padding:1px 8px; border-radius:999px; background:var(--hover); margin-right:6px; }
.sev-high { background:var(--bad-soft); color:var(--bad); } .sev-medium { color:var(--warn); }
pre { white-space:pre-wrap; font-size:12px; background:var(--bg); padding:8px; border-radius:6px; }
@media (max-width: 760px) { .layout { grid-template-columns:1fr; } #nav { min-height:0; max-height:32vh; overflow-y:auto; border-right:0; border-bottom:1px solid var(--line); }
  main { padding:12px 16px 48px; } }
`

export default ui
