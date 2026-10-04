from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QTabWidget, QLabel,
    QMessageBox, QPushButton
)

from app.db.table_model import TableModel
from app.ui.command_panel import CommandPanel
from app.ui.sql_box import SqlBoxPage


class TableViewPage(QWidget):
    """The editable grid for one table, plus the guided command builder and
    the raw-SQL box, as tabs."""

    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.model = None

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectItems)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh)

        grid_container = QWidget()
        grid_layout = QVBoxLayout(grid_container)
        top_row = QHBoxLayout()
        top_row.addWidget(self.title_label)
        top_row.addStretch()
        top_row.addWidget(refresh_button)
        grid_layout.addLayout(top_row)
        grid_layout.addWidget(self.table_view)
        grid_layout.addWidget(QLabel(
            "Tip: edit any cell to update that row. Type into the bottom "
            "'*' row to add a new one -- it commits when you click elsewhere."
        ))

        self.command_panel = CommandPanel(self.connection, self._refresh)
        self.sql_box = SqlBoxPage(self.connection)

        self.tabs = QTabWidget()
        self.tabs.addTab(grid_container, "Table Data")
        self.tabs.addTab(self.command_panel, "Guided Commands")
        self.tabs.addTab(self.sql_box, "Raw SQL")

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

    def load_table(self, table_name):
        self.model = TableModel(self.connection, table_name)
        self.model.error_occurred.connect(lambda msg: QMessageBox.critical(self, "Error", msg))
        self.table_view.setModel(self.model)
        self.table_view.selectionModel().currentChanged.connect(self._on_current_changed)
        self.title_label.setText(f"Table: {table_name}")
        self.command_panel.set_table(table_name)

    def _on_current_changed(self, current, previous):
        # Commit a pending new-row edit once the user moves away from the
        # trailing blank row.
        if self.model is None or not previous.isValid():
            return
        last_row = self.model.rowCount() - 1
        if previous.row() == last_row and current.row() != last_row:
            self.model.commit_pending_row()

    def _refresh(self):
        if self.model is None:
            return
        try:
            self.model.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not refresh table:\n{e}")
