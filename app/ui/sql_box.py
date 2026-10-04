from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QLabel
)


class SqlBoxPage(QWidget):
    """Raw SQL escape hatch: type anything, run it, see results in a grid."""

    def __init__(self, connection):
        super().__init__()
        self.connection = connection

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Type any SQL statement and press Run...")

        run_button = QPushButton("Run")
        run_button.clicked.connect(self._run)

        self.status_label = QLabel()
        self.result_table = QTableWidget()

        layout = QVBoxLayout(self)
        layout.addWidget(self.editor)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(run_button)
        layout.addLayout(row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.result_table)

    def _run(self):
        sql = self.editor.toPlainText().strip()
        if not sql:
            return
        try:
            cols, rows = self.connection.execute(sql, fetch=True)
        except Exception as e:
            QMessageBox.critical(self, "Query failed", str(e))
            return

        if cols:
            self.result_table.setColumnCount(len(cols))
            self.result_table.setHorizontalHeaderLabels(cols)
            self.result_table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, value in enumerate(row):
                    self.result_table.setItem(r, c, QTableWidgetItem("" if value is None else str(value)))
            self.status_label.setText(f"{len(rows)} row(s) returned.")
        else:
            self.result_table.setRowCount(0)
            self.result_table.setColumnCount(0)
            self.status_label.setText("Statement executed.")
