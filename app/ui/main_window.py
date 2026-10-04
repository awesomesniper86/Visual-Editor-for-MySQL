from PySide6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox, QInputDialog, QLineEdit
from PySide6.QtGui import QAction

from app.db.connection import MySQLConnection, ConnectionError as DBConnectionError
from app.db import introspect, query_builder
from app.version import __version__
from app.ui.login_page import LoginPage
from app.ui.db_browser_page import DatabaseBrowserPage
from app.ui.table_browser_page import TableBrowserPage
from app.ui.table_view_page import TableViewPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"MySQL DB Manager v{__version__}")

        self.connection = MySQLConnection()
        self.current_database = None
        self.current_table = None

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_page = LoginPage(self.connection, self.on_connected)
        self.db_browser_page = DatabaseBrowserPage(self.on_database_selected, self.on_create_database)
        self.table_browser_page = TableBrowserPage(self.on_table_selected, self.on_create_table)
        self.table_view_page = TableViewPage(self.connection)

        for page in (self.login_page, self.db_browser_page, self.table_browser_page, self.table_view_page):
            self.stack.addWidget(page)
        self.stack.setCurrentWidget(self.login_page)

        self._build_menu()
        self._update_menu_state()

    # ---------------------------------------------------------------- menu --

    def _build_menu(self):
        menubar = self.menuBar()

        account_menu = menubar.addMenu("&Account")

        self.action_new_user = QAction("Create New User...", self)
        self.action_new_user.triggered.connect(self.create_new_user)
        account_menu.addAction(self.action_new_user)

        self.action_switch_user = QAction("Switch User / Reconnect...", self)
        self.action_switch_user.triggered.connect(self.switch_user)
        account_menu.addAction(self.action_switch_user)

        account_menu.addSeparator()
        self.action_disconnect = QAction("Disconnect", self)
        self.action_disconnect.triggered.connect(self.disconnect)
        account_menu.addAction(self.action_disconnect)

        nav_menu = menubar.addMenu("&Navigate")

        self.action_switch_db = QAction("Switch Database...", self)
        self.action_switch_db.triggered.connect(self.switch_database)
        nav_menu.addAction(self.action_switch_db)

        self.action_switch_table = QAction("Switch Table...", self)
        self.action_switch_table.triggered.connect(self.switch_table)
        nav_menu.addAction(self.action_switch_table)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _update_menu_state(self):
        connected = self.connection.is_connected()
        has_db = connected and self.current_database is not None
        is_root = connected and self.connection.is_root()

        self.action_new_user.setEnabled(is_root)
        self.action_switch_user.setEnabled(connected)
        self.action_disconnect.setEnabled(connected)
        self.action_switch_db.setEnabled(connected)
        self.action_switch_table.setEnabled(has_db)

    # ----------------------------------------------------------- callbacks --

    def on_connected(self):
        self._update_menu_state()
        try:
            user_dbs, system_dbs = introspect.list_databases(self.connection)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not list databases:\n{e}")
            return
        self.db_browser_page.set_databases(user_dbs, system_dbs)
        self.stack.setCurrentWidget(self.db_browser_page)

    def on_database_selected(self, db_name):
        try:
            self.connection.use_database(db_name)
            tables = introspect.list_tables(self.connection)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open database '{db_name}':\n{e}")
            return
        self.current_database = db_name
        self.current_table = None
        self._update_menu_state()
        self.table_browser_page.set_tables(tables)
        self.stack.setCurrentWidget(self.table_browser_page)

    def on_create_database(self, name):
        try:
            sql, params = query_builder.build_create_database(name)
            self.connection.execute(sql, params, fetch=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create database:\n{e}")
            return
        try:
            user_dbs, system_dbs = introspect.list_databases(self.connection)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Database created, but could not refresh the list:\n{e}")
            return
        self.db_browser_page.set_databases(user_dbs, system_dbs)

    def on_create_table(self, table_name, columns):
        try:
            sql, params = query_builder.build_create_table(table_name, columns)
            self.connection.execute(sql, params, fetch=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create table:\n{e}")
            return
        try:
            tables = introspect.list_tables(self.connection)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Table created, but could not refresh the list:\n{e}")
            return
        self.table_browser_page.set_tables(tables)

    def on_table_selected(self, table_name):
        try:
            self.table_view_page.load_table(table_name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open table '{table_name}':\n{e}")
            return
        self.current_table = table_name
        self.stack.setCurrentWidget(self.table_view_page)

    def switch_database(self):
        try:
            user_dbs, system_dbs = introspect.list_databases(self.connection)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not list databases:\n{e}")
            return
        self.db_browser_page.set_databases(user_dbs, system_dbs)
        self.stack.setCurrentWidget(self.db_browser_page)

    def switch_table(self):
        try:
            tables = introspect.list_tables(self.connection)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not list tables:\n{e}")
            return
        self.table_browser_page.set_tables(tables)
        self.stack.setCurrentWidget(self.table_browser_page)

    def switch_user(self):
        self.connection.disconnect()
        self.current_database = None
        self.current_table = None
        self._update_menu_state()
        self.stack.setCurrentWidget(self.login_page)

    def disconnect(self):
        self.connection.disconnect()
        self.current_database = None
        self.current_table = None
        self._update_menu_state()
        self.stack.setCurrentWidget(self.login_page)

    def show_about(self):
        QMessageBox.information(self, "About", f"MySQL DB Manager\nVersion {__version__}")

    def create_new_user(self):
        username, ok = QInputDialog.getText(self, "Create New User", "Username:")
        if not ok or not username:
            return
        host, ok = QInputDialog.getText(self, "Create New User", "Host (use % for any host):", text="%")
        if not ok:
            return
        password, ok = QInputDialog.getText(self, "Create New User", "Password:", QLineEdit.Password)
        if not ok:
            return

        sql, params = query_builder.build_create_user(username, host, password)
        try:
            self.connection.execute(sql, params, fetch=False)
            QMessageBox.information(self, "Success", f"User '{username}'@'{host}' created.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create user:\n{e}")
