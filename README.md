# MySQL DB Manager

**Version:** 0.0.2

A desktop app (PySide6) for browsing and editing MySQL databases visually:
connect to a server, pick a database, pick a table, see it as an editable
grid, and either edit cells directly, use a guided form-based command
builder, or drop into raw SQL.

## Setup

```bash
cd mysql-db-manager
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run (as raw code, before compiling anything)

```bash
python main.py
```

This is the whole point of building it this way first -- test everything
here, make changes, re-run, until it's solid. Only then move to packaging.

## What's in here

```
app/
  db/
    connection.py     # connect/execute wrapper around mysql-connector-python
    introspect.py     # SHOW DATABASES / SHOW TABLES / DESCRIBE
    query_builder.py  # builds parameterized INSERT/UPDATE/DELETE/CREATE USER
    table_model.py     # the editable grid's data model
  ui/
    login_page.py        # host/port/user/password + saved profiles
    db_browser_page.py    # pick a database
    table_browser_page.py # pick a table
    table_view_page.py     # the grid + guided commands + raw SQL, as tabs
    command_panel.py       # the guided, form-based command builder
    sql_box.py              # raw SQL escape hatch
    main_window.py          # menu bar + page routing + app state
  config/
    credentials_store.py  # saved profiles (JSON) + passwords (OS keyring)
main.py                  # entry point
```

## Using it

1. **Connect**: fill in host/port/username/password. Check "Save this
   connection" to store it -- the password goes into your OS's secure
   credential store (Windows Credential Manager / Linux Secret Service via
   the `keyring` library), never into a plain text file.
2. **Pick a database**, then **pick a table**. Each list also has a
   **New Database...** / **New Table...** button -- the latter opens a
   dialog where you define columns (name, type, length, nullable, primary
   key, auto-increment, default) and it builds the `CREATE TABLE` for you.
3. **Table Data tab**: the grid shows the table live. Edit any existing cell
   and it commits as an `UPDATE` as soon as you move off it. Type into the
   bottom row (marked `*`) to add a new row -- it commits as an `INSERT` once
   you click away from it.
4. **Guided Commands tab**: pick INSERT/UPDATE/DELETE, fill in the labeled
   fields (built from the table's own columns), hit Run. No SQL typing
   required.
5. **Raw SQL tab**: type anything and run it, for when you need something
   the guided builder doesn't cover.
6. **Menu bar**: Account menu has Create New User (only enabled when logged
   in as root), Switch User/Reconnect, and Disconnect. Navigate menu lets you
   jump back to pick a different database or table at any time.

## Notes / things worth knowing

- Editing a cell only works on tables that have a primary key (needed to
  target the right row for the `UPDATE`). Tables without one will show an
  error if you try to edit a cell -- use the Raw SQL tab for those.
- `CREATE USER` requires appropriate privileges on the server (typically
  root, or any account granted `CREATE USER`).
- All identifiers (database/table/column names) used in generated SQL come
  from the server itself (`SHOW DATABASES`/`SHOW TABLES`/`DESCRIBE`), and all
  values are sent as query parameters -- never string-concatenated -- so
  normal use doesn't risk SQL injection.

## Packaging (after you've tested everything above)

Build on each target OS separately -- PyInstaller doesn't cross-compile.

**Windows** (run on a Windows machine):
```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name MySQLDBManager main.py
```

**Ubuntu** (run on an Ubuntu machine):
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name MySQLDBManager main.py
```

Either way the binary lands in `dist/`. If PyInstaller complains about
missing Qt plugins, add `--collect-all PySide6` to the command.
