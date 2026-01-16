import sqlite3
from flask import Flask, render_template, request, g, redirect, url_for

DATABASE = 'instance/golf_tracker.db'

app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=DATABASE,
)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    print('Initialized the database.')

@app.route('/')
def index():
    db = get_db()
    sessions = db.execute(
        'SELECT id, session_type, session_date, subjective_feel'
        ' FROM sessions'
        ' ORDER BY session_date DESC'
    ).fetchall()
    return render_template('index.html', sessions=sessions)

@app.route('/add_session', methods=('GET', 'POST'))
def add_session():
    if request.method == 'POST':
        session_type = request.form['session_type']
        subjective_feel = request.form['subjective_feel']
        db = get_db()
        db.execute(
            'INSERT INTO sessions (session_type, subjective_feel)'
            ' VALUES (?, ?)',
            (session_type, subjective_feel)
        )
        db.commit()
        return redirect(url_for('index'))
    return render_template('add_session.html')

@app.route('/session/<int:session_id>/add_drill', methods=('GET', 'POST'))
def add_drill(session_id):
    if request.method == 'POST':
        drill_name = request.form['drill_name']
        club = request.form['club']
        target_distance = request.form['target_distance']
        balls_hit = request.form['balls_hit']
        success_metric = request.form['success_metric']

        db = get_db()
        db.execute(
            'INSERT INTO drills (session_id, drill_name, club, target_distance, balls_hit, success_metric)'
            ' VALUES (?, ?, ?, ?, ?, ?)',
            (session_id, drill_name, club, target_distance, balls_hit, success_metric)
        )
        db.commit()
        return redirect(url_for('index'))
    return render_template('add_drill.html', session_id=session_id)

@app.route('/session/<int:session_id>')
def session_details(session_id):
    db = get_db()
    session = db.execute(
        'SELECT id, session_type, session_date, subjective_feel'
        ' FROM sessions'
        ' WHERE id = ?',
        (session_id,)
    ).fetchone()
    drills = db.execute(
        'SELECT id, drill_name, club, target_distance, balls_hit, success_metric'
        ' FROM drills'
        ' WHERE session_id = ?'
        ' ORDER BY id DESC',
        (session_id,)
    ).fetchall()

    if session is None:
        # Handle case where session is not found
        return "Session not found", 404
    
    return render_template('session_details.html', session=session, drills=drills)

if __name__ == '__main__':
    app.run(debug=True)
