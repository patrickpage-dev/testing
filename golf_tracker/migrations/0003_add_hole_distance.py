MIGRATION_ID = '0003_add_hole_distance'

def column_exists(conn, table_name, column_name):
    columns = conn.execute(f'PRAGMA table_info({table_name})').fetchall()
    return any(column['name'] == column_name for column in columns)

def upgrade(conn):
    if not column_exists(conn, 'holes', 'distance'):
        conn.execute('ALTER TABLE holes ADD COLUMN distance INTEGER')
    conn.commit()