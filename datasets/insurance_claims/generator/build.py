"""Build this dataset: python3 generator/build.py  (run from the dataset folder)

Everything the build needs is in this folder:
  generator/scenario.py    build(rng) -> (schema, rows, facts, rules, cases, case_records), and checks(con) -> [failures]
  generator/write_docs.py  write(con, out_dir): docs/spec.md, docs/planted-cases.md, docs/about.html and packs/
  generator/common/        names, UK formats, the firm, standard tables, page layout, theme.css
  generator/release.py     dataset name, version and release date for document footers

Writes db/<name>.sqlite and db/seed.sql, runs the checks, then the documents, then generator/common/publish.py
(canary, HTML versions of the Markdown documents, README.md). Exits non-zero if any check fails.
"""

import hashlib
import os
import random
import shutil
import sqlite3
import sys

sys.dont_write_bytecode = True  # keep __pycache__ out of the dataset folder

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the dataset folder
sys.path.insert(0, ROOT)

from generator import release, scenario, write_docs  # noqa: E402
from generator.common import dataset, firm, publish  # noqa: E402


def generic_checks(con):
    errors = []
    for row in con.execute("PRAGMA foreign_key_check"):
        errors.append(f"foreign key broken: {row}")
    pk = {r[0]: r[1] for r in con.execute("SELECT table_name, primary_key FROM _meta_tables")}
    for case_id, table, rec in con.execute("SELECT case_id, table_name, record_id FROM _truth_case_records"):
        if not con.execute(f'SELECT 1 FROM "{table}" WHERE "{pk[table]}" = ?', (rec,)).fetchone():
            errors.append(f"{case_id}: {table} {rec} does not exist")
    for case_id, sql in con.execute("SELECT case_id, detection_sql FROM _truth_cases"):
        found = {r[0] for r in con.execute(sql)}
        expected = {r[0] for r in con.execute(
            "SELECT record_id FROM _truth_case_records WHERE case_id = ? AND is_key_record = 1", (case_id,))}
        if found != expected:
            errors.append(f"{case_id}: detection query found {sorted(found)}, answer key says {sorted(expected)}")
    return errors


def main():
    name = release.DATASET
    rng = random.Random(firm.SEED)
    schema, rows, facts, rules, cases, case_records = scenario.build(rng)
    tables, rows = dataset.assemble(schema, rows, facts, rules, cases, case_records)
    db_path, sql_path = dataset.write(os.path.join(ROOT, "db"), name, tables, rows)

    con = sqlite3.connect(db_path)
    errors = generic_checks(con) + scenario.checks(con)
    for t in tables:
        n = con.execute(f'SELECT count(*) FROM "{t.name}"').fetchone()[0]
        print(f"  {t.name:<24} {n:>5} rows")
    if errors:
        print(f"\n{len(errors)} check(s) failed:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    write_docs.write(con, ROOT)
    errors = publish.publish(con, ROOT, release)
    if errors:
        print("\n" + "\n".join("  - " + e for e in errors))
        sys.exit(1)
    shutil.copyfile(os.path.join(ROOT, "generator", "common", "theme.css"), os.path.join(ROOT, "docs", "theme.css"))
    con.close()
    digest = hashlib.sha256(open(sql_path, "rb").read()).hexdigest()[:16]
    print(f"\nAll checks passed. seed.sql sha256 {digest}")


if __name__ == "__main__":
    main()
