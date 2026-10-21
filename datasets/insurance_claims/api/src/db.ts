// Schema discovery and role rules shared by the JSON API and the htmx pages.

export type Role = 'public' | 'analyst' | 'reviewer'

export type Env = {
  DB: D1Database
  DATASET: string
  ANALYST_KEY?: string
  REVIEWER_KEY?: string
}

export type Vars = { role: Role }

export const RANK: Record<Role, number> = { public: 0, analyst: 1, reviewer: 2 }

export const roleForTable = (name: string): Role =>
  name.startsWith('_truth_') ? 'reviewer' : name.startsWith('_meta_') ? 'analyst' : 'public'

export const allowed = (role: Role, table: string) => RANK[role] >= RANK[roleForTable(table)]

export const quote = (id: string) => `"${id.replace(/"/g, '""')}"`

export async function allTables(db: D1Database): Promise<string[]> {
  const { results } = await db
    .prepare(
      `SELECT name FROM sqlite_master WHERE type = 'table'
       AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_cf_%' AND name <> 'd1_migrations' ORDER BY name`,
    )
    .all<{ name: string }>()
  return results.map((r) => r.name)
}

export type Column = { name: string; type: string; pk: number }

export async function columns(db: D1Database, table: string): Promise<Column[]> {
  const { results } = await db
    .prepare(`SELECT name, type, pk FROM pragma_table_info(?)`)
    .bind(table)
    .all<Column>()
  return results
}

export type ForeignKey = { from_table: string; from_col: string; to_table: string; to_col: string }

// Every foreign key in the database, read in one batch.
export async function foreignKeys(db: D1Database, tables: string[]): Promise<ForeignKey[]> {
  const res = await db.batch(
    tables.map((t) => db.prepare(`SELECT ? AS from_table, "from" AS from_col, "table" AS to_table, "to" AS to_col
                                  FROM pragma_foreign_key_list(?)`).bind(t, t)),
  )
  return res.flatMap((r) => r.results as ForeignKey[])
}
