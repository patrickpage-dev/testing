DROP TABLE IF EXISTS drills;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS journal_entries;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS holes;
DROP TABLE IF EXISTS scores;

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_type TEXT NOT NULL,
    session_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subjective_feel INTEGER CHECK(subjective_feel >= 1 AND subjective_feel <= 5)
);

CREATE TABLE drills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    drill_name TEXT NOT NULL,
    club TEXT,
    target_distance INTEGER,
    balls_hit INTEGER,
    success_metric TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions (id)
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    par INTEGER,
    course_rating REAL,
    slope INTEGER
);

CREATE TABLE holes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    hole_number INTEGER NOT NULL CHECK(hole_number >= 1 AND hole_number <= 18),
    par INTEGER NOT NULL,
    UNIQUE(course_id, hole_number),
    FOREIGN KEY (course_id) REFERENCES courses (id)
);

CREATE TABLE journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    course_id INTEGER,
    notes_before_round TEXT,
    notes_after_round TEXT,
    mental_state TEXT,
    physical_state TEXT,
    weather TEXT,
    FOREIGN KEY (course_id) REFERENCES courses (id)
);

CREATE TABLE scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_entry_id INTEGER NOT NULL,
    hole_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    UNIQUE(journal_entry_id, hole_id),
    FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id),
    FOREIGN KEY (hole_id) REFERENCES holes (id)
);