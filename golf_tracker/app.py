import sqlite3
import csv
import io
from flask import Flask, render_template, request, g, redirect, url_for, make_response

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

    # Pre-populate some golf courses
    courses_to_add = [
        ('Legacy Links', 72, 70.5, 125),
        ('Steel Canyon', 71, 69.8, 120),
        ('Fox Creek', 70, 68.2, 115),
    ]
    for course in courses_to_add:
        try:
            db.execute('INSERT INTO courses (name, par, course_rating, slope) VALUES (?, ?, ?, ?)', course)
        except sqlite3.IntegrityError:
            # Handle case where course already exists (e.g., if re-initializing after manual adds)
            pass # Or log a warning
    db.commit()

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
        cursor = db.execute(
            'INSERT INTO sessions (session_type, subjective_feel)'
            ' VALUES (?, ?)',
            (session_type, subjective_feel)
        )
        db.commit()
        new_session_id = cursor.lastrowid
        return redirect(url_for('add_drill', session_id=new_session_id))
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

@app.route('/journal')
def journal_list():
    db = get_db()
    entries = db.execute(
        'SELECT je.id, je.entry_date, c.name AS course_name, je.mental_state, je.physical_state, je.weather '
        'FROM journal_entries je LEFT JOIN courses c ON je.course_id = c.id '
        'ORDER BY je.entry_date DESC'
    ).fetchall()
    return render_template('journal_list.html', entries=entries)

@app.route('/add_journal_entry', methods=('GET', 'POST'))
def add_journal_entry():
    db = get_db()
    courses = db.execute('SELECT id, name FROM courses ORDER BY name').fetchall()

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        notes_before_round = request.form['notes_before_round']
        notes_after_round = request.form['notes_after_round']
        mental_state = request.form['mental_state']
        physical_state = request.form['physical_state']
        weather = request.form['weather']
        
        cursor = db.execute(
            'INSERT INTO journal_entries (course_id, notes_before_round, notes_after_round, mental_state, physical_state, weather)'
            ' VALUES (?, ?, ?, ?, ?, ?)',
            (course_id if course_id else None, notes_before_round, notes_after_round, mental_state, physical_state, weather)
        )
        db.commit()
        new_journal_entry_id = cursor.lastrowid

        if course_id and course_id != '':
            return redirect(url_for('add_scorecard', journal_entry_id=new_journal_entry_id))
        else:
            return redirect(url_for('journal_list'))

    return render_template('add_journal_entry.html', courses=courses)

@app.route('/journal/<int:entry_id>')
def journal_details(entry_id):
    db = get_db()
    entry = db.execute(
        'SELECT je.id, je.entry_date, c.name AS course_name, je.notes_before_round, je.notes_after_round, je.mental_state, je.physical_state, je.weather, je.course_id '
        'FROM journal_entries je LEFT JOIN courses c ON je.course_id = c.id '
        'WHERE je.id = ?',
        (entry_id,)
    ).fetchone()

    if entry is None:
        return "Journal entry not found", 404
    
    scorecard = []
    total_score = 0
    total_par = 0
    score_difference = None

    if entry['course_id']:
        holes_data = db.execute(
            'SELECT h.hole_number, h.par, s.score FROM holes h '
            'LEFT JOIN scores s ON h.id = s.hole_id AND s.journal_entry_id = ? '
            'WHERE h.course_id = ? ORDER BY h.hole_number',
            (entry_id, entry['course_id'],)
        ).fetchall()
        
        for hole in holes_data:
            scorecard.append({
                'hole_number': hole['hole_number'],
                'par': hole['par'],
                'score': hole['score'] if hole['score'] is not None else '-'
            })
            if hole['score'] is not None:
                total_score += hole['score']
            total_par += hole['par']
        
        if total_score > 0: # Only calculate if scores were entered
            score_difference = total_score - total_par

    return render_template('journal_details.html', entry=entry, scorecard=scorecard, total_score=total_score, total_par=total_par, score_difference=score_difference)

@app.route('/courses')
def course_list():
    db = get_db()
    courses = db.execute(
        'SELECT id, name, par, course_rating, slope FROM courses ORDER BY name'
    ).fetchall()
    return render_template('course_list.html', courses=courses)

@app.route('/add_course', methods=('GET', 'POST'))
def add_course():
    if request.method == 'POST':
        name = request.form['name']
        par = request.form['par']
        course_rating = request.form['course_rating']
        slope = request.form['slope']

        db = get_db()
        db.execute(
            'INSERT INTO courses (name, par, course_rating, slope)'
            ' VALUES (?, ?, ?, ?)',
            (name, par, course_rating, slope)
        )
        db.commit()
        return redirect(url_for('course_list'))
    return render_template('add_course.html')

