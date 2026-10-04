from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QPushButton

from app.ui.create_table_dialog import CreateTableDialog


class TableBrowserPage(QWidget):
    """Lists SHOW TABLES output for the currently selected database.
    New Table... opens a column-definition dialog and hands the result
    off to on_create(table_name, columns)."""

    def __init__(self, on_selected, on_create):
        super().__init__()
        self.on_selected = on_selected
        self.on_create = on_create

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(lambda item: self.on_selected(item.text()))

        new_button = QPushButton("New Table...")
        new_button.clicked.connect(self._new_table)

        open_button = QPushButton("Open Table")
        open_button.clicked.connect(self._open_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select a table:"))
        layout.addWidget(self.list_widget)
        row = QHBoxLayout()
        row.addWidget(new_button)
        row.addStretch()
        row.addWidget(open_button)
        layout.addLayout(row)

    def set_tables(self, tables):
        self.list_widget.clear()
        for name in tables:
            self.list_widget.addItem(name)

    def _open_clicked(self):
        item = self.list_widget.currentItem()
        if item:
            self.on_selected(item.text())

    def _new_table(self):
        dialog = CreateTableDialog(self)
        if dialog.exec():
            table_name, columns = dialog.get_result()
            self.on_create(table_name, columns)
