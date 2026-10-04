from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QVBoxLayout, QLabel, QMessageBox, QSpinBox
)

from app.config import credentials_store
from app.db.connection import ConnectionError as DBConnectionError


class LoginPage(QWidget):
    """Host/port/user/password form, with saved-profile recall and a
    "Save this connection" checkbox that stores the profile via
    credentials_store (password goes to the OS keyring)."""

    def __init__(self, connection, on_connected):
        super().__init__()
        self.connection = connection
        self.on_connected = on_connected

        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self._profile_chosen)
        self._refresh_profile_list()

        self.host_edit = QLineEdit("127.0.0.1")
        self.port_edit = QSpinBox()
        self.port_edit.setRange(1, 65535)
        self.port_edit.setValue(3306)
        self.user_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)

        self.save_checkbox = QCheckBox("Save this connection")
        self.profile_name_edit = QLineEdit()
        self.profile_name_edit.setPlaceholderText("Name for this saved connection")
        self.profile_name_edit.setEnabled(False)
        self.save_checkbox.toggled.connect(self.profile_name_edit.setEnabled)

        form = QFormLayout()
        form.addRow("Saved connections:", self.profile_combo)
        form.addRow("Host:", self.host_edit)
        form.addRow("Port:", self.port_edit)
        form.addRow("Username:", self.user_edit)
        form.addRow("Password:", self.password_edit)
        form.addRow(self.save_checkbox, self.profile_name_edit)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.attempt_connect)

        layout = QVBoxLayout(self)
        layout.addStretch()
        title = QLabel("Connect to MySQL Server")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(self.connect_button)
        layout.addStretch()

    def _refresh_profile_list(self, select_name=None):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem("-- New connection --", None)
        for p in credentials_store.load_profiles():
            self.profile_combo.addItem(p["name"], p)
        if select_name:
            idx = self.profile_combo.findText(select_name)
            if idx >= 0:
                self.profile_combo.setCurrentIndex(idx)
        self.profile_combo.blockSignals(False)

    def _profile_chosen(self, index):
        data = self.profile_combo.itemData(index)
        if not data:
            return
        self.host_edit.setText(data["host"])
        self.port_edit.setValue(int(data["port"]))
        self.user_edit.setText(data["username"])
        password = credentials_store.get_password(data["name"], data["host"], data["port"], data["username"])
        if password:
            self.password_edit.setText(password)
        self.save_checkbox.setChecked(True)
        self.profile_name_edit.setText(data["name"])

    def attempt_connect(self):
        host = self.host_edit.text().strip()
        port = self.port_edit.value()
        user = self.user_edit.text().strip()
        password = self.password_edit.text()

        if not host or not user:
            QMessageBox.warning(self, "Missing info", "Host and username are required.")
            return

        try:
            self.connection.connect(host, port, user, password)
        except DBConnectionError as e:
            QMessageBox.critical(self, "Connection failed", str(e))
            return

        if self.save_checkbox.isChecked():
            name = self.profile_name_edit.text().strip() or f"{user}@{host}"
            credentials_store.save_profile(name, host, port, user, password)
            self._refresh_profile_list(select_name=name)

        self.on_connected()