@app.route('/add_holes_to_course/<int:course_id>', methods=('GET', 'POST'))
def add_holes_to_course(course_id):
    db = get_db()
    course = db.execute('SELECT id, name, par FROM courses WHERE id = ?', (course_id,)).fetchone()

    if course is None:
        return "Course not found", 404

    if request.method == 'POST':
        # Delete existing holes for this course first to allow re-defining
        db.execute('DELETE FROM holes WHERE course_id = ?', (course_id,))

        for i in range(1, 19): # Assuming 18 holes
            par_key = f'hole_{i}_par'
            par_value = request.form.get(par_key)
            if par_value:
                db.execute(
                    'INSERT INTO holes (course_id, hole_number, par) VALUES (?, ?, ?)',
                    (course_id, i, int(par_value))
                )
        db.commit()
        return redirect(url_for('course_list')) # Redirect back to course list

    # GET request: Prepare an empty form for 18 holes or show existing pars
    existing_holes = db.execute('SELECT hole_number, par FROM holes WHERE course_id = ? ORDER BY hole_number', (course_id,)).fetchall()
    holes_data = {hole['hole_number']: hole['par'] for hole in existing_holes}

    # Create a list of 18 holes with default par 4, or existing par
    holes_for_template = []
    for i in range(1, 19):
        holes_for_template.append({'hole_number': i, 'par': holes_data.get(i, 4)})

    return render_template('add_holes_to_course.html', course=course, holes=holes_for_template)

@app.route('/add_scorecard/<int:journal_entry_id>', methods=('GET', 'POST'))
def add_scorecard(journal_entry_id):
    db = get_db()
    journal_entry = db.execute(
        'SELECT je.id, je.course_id, c.name AS course_name '
        'FROM journal_entries je JOIN courses c ON je.course_id = c.id '
        'WHERE je.id = ?',
        (journal_entry_id,)
    ).fetchone()

    if journal_entry is None or journal_entry['course_id'] is None:
        return "Journal entry not found or no course selected for this entry.", 404

    course_id = journal_entry['course_id']
    course_name = journal_entry['course_name']

    if request.method == 'POST':
        # Delete existing scores for this journal entry first to allow re-entry
        db.execute('DELETE FROM scores WHERE journal_entry_id = ?', (journal_entry_id,))

        for i in range(1, 19): # Assuming 18 holes for now
            hole_score_key = f'hole_{i}_score'
            hole_score = request.form.get(hole_score_key)
            if hole_score:
                hole_id_result = db.execute(
                    'SELECT id FROM holes WHERE course_id = ? AND hole_number = ?',
                    (course_id, i)
                ).fetchone()
                if hole_id_result:
                    hole_id = hole_id_result['id']
                    db.execute(
                        'INSERT INTO scores (journal_entry_id, hole_id, score) VALUES (?, ?, ?)',
                        (journal_entry_id, hole_id, int(hole_score))
                    )
        db.commit()
        return redirect(url_for('journal_details', entry_id=journal_entry_id))

    # GET request: Prepare data for the scorecard form
    holes = db.execute(
        'SELECT id, hole_number, par FROM holes WHERE course_id = ? ORDER BY hole_number',
        (course_id,)
    ).fetchall()
    
    # Fetch existing scores for this journal entry, if any
    existing_scores = db.execute(
        'SELECT h.hole_number, s.score FROM scores s JOIN holes h ON s.hole_id = h.id WHERE s.journal_entry_id = ? ORDER BY h.hole_number',
        (journal_entry_id,)
    ).fetchall()
    scores_data = {score['hole_number']: score['score'] for score in existing_scores}

    if not holes:
        # If no holes are defined for the course, prompt to define them first
        return redirect(url_for('add_holes_to_course', course_id=course_id))

    return render_template('add_scorecard.html', journal_entry=journal_entry, course_name=course_name, holes=holes, scores_data=scores_data)

@app.route('/export/sessions_csv')
def export_sessions_csv():
    db = get_db()
    sessions = db.execute('SELECT id, session_type, session_date, subjective_feel FROM sessions').fetchall()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Session Type', 'Session Date', 'Subjective Feel'])
    cw.writerows(sessions)
    
    response = make_response(si.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=golf_sessions.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

@app.route('/export/drills_csv/<int:session_id>')
def export_drills_csv(session_id):
    db = get_db()
    drills = db.execute(
        'SELECT id, drill_name, club, target_distance, balls_hit, success_metric FROM drills WHERE session_id = ?',
        (session_id,)
    ).fetchall()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Drill Name', 'Club', 'Target Distance', 'Balls Hit', 'Success Metric'])
    cw.writerows(drills)
    
    response = make_response(si.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=session_{session_id}_drills.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

@app.route('/export/journal_csv')
def export_journal_csv():
    db = get_db()
    entries = db.execute(
        'SELECT id, entry_date, round_stats, notes_before_round, notes_after_round, mental_state, physical_state, weather FROM journal_entries'
    ).fetchall()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Entry Date', 'Round Stats', 'Notes Before Round', 'Notes After Round', 'Mental State', 'Physical State', 'Weather'])
    cw.writerows(entries)
    
    response = make_response(si.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=golf_journal.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

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
