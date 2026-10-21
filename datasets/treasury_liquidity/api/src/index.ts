// Read-only API over one synthetic dataset held in D1 (Cloudflare's SQLite).
// The code knows nothing about any particular dataset: it discovers tables from the database.
// Access follows docs/roles.html: public sees business tables, analyst adds _meta_ tables,
// reviewer adds the _truth_ answer key.

import { Hono } from 'hono'
import { allTables, allowed, columns, quote, RANK, roleForTable, type Env, type Role, type Vars } from './db'
import ui from './ui'
import { homePage } from './home'
import { findPackFile, visiblePackFiles } from './packs'
import rolesHtml from '../../docs/roles.html'
import appraisalHtml from '../../docs/appraisal-types.html'
import aboutHtml from '../../docs/about.html'
import methodHtml from '../../docs/method.html'
import themeCss from '../../docs/theme.css'

const MAX_LIMIT = 500

const app = new Hono<{ Bindings: Env; Variables: Vars }>()

// Resolve the caller's role. No header means public; a role with a wrong key is refused.
app.use('*', async (c, next) => {
  const asked = (c.req.header('X-Role') ?? 'public').toLowerCase().replace(/[^a-z]/g, '')
  const key = c.req.header('X-Role-Key')
  if (asked === 'public') {
    c.set('role', 'public')
  } else if (asked === 'analyst' && c.env.ANALYST_KEY && key === c.env.ANALYST_KEY) {
    c.set('role', 'analyst')
  } else if (asked === 'reviewer' && c.env.REVIEWER_KEY && key === c.env.REVIEWER_KEY) {
    c.set('role', 'reviewer')
  } else {
    const msg = `Role '${asked}' refused: unknown role or wrong X-Role-Key.`
    // htmx only swaps successful responses, so the pages get the refusal as a 200 fragment.
    if (c.req.path.startsWith('/ui')) return c.html(`<p class="notice error">${msg} Showing nothing until the key is fixed.</p>`)
    return c.json({ error: msg }, 401)
  }
  await next()
})

const apiIndex = (c: any) => ({
  dataset: c.env.DATASET,
  role: c.get('role'),
  ui: '/ui',
  routes: ['/meta', '/tables', '/tables/:name', '/tables/:name/:id', '/dictionary', '/rules', '/packs', '/packs/:pack/:file', '/truth/cases'],
  filters: 'GET /tables/:name?column=value&limit=100&offset=0&order=column',
})

// Browsers get the home page; programs get the route list as JSON.
app.get('/', async (c) => {
  if (!(c.req.header('Accept') ?? '').includes('text/html')) return c.json(apiIndex(c))
  const db = c.env.DB
  const facts = await db.prepare('SELECT key, value FROM _meta_dataset').all<{ key: string; value: string }>()
  const tables = []
  for (const t of await allTables(db)) {
    if (!allowed('public', t)) continue
    const n = await db.prepare(`SELECT count(*) AS n FROM ${quote(t)}`).first<{ n: number }>()
    tables.push({ table: t, rows: n?.n ?? 0 })
  }
  return c.html(homePage(Object.fromEntries(facts.results.map((f) => [f.key, f.value])), tables))
})

app.get('/api', (c) => c.json(apiIndex(c)))

app.get('/meta', async (c) => {
  const db = c.env.DB
  const facts = await db.prepare('SELECT key, value FROM _meta_dataset').all<{ key: string; value: string }>()
  const role = c.get('role')
  const tables = []
  for (const t of await allTables(db)) {
    if (!allowed(role, t)) continue
    const n = await db.prepare(`SELECT count(*) AS n FROM ${quote(t)}`).first<{ n: number }>()
    tables.push({ table: t, rows: n?.n ?? 0, access: roleForTable(t) })
  }
  return c.json({ role, ...Object.fromEntries(facts.results.map((f) => [f.key, f.value])), tables })
})

app.get('/tables', async (c) => {
  const role = c.get('role')
  return c.json((await allTables(c.env.DB)).filter((t) => allowed(role, t)))
})

