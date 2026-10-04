from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QPushButton,
    QLabel, QCheckBox, QPlainTextEdit, QMessageBox, QGridLayout, QDialogButtonBox
)

from app.db import introspect, query_builder

PRIVILEGE_OPTIONS = [
    "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER",
    "INDEX", "REFERENCES", "EXECUTE", "CREATE VIEW", "SHOW VIEW", "TRIGGER",
]


class PermissionsDialog(QDialog):
    """Root-only: grant privileges to a user on a database/table, and view
    a user's current grants. Like the guided command panel and raw SQL tab,
    this owns the connection and runs its own queries directly rather than
    routing everything back through MainWindow."""

    def __init__(self, connection, parent=None):
        super().__init__(parent)
        self.connection = connection
        self.setWindowTitle("Manage Permissions")
        self.setMinimumSize(580, 560)

        self.user_combo = QComboBox()
        self.user_combo.setEditable(True)
        self.host_combo = QComboBox()
        self.host_combo.setEditable(True)

        self.database_combo = QComboBox()
        self.database_combo.currentIndexChanged.connect(self._database_changed)
        self.table_combo = QComboBox()

        self.all_privileges_check = QCheckBox("ALL PRIVILEGES")
        self.all_privileges_check.toggled.connect(self._all_privileges_toggled)
        self.privilege_checks = {}
        priv_grid = QGridLayout()
        for i, priv in enumerate(PRIVILEGE_OPTIONS):
            check = QCheckBox(priv)
            self.privilege_checks[priv] = check
            priv_grid.addWidget(check, i // 3, i % 3)

        grant_button = QPushButton("Grant")
        grant_button.clicked.connect(self._grant)

        show_grants_button = QPushButton("Show Current Grants")
        show_grants_button.clicked.connect(self._show_grants)

        self.grants_display = QPlainTextEdit()
        self.grants_display.setReadOnly(True)
        self.grants_display.setPlaceholderText("Current grants for the selected user will appear here.")

        close_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_box.rejected.connect(self.accept)

        form = QFormLayout()
        form.addRow("User:", self.user_combo)
        form.addRow("Host:", self.host_combo)
        form.addRow("Database:", self.database_combo)
        form.addRow("Table:", self.table_combo)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.all_privileges_check)
        layout.addLayout(priv_grid)

        button_row = QHBoxLayout()
        button_row.addWidget(show_grants_button)
        button_row.addStretch()
        button_row.addWidget(grant_button)
        layout.addLayout(button_row)

        layout.addWidget(QLabel("Current grants:"))
        layout.addWidget(self.grants_display)
        layout.addWidget(close_box)

        self._load_users()
        self._load_databases()

    def _load_users(self):
        try:
            users = introspect.list_users(self.connection)
        except Exception as e:
            QMessageBox.warning(self, "Could not list users", str(e))
            users = []
        seen_users, seen_hosts = set(), set()
        for user, host in users:
            if user not in seen_users:
                self.user_combo.addItem(user)
                seen_users.add(user)
            if host not in seen_hosts:
                self.host_combo.addItem(host)
                seen_hosts.add(host)
        if self.host_combo.findText("%") < 0:
            self.host_combo.addItem("%")

    def _load_databases(self):
        self.database_combo.addItem("* (all databases)", "*")
        try:
            user_dbs, system_dbs = introspect.list_databases(self.connection)
        except Exception as e:
            QMessageBox.warning(self, "Could not list databases", str(e))
            return
        for name in user_dbs + system_dbs:
            self.database_combo.addItem(name, name)

    def _database_changed(self):
        self.table_combo.clear()
        self.table_combo.addItem("* (all tables)", "*")
        db = self.database_combo.currentData()
        if not db or db == "*":
            self.table_combo.setEnabled(False)
            return
        self.table_combo.setEnabled(True)
        try:
            tables = introspect.list_tables_in(self.connection, db)
        except Exception as e:
            QMessageBox.warning(self, "Could not list tables", str(e))
            return
        for t in tables:
            self.table_combo.addItem(t, t)

    def _all_privileges_toggled(self, checked):
        for check in self.privilege_checks.values():
            check.setEnabled(not checked)

    def _selected_privileges(self):
        if self.all_privileges_check.isChecked():
            return ["ALL PRIVILEGES"]
        return [priv for priv, check in self.privilege_checks.items() if check.isChecked()]

    def _grant(self):
        username = self.user_combo.currentText().strip()
        host = self.host_combo.currentText().strip() or "%"
        database = self.database_combo.currentData() or "*"
        table = self.table_combo.currentData() or "*"
        privileges = self._selected_privileges()

        if not username:
            QMessageBox.warning(self, "Missing user", "Enter or select a username.")
            return
        if not privileges:
            QMessageBox.warning(self, "No privileges selected", "Check at least one privilege (or ALL PRIVILEGES).")
            return

        scope = "every database" if database == "*" else f"{database}.{table}"
        confirm = QMessageBox.question(
            self, "Confirm grant",
            f"Grant {', '.join(privileges)} on {scope} to '{username}'@'{host}'?",
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            sql, params = query_builder.build_grant(username, host, privileges, database, table)
            self.connection.execute(sql, params, fetch=False)
            flush_sql, flush_params = query_builder.build_flush_privileges()
            self.connection.execute(flush_sql, flush_params, fetch=False)
        except Exception as e:
            QMessageBox.critical(self, "Grant failed", str(e))
            return

        QMessageBox.information(
            self, "Success",
            f"Granted {', '.join(privileges)} on {scope} to '{username}'@'{host}'.",
        )
        self._show_grants()

    def _show_grants(self):
        username = self.user_combo.currentText().strip()
        host = self.host_combo.currentText().strip() or "%"
        if not username:
            QMessageBox.warning(self, "Missing user", "Enter or select a username.")
            return
        try:
            grants = introspect.get_grants(self.connection, username, host)
        except Exception as e:
            self.grants_display.setPlainText("")
            QMessageBox.critical(self, "Could not fetch grants", str(e))
            return
        self.grants_display.setPlainText("\n".join(grants))
