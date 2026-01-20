MIGRATION_ID = '0002_enforce_user_id_not_null'

def upgrade(conn):
    null_sessions = conn.execute('SELECT COUNT(*) AS count FROM sessions WHERE user_id IS NULL').fetchone()['count']
    null_journals = conn.execute('SELECT COUNT(*) AS count FROM journal_entries WHERE user_id IS NULL').fetchone()['count']
    if null_sessions or null_journals:
        raise RuntimeError('Cannot enforce NOT NULL user_id with existing NULL rows.')

    conn.execute('PRAGMA foreign_keys = OFF')

    conn.execute(
        'CREATE TABLE sessions_new ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'session_type TEXT NOT NULL, '
        'session_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, '
        'subjective_feel INTEGER CHECK(subjective_feel >= 1 AND subjective_feel <= 5), '
        'user_id INTEGER NOT NULL, '
        'FOREIGN KEY (user_id) REFERENCES users (id)'
        ')'
    )
    conn.execute(
        'INSERT INTO sessions_new (id, session_type, session_date, subjective_feel, user_id) '
        'SELECT id, session_type, session_date, subjective_feel, user_id FROM sessions'
    )
    conn.execute('DROP TABLE sessions')
    conn.execute('ALTER TABLE sessions_new RENAME TO sessions')

    conn.execute(
        'CREATE TABLE journal_entries_new ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'entry_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, '
        'course_id INTEGER, '
        'notes_before_round TEXT, '
        'notes_after_round TEXT, '
        'mental_state TEXT, '
        'physical_state TEXT, '
        'weather TEXT, '
        'user_id INTEGER NOT NULL, '
        'FOREIGN KEY (course_id) REFERENCES courses (id), '
        'FOREIGN KEY (user_id) REFERENCES users (id)'
        ')'
    )
    conn.execute(
        'INSERT INTO journal_entries_new (id, entry_date, course_id, notes_before_round, notes_after_round, mental_state, physical_state, weather, user_id) '
        'SELECT id, entry_date, course_id, notes_before_round, notes_after_round, mental_state, physical_state, weather, user_id '
        'FROM journal_entries'
    )
    conn.execute('DROP TABLE journal_entries')
    conn.execute('ALTER TABLE journal_entries_new RENAME TO journal_entries')

    conn.execute('PRAGMA foreign_keys = ON')
    conn.commit()
