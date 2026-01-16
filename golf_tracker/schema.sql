DROP TABLE IF EXISTS drills;
DROP TABLE IF EXISTS sessions;

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