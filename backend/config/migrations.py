"""
Database migrations: idempotent schema upgrades that run on app startup.

Each migration checks whether it's needed before doing work, so it's safe
to re-run on every boot.
"""


def _has_legacy_operation_check(conn, table: str) -> bool:
    """Detect the old restrictive CHECK constraint on the operation column."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    if not row or not row[0]:
        return False
    sql = row[0]
    return "operation IN ('repair','replace','refinish','blend','overhaul','sublet','other')" in sql


def _drop_operation_check(conn, table: str, fk_parent_col: str) -> None:
    """
    Recreate `table` without the restrictive CHECK on `operation`.
    SQLite can't ALTER constraints, so we rebuild: rename → create new → copy → drop.
    `fk_parent_col` is the FK column name (estimate_id or ro_id).
    """
    cur = conn.cursor()

    # Get the column list from the existing table (preserves any future-added columns).
    cols_info = cur.execute(f"PRAGMA table_info({table})").fetchall()
    col_names = [c[1] for c in cols_info]
    col_list = ", ".join(col_names)

    parent_table = "estimates" if fk_parent_col == "estimate_id" else "repair_orders"
    extra_status = ""
    if table == "ro_lines":
        extra_status = (
            "status TEXT DEFAULT 'pending' "
            "CHECK(status IN ('pending','ordered','received','installed','complete')), "
            "assigned_tech_id INTEGER REFERENCES employees(id), "
            "vendor_id INTEGER REFERENCES vendors(id), "
        )

    new_sql = f"""
    CREATE TABLE {table}__new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {fk_parent_col} INTEGER NOT NULL REFERENCES {parent_table}(id) ON DELETE CASCADE,
        line_number INTEGER NOT NULL,
        line_type TEXT NOT NULL CHECK(line_type IN ('labor','part','paint','sublet','other')),
        operation TEXT,
        description TEXT NOT NULL,
        part_number TEXT,
        part_type TEXT CHECK(part_type IN ('OEM','aftermarket','used','reconditioned','remanufactured')),
        quantity REAL DEFAULT 1,
        labor_hours REAL DEFAULT 0,
        labor_rate REAL DEFAULT 0,
        paint_hours REAL DEFAULT 0,
        paint_rate REAL DEFAULT 0,
        part_price REAL DEFAULT 0,
        part_cost REAL DEFAULT 0,
        line_total REAL DEFAULT 0,
        is_supplement INTEGER DEFAULT 0,
        supplement_number INTEGER DEFAULT 0,
        {extra_status}
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """

    # Run inside a transaction; FKs OFF temporarily so the rebuild doesn't trip.
    cur.execute("PRAGMA foreign_keys = OFF")
    try:
        cur.execute(new_sql)

        # Build the column intersection so we don't break if either table has extra columns.
        new_cols_info = cur.execute(f"PRAGMA table_info({table}__new)").fetchall()
        new_col_names = {c[1] for c in new_cols_info}
        copy_cols = [c for c in col_names if c in new_col_names]
        copy_list = ", ".join(copy_cols)

        cur.execute(f"INSERT INTO {table}__new ({copy_list}) SELECT {copy_list} FROM {table}")
        cur.execute(f"DROP TABLE {table}")
        cur.execute(f"ALTER TABLE {table}__new RENAME TO {table}")
        conn.commit()
    finally:
        cur.execute("PRAGMA foreign_keys = ON")


def run_migrations(conn) -> None:
    """Run all pending migrations. Safe to call on every startup."""
    # Migration 001: drop restrictive operation CHECK on estimate_lines / ro_lines.
    if _has_legacy_operation_check(conn, "estimate_lines"):
        print("[migration] Removing restrictive operation CHECK on estimate_lines")
        _drop_operation_check(conn, "estimate_lines", "estimate_id")

    if _has_legacy_operation_check(conn, "ro_lines"):
        print("[migration] Removing restrictive operation CHECK on ro_lines")
        _drop_operation_check(conn, "ro_lines", "ro_id")
