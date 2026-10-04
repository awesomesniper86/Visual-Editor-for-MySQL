"""Turns form input (dicts of column -> value) into parameterized SQL.

Most column/table names here are expected to come from introspect.py (i.e.
from the server itself), so backtick-quoting them is safe. Values always
travel as query parameters (%s), never string-formatted into the SQL text.

CREATE DATABASE / CREATE TABLE are the exception: the names involved are
freshly typed by the user, not read back from the server, and MySQL has no
way to parameterize an identifier (a table or column name) the way it does a
value -- %s only works for values. So build_create_database/build_create_table
validate every name themselves (validate_identifier) before it ever touches
an f-string, instead of relying on parameterization.
"""

import re

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")

_NUMERIC_TYPES = {"INT", "BIGINT", "SMALLINT", "TINYINT", "DECIMAL", "FLOAT", "DOUBLE", "BOOLEAN"}
_KEYWORD_DEFAULTS = {"CURRENT_TIMESTAMP", "NULL", "TRUE", "FALSE"}

VALID_PRIVILEGES = {
    "ALL PRIVILEGES", "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP",
    "ALTER", "INDEX", "REFERENCES", "EXECUTE", "CREATE VIEW", "SHOW VIEW", "TRIGGER",
}


def validate_identifier(name, kind="identifier"):
    """Raises ValueError if `name` isn't safe to splice into DDL as an
    identifier. Letters/numbers/underscore only, must not start with a digit."""
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(
            f"'{name}' isn't a valid {kind} name. Use only letters, numbers, "
            f"and underscores, and don't start with a number."
        )


def _format_default(value, col_type):
    upper = value.strip().upper()
    if upper in _KEYWORD_DEFAULTS:
        return upper
    base_type = col_type.split("(")[0].upper()
    if base_type in _NUMERIC_TYPES:
        try:
            float(value)
            return value
        except ValueError:
            pass  # not actually numeric -- fall through and quote it
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def build_insert(table, column_values):
    columns = list(column_values.keys())
    col_list = ", ".join(f"`{c}`" for c in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"
    return sql, list(column_values.values())


def build_update(table, column_values, where_column_values):
    set_clause = ", ".join(f"`{c}` = %s" for c in column_values)
    where_clause = " AND ".join(f"`{c}` = %s" for c in where_column_values)
    sql = f"UPDATE `{table}` SET {set_clause} WHERE {where_clause}"
    params = list(column_values.values()) + list(where_column_values.values())
    return sql, params


def build_delete(table, where_column_values):
    where_clause = " AND ".join(f"`{c}` = %s" for c in where_column_values)
    sql = f"DELETE FROM `{table}` WHERE {where_clause}"
    return sql, list(where_column_values.values())


def build_create_user(username, host, password):
    sql = "CREATE USER %s@%s IDENTIFIED BY %s"
    return sql, [username, host, password]


def build_grant(username, host, privileges, database="*", table="*"):
    """database/table may be "*" for "all databases"/"all tables"; anything
    else is validated as an identifier before being backtick-quoted, since
    MySQL can't take a placeholder for an identifier the way it can for a
    value. privileges is checked against a fixed whitelist for the same
    reason -- it's spliced into the statement text, not passed as a param."""
    if not privileges:
        raise ValueError("Select at least one privilege to grant.")
    for p in privileges:
        if p not in VALID_PRIVILEGES:
            raise ValueError(f"'{p}' isn't a recognized privilege.")
    priv_list = ", ".join(privileges)

    if database == "*":
        db_target = "*"
    else:
        validate_identifier(database, "database")
        db_target = f"`{database}`"

    if table == "*":
        table_target = "*"
    else:
        validate_identifier(table, "table")
        table_target = f"`{table}`"

    sql = f"GRANT {priv_list} ON {db_target}.{table_target} TO %s@%s"
    return sql, [username, host]


def build_flush_privileges():
    return "FLUSH PRIVILEGES", []


def build_create_database(name):
    validate_identifier(name, "database")
    return f"CREATE DATABASE `{name}`", []


def build_create_table(table, columns):
    """columns: list of dicts with keys name, type, length (optional),
    nullable, primary_key, auto_increment, default (optional)."""
    validate_identifier(table, "table")
    if not columns:
        raise ValueError("A table needs at least one column.")

    col_defs = []
    pk_cols = []
    for c in columns:
        validate_identifier(c["name"], "column")
        type_sql = c["type"]
        if c.get("length"):
            type_sql += f"({c['length']})"

        parts = [f"`{c['name']}`", type_sql]
        if not c.get("nullable", True):
            parts.append("NOT NULL")
        if c.get("auto_increment"):
            parts.append("AUTO_INCREMENT")
        default_val = c.get("default")
        if default_val not in (None, ""):
            parts.append(f"DEFAULT {_format_default(default_val, c['type'])}")

        col_defs.append(" ".join(parts))
        if c.get("primary_key"):
            pk_cols.append(c["name"])

    if pk_cols:
        pk_clause = ", ".join(f"`{p}`" for p in pk_cols)
        col_defs.append(f"PRIMARY KEY ({pk_clause})")

    sql = f"CREATE TABLE `{table}` (\n  " + ",\n  ".join(col_defs) + "\n)"
    return sql, []
