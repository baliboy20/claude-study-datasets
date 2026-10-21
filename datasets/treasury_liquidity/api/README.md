# Treasury liquidity dataset API

A read-only Hono API and htmx data browser for the treasury liquidity dataset, run locally as a Cloudflare Worker. The code reads the table list from the database. Settings are in `wrangler.toml` and role keys in `.dev.vars`, both in this folder.

## Run

From this folder:

```bash
npm install
```

```bash
npm run load
```

```bash
npm run dev
```

`load` rebuilds the local D1 database from `../db/seed.sql`. Run it again after each `python3 generator/build.py`. The D1 files live in `../db/v3/`.

The API listens on http://localhost:8851, with its debugger on 9851. Port 8787, wrangler's default, is used by another Worker on this machine, 8846 by the procurement dataset, 8847 by the regulatory reporting dataset, 8848 by the AML dataset, 8849 by the insurance claims dataset and 8850 by the SME lending dataset.

## Data browser

Open http://localhost:8851/ui in a browser. The pages use htmx and are served by the same Worker as the JSON API, so they follow the same access rules.

| View | Shows |
|---|---|
| Overview | Dataset facts and every table you can see, with row counts |
| Table | 25 rows a page. Click a heading to sort. Type in the box under a heading to filter by that column |
| Record panel | Opens when you click a row. Linked values open the linked record. Lists the records in other tables that point to this one. For the reviewer role, it also shows the planted case the record belongs to |
| Business rules, Data dictionary | Analyst role and above |
| Use packs | Analyst role and above; answer files reviewer only |
| Planted cases | Reviewer role only |
| Documents | The dataset's `docs/` pages, served at `/docs/about`, `/docs/method`, `/docs/roles` and `/docs/appraisal-types` |

To change role, choose it at the top of the page, enter its key from `.dev.vars`, and press Apply. The browser remembers the role and key in its local storage. Choose public and press Apply to clear them.

## Roles

Roles follow `docs/roles.html`. Send `X-Role` and `X-Role-Key` headers. The keys are in `.dev.vars` in this folder, which is not shared. `.dev.vars.example` shows the format.

| Role | Sees |
|---|---|
| public (no headers) | Business and lookup tables, including `treasury_policy` (the policy and its definitions), `liquidity_buckets` and `stress_scenarios` |
| analyst | Also `_meta_` tables, `/dictionary` and `/rules` (the treasury procedures) |
| reviewer | Also `_truth_` tables and `/truth/cases` (the answer key) |

## Routes

| Route | Returns |
|---|---|
| `GET /` | In a browser: the dataset's home page, linking the data browser, documents and API. From a program: the route list as JSON |
| `GET /api` | The route list as JSON |
| `GET /ui` | The data browser described above |
| `GET /docs/about`, `/docs/method`, `/docs/roles`, `/docs/appraisal-types` | The dataset's documents |
| `GET /meta` | Dataset facts and the tables your role can see, with row counts |
| `GET /tables` | Table names your role can see |
| `GET /tables/:name` | Rows. Filter with `?column=value`, page with `limit` (up to 500) and `offset`, sort with `order=column` or `order=-column` |
| `GET /tables/:name/:id` | One row by primary key |
| `GET /dictionary` | Data dictionary (analyst) |
| `GET /rules` | Business rules (analyst) |
| `GET /packs` | Use-pack files your role may see (analyst and reviewer) |
| `GET /packs/:pack/:file` | One pack file. Answer files, such as `ai-eval/expected-answers.json`, need the reviewer role |
| `GET /truth/cases` | Planted cases with their records (reviewer) |

Example:

```bash
curl "localhost:8851/tables/cashflows?counterparty_id=CP-0031&order=due_date"
```

---

| Document | Version | Date | Purpose | Dataset |
|---|---|---|---|---|
| api/README.md | 1.2 | 2026-10-20 | Explains how to run the local API and data browser, and what each route and role returns | Treasury liquidity |
