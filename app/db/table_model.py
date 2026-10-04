"""QAbstractTableModel backing the editable grid.

- Editing an existing cell issues a parameterized UPDATE keyed on the table's
  primary key.
- The last row in the grid is always a blank "new row". Typing into its cells
  buffers values; moving focus away from that row (handled by the view)
  commits a parameterized INSERT and refreshes.
"""

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal

from app.db import introspect, query_builder


class TableModel(QAbstractTableModel):
    error_occurred = Signal(str)

    def __init__(self, connection, table_name, parent=None):
        super().__init__(parent)
        self.connection = connection
        self.table_name = table_name
        self.columns = []
        self.primary_keys = []
        self.rows = []
        self._pending_new_row = {}
        self.refresh()

    def refresh(self):
        desc = introspect.describe_table(self.connection, self.table_name)
        self.columns = [d["field"] for d in desc]
        self.primary_keys = [d["field"] for d in desc if d["key"] == "PRI"]
        _, rows = self.connection.execute(f"SELECT * FROM `{self.table_name}`")
        self.beginResetModel()
        self.rows = [list(r) for r in rows]
        self._pending_new_row = {}
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.rows) + 1  # +1 for the trailing blank "new row"

    def columnCount(self, parent=QModelIndex()):
        return len(self.columns)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.columns[section]
        return str(section + 1) if section < len(self.rows) else "*"

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        row, col = index.row(), index.column()
        if row < len(self.rows):
            value = self.rows[row][col]
            return "" if value is None else str(value)
        column_name = self.columns[col]
        return self._pending_new_row.get(column_name, "")

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole:
            return False
        row, col = index.row(), index.column()
        column_name = self.columns[col]

        if row < len(self.rows):
            old_value = self.rows[row][col]
            if (old_value is None and value == "") or str(old_value) == value:
                return False
            if not self.primary_keys:
                self.error_occurred.emit(
                    "This table has no primary key, so individual cells can't "
                    "be safely edited here. Use Raw SQL instead."
                )
                return False
            try:
                where_values = [self.rows[row][self.columns.index(pk)] for pk in self.primary_keys]
                where_clause = " AND ".join(f"`{pk}` = %s" for pk in self.primary_keys)
                sql = f"UPDATE `{self.table_name}` SET `{column_name}` = %s WHERE {where_clause}"
                self.connection.execute(sql, [value if value != "" else None] + where_values, fetch=False)
            except Exception as e:
                self.error_occurred.emit(str(e))
                return False
            self.rows[row][col] = value
            self.dataChanged.emit(index, index)
            return True

        # Editing the trailing blank "new row": buffer, don't hit the DB yet.
        if value == "":
            self._pending_new_row.pop(column_name, None)
        else:
            self._pending_new_row[column_name] = value
        self.dataChanged.emit(index, index)
        return True

    def has_pending_row(self):
        return bool(self._pending_new_row)

    def commit_pending_row(self):
        """Call when focus leaves the trailing blank row. No-op if it's empty."""
        if not self._pending_new_row:
            return
        sql, params = query_builder.build_insert(self.table_name, self._pending_new_row)
        try:
            self.connection.execute(sql, params, fetch=False)
        except Exception as e:
            self.error_occurred.emit(str(e))
            return
        self._pending_new_row = {}
        self.refresh()
