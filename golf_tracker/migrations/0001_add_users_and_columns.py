MIGRATION_ID = '0001_add_users_and_columns'

def column_exists(conn, table_name, column_name):
    columns = conn.execute(f'PRAGMA table_info({table_name})').fetchall()
    return any(column['name'] == column_name for column in columns)

def table_exists(conn, table_name):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,)
    ).fetchone()
    return row is not None

def upgrade(conn):
    if not column_exists(conn, 'courses', 'website_url'):
        conn.execute('ALTER TABLE courses ADD COLUMN website_url TEXT')

    if not column_exists(conn, 'sessions', 'user_id'):
        conn.execute('ALTER TABLE sessions ADD COLUMN user_id INTEGER')

    if not column_exists(conn, 'journal_entries', 'user_id'):
        conn.execute('ALTER TABLE journal_entries ADD COLUMN user_id INTEGER')

    if not table_exists(conn, 'users'):
        conn.execute(
            'CREATE TABLE users ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'username TEXT NOT NULL UNIQUE, '
            'password_hash TEXT NOT NULL, '
            'is_admin INTEGER NOT NULL DEFAULT 0, '
            'created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP'
            ')'
        )
    elif not column_exists(conn, 'users', 'is_admin'):
        conn.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0')

    conn.commit()