app.get('/tables/:name', async (c) => {
  const db = c.env.DB
  const name = c.req.param('name')
  if (!(await allTables(db)).includes(name)) return c.json({ error: `No table '${name}'.` }, 404)
  if (!allowed(c.get('role'), name)) return c.json({ error: `Table '${name}' needs the ${roleForTable(name)} role.` }, 403)

  const cols = (await columns(db, name)).map((x) => x.name)
  const q = c.req.query()
  const limit = Math.min(Math.max(parseInt(q.limit ?? '100', 10) || 100, 1), MAX_LIMIT)
  const offset = Math.max(parseInt(q.offset ?? '0', 10) || 0, 0)
  const where: string[] = []
  const args: string[] = []
  for (const [k, v] of Object.entries(q)) {
    if (['limit', 'offset', 'order'].includes(k)) continue
    if (!cols.includes(k)) return c.json({ error: `Unknown column '${k}' in ${name}.` }, 400)
    where.push(`${quote(k)} = ?`)
    args.push(v)
  }
  const order = q.order && cols.includes(q.order.replace(/^-/, '')) ? q.order : cols[0]
  const orderSql = order.startsWith('-') ? `${quote(order.slice(1))} DESC` : quote(order)
  const filter = where.length ? `WHERE ${where.join(' AND ')}` : ''
  const total = await db.prepare(`SELECT count(*) AS n FROM ${quote(name)} ${filter}`).bind(...args).first<{ n: number }>()
  const { results } = await db
    .prepare(`SELECT * FROM ${quote(name)} ${filter} ORDER BY ${orderSql} LIMIT ? OFFSET ?`)
    .bind(...args, limit, offset)
    .all()
  return c.json({ table: name, total: total?.n ?? 0, limit, offset, rows: results })
})

app.get('/tables/:name/:id', async (c) => {
  const db = c.env.DB
  const { name, id } = c.req.param()
  if (!(await allTables(db)).includes(name)) return c.json({ error: `No table '${name}'.` }, 404)
  if (!allowed(c.get('role'), name)) return c.json({ error: `Table '${name}' needs the ${roleForTable(name)} role.` }, 403)
  const pk = (await columns(db, name)).find((x) => x.pk === 1)?.name
  if (!pk) return c.json({ error: `Table '${name}' has no single primary key.` }, 400)
  const row = await db.prepare(`SELECT * FROM ${quote(name)} WHERE ${quote(pk)} = ?`).bind(id).first()
  return row ? c.json(row) : c.json({ error: `No row '${id}' in ${name}.` }, 404)
})

const needs = (min: Role) => async (c: any, next: () => Promise<void>) => {
  if (RANK[c.get('role') as Role] < RANK[min]) return c.json({ error: `Needs the ${min} role.` }, 403)
  await next()
}

app.get('/dictionary', needs('analyst'), async (c) => {
  const db = c.env.DB
  const tables = await db.prepare('SELECT * FROM _meta_tables').all()
  const cols = await db.prepare('SELECT * FROM _meta_columns ORDER BY table_name, position').all()
  const role = c.get('role')
  return c.json({
    tables: tables.results.filter((t: any) => allowed(role, t.table_name)),
    columns: cols.results.filter((x: any) => allowed(role, x.table_name)),
  })
})

app.get('/rules', needs('analyst'), async (c) => {
  const { results } = await c.env.DB.prepare('SELECT * FROM _meta_rules ORDER BY rule_id').all()
  return c.json(results)
})

// Use packs: analyst sees every file except answer files; reviewer sees everything.
app.get('/packs', needs('analyst'), (c) =>
  c.json(visiblePackFiles(c.get('role')).map((f) => ({
    pack: f.pack, file: f.file, description: f.description, url: `/packs/${f.pack}/${f.file}`,
  }))),
)

app.get('/packs/:pack/:file', needs('analyst'), (c) => {
  const f = findPackFile(c.req.param('pack'), c.req.param('file'))
  if (!f) return c.json({ error: 'No such pack file.' }, 404)
  if (RANK[c.get('role')] < RANK[f.minRole]) return c.json({ error: `This file needs the ${f.minRole} role.` }, 403)
  return c.body(f.body, 200, { 'Content-Type': f.contentType })
})

app.get('/truth/cases', needs('reviewer'), async (c) => {
  const db = c.env.DB
  const cases = await db.prepare('SELECT * FROM _truth_cases ORDER BY case_id').all()
  const recs = await db.prepare('SELECT * FROM _truth_case_records ORDER BY case_record_id').all()
  return c.json(
    cases.results.map((k: any) => ({ ...k, records: recs.results.filter((r: any) => r.case_id === k.case_id) })),
  )
})

app.get('/docs/roles', (c) => c.html(rolesHtml))
app.get('/docs/appraisal-types', (c) => c.html(appraisalHtml))
app.get('/docs/about', (c) => c.html(aboutHtml))
app.get('/docs/method', (c) => c.html(methodHtml))
app.get('/docs/theme.css', (c) => c.body(themeCss, 200, { 'Content-Type': 'text/css; charset=utf-8' }))

app.route('/ui', ui)

app.onError((err, c) => c.json({ error: err.message }, 500))

export default app
