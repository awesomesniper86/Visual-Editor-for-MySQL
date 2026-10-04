"""Read-only lookups: databases, tables, column schema.

Identifiers returned here (database/table/column names) come straight from the
server via SHOW/DESCRIBE, so they're safe to splice into SQL with backtick
quoting elsewhere in the app. Never splice raw free-typed text as an identifier.
"""

SYSTEM_DATABASES = {"information_schema", "performance_schema", "mysql", "sys"}


def list_databases(connection):
    """Returns (user_databases, system_databases) as two lists of names."""
    _, rows = connection.execute("SHOW DATABASES")
    names = [r[0] for r in rows]
    user_dbs = [n for n in names if n not in SYSTEM_DATABASES]
    system_dbs = [n for n in names if n in SYSTEM_DATABASES]
    return user_dbs, system_dbs


def list_tables(connection):
    _, rows = connection.execute("SHOW TABLES")
    return [r[0] for r in rows]


def describe_table(connection, table_name):
    """Returns a list of dicts: field, type, null, key, default, extra."""
    _, rows = connection.execute(f"DESCRIBE `{table_name}`")
    result = []
    for r in rows:
        result.append({
            "field": r[0],
            "type": r[1],
            "null": r[2],
            "key": r[3],
            "default": r[4],
            "extra": r[5],
        })
    return result


def get_primary_key_columns(connection, table_name):
    desc = describe_table(connection, table_name)
    return [d["field"] for d in desc if d["key"] == "PRI"]


def list_tables_in(connection, database):
    """Lists tables in `database` without switching the connection's active
    database (unlike list_tables, which uses whatever's currently selected)."""
    _, rows = connection.execute(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME",
        [database],
    )
    return [r[0] for r in rows]


def list_users(connection):
    """Returns a sorted list of (user, host) tuples from mysql.user. Requires
    a user with privileges to read that table (root always can)."""
    _, rows = connection.execute("SELECT User, Host FROM mysql.user ORDER BY User, Host")
    return [(r[0], r[1]) for r in rows]


def get_grants(connection, username, host):
    """Returns SHOW GRANTS FOR <user>@<host> as a list of strings."""
    _, rows = connection.execute("SHOW GRANTS FOR %s@%s", [username, host])
    return [r[0] for r in rows]
