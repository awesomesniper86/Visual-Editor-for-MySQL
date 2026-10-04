from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTableWidget, QComboBox, QCheckBox, QMessageBox, QDialogButtonBox
)

COLUMN_TYPES = [
    "INT", "BIGINT", "SMALLINT", "TINYINT", "DECIMAL", "FLOAT", "DOUBLE",
    "VARCHAR", "CHAR", "TEXT", "DATE", "DATETIME", "TIMESTAMP", "BOOLEAN",
]
TYPES_WITH_LENGTH = {"VARCHAR", "CHAR", "DECIMAL"}


class CreateTableDialog(QDialog):
    """Define a new table's columns without writing CREATE TABLE by hand.
    Call exec(); on an accepted result, get_result() returns (table_name, columns)."""

    COLS = ["Name", "Type", "Length", "Nullable", "Primary Key", "Auto Inc.", "Default"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Table")
        self.setMinimumSize(680, 360)
        self._result = None

        self.table_name_edit = QLineEdit()

        self.grid = QTableWidget(0, len(self.COLS))
        self.grid.setHorizontalHeaderLabels(self.COLS)
        self.grid.horizontalHeader().setStretchLastSection(True)

        add_row_button = QPushButton("Add Column")
        add_row_button.clicked.connect(self._add_column_row)
        remove_row_button = QPushButton("Remove Selected")
        remove_row_button.clicked.connect(self._remove_selected_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Table name:"))
        name_row.addWidget(self.table_name_edit)
        layout.addLayout(name_row)

        layout.addWidget(self.grid)

        row_buttons = QHBoxLayout()
        row_buttons.addWidget(add_row_button)
        row_buttons.addWidget(remove_row_button)
        row_buttons.addStretch()
        layout.addLayout(row_buttons)

        layout.addWidget(buttons)

        self._add_column_row()  # start with one blank row so the dialog isn't empty

    def _add_column_row(self):
        row = self.grid.rowCount()
        self.grid.insertRow(row)

        self.grid.setCellWidget(row, 0, QLineEdit())

        type_combo = QComboBox()
        type_combo.addItems(COLUMN_TYPES)
        self.grid.setCellWidget(row, 1, type_combo)

        length_edit = QLineEdit()
        length_edit.setPlaceholderText("e.g. 255")
        self.grid.setCellWidget(row, 2, length_edit)

        nullable_check = QCheckBox()
        nullable_check.setChecked(True)
        self.grid.setCellWidget(row, 3, nullable_check)

        self.grid.setCellWidget(row, 4, QCheckBox())
        self.grid.setCellWidget(row, 5, QCheckBox())

        default_edit = QLineEdit()
        default_edit.setPlaceholderText("optional")
        self.grid.setCellWidget(row, 6, default_edit)

    def _remove_selected_row(self):
        row = self.grid.currentRow()
        if row >= 0:
            self.grid.removeRow(row)

    def _on_accept(self):
        table_name = self.table_name_edit.text().strip()
        if not table_name:
            QMessageBox.warning(self, "Missing name", "Enter a table name.")
            return

        columns = []
        for row in range(self.grid.rowCount()):
            name = self.grid.cellWidget(row, 0).text().strip()
            if not name:
                continue  # skip blank rows rather than erroring on them
            col_type = self.grid.cellWidget(row, 1).currentText()
            length = self.grid.cellWidget(row, 2).text().strip()
            if length and col_type not in TYPES_WITH_LENGTH:
                length = ""  # this type doesn't take a length -- ignore a stray value

            columns.append({
                "name": name,
                "type": col_type,
                "length": length or None,
                "nullable": self.grid.cellWidget(row, 3).isChecked(),
                "primary_key": self.grid.cellWidget(row, 4).isChecked(),
                "auto_increment": self.grid.cellWidget(row, 5).isChecked(),
                "default": self.grid.cellWidget(row, 6).text().strip() or None,
            })

        if not columns:
            QMessageBox.warning(self, "No columns", "Add at least one column.")
            return

        self._result = (table_name, columns)
        self.accept()

    def get_result(self):
        """Returns (table_name, columns) after an accepted dialog, else None."""
        return self._result
