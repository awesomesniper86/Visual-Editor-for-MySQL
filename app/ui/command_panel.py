from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QFormLayout, QLineEdit,
    QPushButton, QMessageBox, QLabel, QScrollArea
)

from app.db import introspect, query_builder


class CommandPanel(QWidget):
    """Guided command builder: pick an action, fill labeled fields built from
    the table's own schema, hit Run -- builds and executes parameterized SQL.
    No hand-written INSERT/UPDATE/DELETE needed."""

    ACTIONS = ["INSERT", "UPDATE", "DELETE"]

    def __init__(self, connection, on_run):
        super().__init__()
        self.connection = connection
        self.on_run = on_run
        self.table_name = None
        self.columns_desc = []
        self.value_fields = {}
        self.where_fields = {}

        self.action_combo = QComboBox()
        self.action_combo.addItems(self.ACTIONS)
        self.action_combo.currentTextChanged.connect(self._rebuild_form)

        self.form_container = QWidget()
        self.form_layout = QFormLayout(self.form_container)

        run_button = QPushButton("Run Command")
        run_button.clicked.connect(self._run)

        scroll = QScrollArea()
        scroll.setWidget(self.form_container)
        scroll.setWidgetResizable(True)

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Action:"))
        top.addWidget(self.action_combo)
        top.addStretch()
        layout.addLayout(top)
        layout.addWidget(scroll)
        layout.addWidget(run_button)

    def set_table(self, table_name):
        self.table_name = table_name
        self.columns_desc = introspect.describe_table(self.connection, table_name)
        self._rebuild_form()

    def _clear_form(self):
        while self.form_layout.rowCount():
            self.form_layout.removeRow(0)
        self.value_fields = {}
        self.where_fields = {}

    def _rebuild_form(self):
        self._clear_form()
        if not self.table_name:
            return
        action = self.action_combo.currentText()
        pk_cols = [c["field"] for c in self.columns_desc if c["key"] == "PRI"]

        if action in ("INSERT", "UPDATE"):
            self.form_layout.addRow(QLabel("<b>Values</b>"))
            for c in self.columns_desc:
                field = QLineEdit()
                field.setPlaceholderText(c["type"])
                self.form_layout.addRow(f"{c['field']}:", field)
                self.value_fields[c["field"]] = field

        if action in ("UPDATE", "DELETE"):
            self.form_layout.addRow(QLabel("<b>Where (row to match)</b>"))
            where_cols = pk_cols if pk_cols else [c["field"] for c in self.columns_desc]
            for name in where_cols:
                field = QLineEdit()
                self.form_layout.addRow(f"{name} =", field)
                self.where_fields[name] = field

    @staticmethod
    def _collect(fields):
        result = {}
        for name, widget in fields.items():
            text = widget.text()
            if text != "":
                result[name] = text
        return result

    def _run(self):
        action = self.action_combo.currentText()
        try:
            if action == "INSERT":
                values = self._collect(self.value_fields)
                if not values:
                    QMessageBox.warning(self, "Nothing to insert", "Fill in at least one field.")
                    return
                sql, params = query_builder.build_insert(self.table_name, values)

            elif action == "UPDATE":
                values = self._collect(self.value_fields)
                where = self._collect(self.where_fields)
                if not values or not where:
                    QMessageBox.warning(self, "Missing info", "Fill in at least one value and the WHERE fields.")
                    return
                sql, params = query_builder.build_update(self.table_name, values, where)

            else:  # DELETE
                where = self._collect(self.where_fields)
                if not where:
                    QMessageBox.warning(self, "Missing info", "Fill in the WHERE fields.")
                    return
                confirm = QMessageBox.question(
                    self, "Confirm delete",
                    f"Delete row(s) from '{self.table_name}' matching {where}?",
                )
                if confirm != QMessageBox.Yes:
                    return
                sql, params = query_builder.build_delete(self.table_name, where)

            self.connection.execute(sql, params, fetch=False)
            QMessageBox.information(self, "Success", f"{action} completed.")
            self.on_run()
        except Exception as e:
            QMessageBox.critical(self, "Command failed", str(e))
