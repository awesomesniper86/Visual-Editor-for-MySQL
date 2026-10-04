"""Thin wrapper around mysql-connector-python for the app's single live connection."""

import mysql.connector
from mysql.connector import Error as MySQLError


class ConnectionError(Exception):
    """Raised for any connect/query failure we want the UI to show to the user."""
    pass


class MySQLConnection:
    def __init__(self):
        self.conn = None
        self.host = None
        self.port = None
        self.user = None

    def connect(self, host, port, user, password, database=None, timeout=5):
        try:
            self.conn = mysql.connector.connect(
                host=host,
                port=int(port),
                user=user,
                password=password,
                database=database,
                connection_timeout=timeout,
                autocommit=True,
            )
            self.host, self.port, self.user = host, port, user
            return True
        except MySQLError as e:
            raise ConnectionError(str(e)) from e

    def is_connected(self):
        return self.conn is not None and self.conn.is_connected()

    def disconnect(self):
        if self.conn is not None:
            try:
                self.conn.close()
            finally:
                self.conn = None
                self.host = self.port = self.user = None

    def use_database(self, name):
        if not self.is_connected():
            raise ConnectionError("Not connected to a MySQL server.")
        try:
            self.conn.database = name
        except MySQLError as e:
            raise ConnectionError(str(e)) from e

    def execute(self, query, params=None, dictionary=False, fetch=True):
        """Run one statement. Returns (columns, rows); rows/columns are empty for
        statements with no result set (INSERT/UPDATE/DELETE/CREATE USER/etc.)."""
        if not self.is_connected():
            raise ConnectionError("Not connected to a MySQL server.")
        cur = self.conn.cursor(dictionary=dictionary)
        try:
            cur.execute(query, params or ())
            if fetch and cur.with_rows:
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description] if cur.description else []
                return cols, rows
            return [], []
        except MySQLError as e:
            raise ConnectionError(str(e)) from e
        finally:
            cur.close()

    def is_root(self):
        try:
            _, rows = self.execute("SELECT CURRENT_USER()")
            current_user = rows[0][0] if rows else ""
            return current_user.split("@")[0] == "root"
        except Exception:
            return False
