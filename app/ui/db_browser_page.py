from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QPushButton, QInputDialog
)


class DatabaseBrowserPage(QWidget):
    """Lists SHOW DATABASES output; double-click or Open button selects one.
    New Database... prompts for a name and hands it off to on_create."""

    def __init__(self, on_selected, on_create):
        super().__init__()
        self.on_selected = on_selected
        self.on_create = on_create

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(lambda item: self._open(item.text()))

        new_button = QPushButton("New Database...")
        new_button.clicked.connect(self._new_database)

        open_button = QPushButton("Open Database")
        open_button.clicked.connect(self._open_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select a database:"))
        layout.addWidget(self.list_widget)
        row = QHBoxLayout()
        row.addWidget(new_button)
        row.addStretch()
        row.addWidget(open_button)
        layout.addLayout(row)

    def set_databases(self, user_dbs, system_dbs):
        self.list_widget.clear()
        for name in user_dbs:
            self.list_widget.addItem(name)
        if system_dbs:
            self.list_widget.addItem("── system databases ──")
            for name in system_dbs:
                self.list_widget.addItem(name)

    def _open_clicked(self):
        item = self.list_widget.currentItem()
        if item:
            self._open(item.text())

    def _open(self, name):
        if name.startswith("──"):
            return
        self.on_selected(name)

    def _new_database(self):
        name, ok = QInputDialog.getText(self, "New Database", "Database name:")
        if ok and name.strip():
            self.on_create(name.strip())
