import sqlite3
import csv
import io
import os
import calendar
import statistics
import importlib.util
from pathlib import Path
from flask import Flask, render_template, request, g, redirect, url_for, make_response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'instance/golf_tracker.db'

app = Flask(__name__)
debug_enabled = os.environ.get('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes'}
secret_key = os.environ.get('SECRET_KEY')
if not secret_key and not debug_enabled:
    raise RuntimeError('SECRET_KEY not set')
app.config.from_mapping(
    SECRET_KEY=secret_key or 'dev',
    DATABASE=DATABASE,
)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, default_limits=['200 per day', '50 per hour'])

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

class User(UserMixin):
    def __init__(self, user_id, username, password_hash, is_admin):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash
        self.is_admin = bool(is_admin)

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    row = db.execute('SELECT id, username, password_hash, is_admin FROM users WHERE id = ?', (user_id,)).fetchone()
    if row is None:
        return None
    return User(row['id'], row['username'], row['password_hash'], row['is_admin'])

def get_user_by_username(username):
    db = get_db()
    row = db.execute('SELECT id, username, password_hash, is_admin FROM users WHERE username = ?', (username,)).fetchone()
    if row is None:
        return None
    return User(row['id'], row['username'], row['password_hash'], row['is_admin'])

def require_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        return "Admin access required", 403
    return None

def parse_int(value, field_name, min_value=None, max_value=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field_name} must be a valid number.')
    if min_value is not None and parsed < min_value:
        raise ValueError(f'{field_name} must be at least {min_value}.')
    if max_value is not None and parsed > max_value:
        raise ValueError(f'{field_name} must be at most {max_value}.')
    return parsed

def parse_float(value, field_name, min_value=None, max_value=None):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field_name} must be a valid number.')
    if min_value is not None and parsed < min_value:
        raise ValueError(f'{field_name} must be at least {min_value}.')
    if max_value is not None and parsed > max_value:
        raise ValueError(f'{field_name} must be at most {max_value}.')
    return parsed

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

app.teardown_appcontext(close_db)

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

    admin_username = os.environ.get('ADMIN_USERNAME')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    if admin_username and admin_password:
        existing = db.execute('SELECT id FROM users WHERE username = ?', (admin_username,)).fetchone()
        if existing is None:
            db.execute(
                'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)',
                (admin_username, generate_password_hash(admin_password))
            )
            db.commit()

@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    print('Initialized the database.')

@app.cli.command('migrate-db')
def migrate_db_command():
    """Apply versioned migrations from the migrations folder."""
    db = get_db()
    db.execute(
        'CREATE TABLE IF NOT EXISTS schema_migrations ('
        'id TEXT PRIMARY KEY, '
        'applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP'
        ')'
    )
    db.commit()

    migrations_dir = Path(__file__).parent / 'migrations'
    if not migrations_dir.exists():
        print('No migrations directory found.')
        return

    applied = {row['id'] for row in db.execute('SELECT id FROM schema_migrations').fetchall()}
    for path in sorted(migrations_dir.glob('*.py')):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        migration_id = getattr(module, 'MIGRATION_ID', path.stem)
        if migration_id in applied:
            continue
        try:
            db.execute('BEGIN')
            module.upgrade(db)
            db.execute('INSERT INTO schema_migrations (id) VALUES (?)', (migration_id,))
            db.commit()
            print(f'Applied migration {migration_id}')
        except Exception:
            db.rollback()
            raise

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/app')
@login_required
def dashboard():
    db = get_db()
    sessions = db.execute(
        'SELECT id, session_type, session_date, subjective_feel'
        ' FROM sessions'
        ' WHERE user_id = ?'
        ' ORDER BY session_date DESC',
        (current_user.id,)
    ).fetchall()
    
    # Calculate stats for dashboard
    from datetime import datetime, timedelta
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    sessions_this_week = db.execute(
        'SELECT COUNT(*) AS count FROM sessions WHERE user_id = ? AND session_date >= ?',
        (current_user.id, week_ago)
    ).fetchone()['count']
    
    avg_feel_month = db.execute(
        'SELECT AVG(subjective_feel) AS avg FROM sessions WHERE user_id = ? AND session_date >= ?',
        (current_user.id, month_ago)
    ).fetchone()['avg']
    
    most_used_club = db.execute(
        '''SELECT club, COUNT(*) AS count FROM drills d
           JOIN sessions s ON d.session_id = s.id
           WHERE s.user_id = ? AND d.club IS NOT NULL AND d.club != ''
           GROUP BY club ORDER BY count DESC LIMIT 1''',
        (current_user.id,)
    ).fetchone()
    
    last_session = db.execute(
        'SELECT session_date FROM sessions WHERE user_id = ? ORDER BY session_date DESC LIMIT 1',
        (current_user.id,)
    ).fetchone()
    
    stats = {
        'sessions_this_week': sessions_this_week,
        'avg_feel_month': avg_feel_month,
        'most_used_club': most_used_club['club'] if most_used_club else None,
        'last_session_date': last_session['session_date'] if last_session else None
    }
    
    return render_template('index.html', sessions=sessions, stats=stats)

@app.route('/login', methods=('GET', 'POST'))
@limiter.limit('10 per minute')
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = get_user_by_username(username)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_url = request.args.get('next')
            return redirect(next_url or url_for('dashboard'))
        return render_template('login.html', error='Invalid username or password.')
    return render_template('login.html', error=None)

@app.route('/register', methods=('GET', 'POST'))
@limiter.limit('5 per minute')
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not password:
            return render_template('register.html', error='Username and password are required.')
        if len(password) < 8:
            return render_template('register.html', error='Password must be at least 8 characters.')
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match.')
        if get_user_by_username(username):
            return render_template('register.html', error='Username already exists.')

        db = get_db()
        db.execute(
            'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 0)',
            (username, generate_password_hash(password))
        )
        db.commit()

        user = get_user_by_username(username)
        if user:
            login_user(user)
            return redirect(url_for('dashboard'))

        return redirect(url_for('login'))

    return render_template('register.html', error=None)

@app.post('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_session', methods=('GET', 'POST'))
@login_required
def add_session():
    if request.method == 'POST':
        session_type = request.form['session_type']
        try:
            subjective_feel = parse_int(request.form['subjective_feel'], 'Subjective feel', 1, 5)
        except ValueError as exc:
            return render_template('add_session.html', error=str(exc))

        db = get_db()
        cursor = db.execute(
            'INSERT INTO sessions (session_type, subjective_feel, user_id)'
            ' VALUES (?, ?, ?)',
            (session_type, subjective_feel, current_user.id)
        )
        db.commit()
        new_session_id = cursor.lastrowid
        return redirect(url_for('add_drill', session_id=new_session_id))
    return render_template('add_session.html', error=None)

@app.route('/session/<int:session_id>/add_drill', methods=('GET', 'POST'))
@login_required
def add_drill(session_id):
    db = get_db()
    session = db.execute(
        'SELECT id FROM sessions WHERE id = ? AND user_id = ?',
        (session_id, current_user.id)
    ).fetchone()
    if session is None:
        return "Session not found", 404

    if request.method == 'POST':
        drill_name = request.form['drill_name']
        club = request.form['club']
        target_distance = request.form.get('target_distance') or None
        balls_hit = request.form.get('balls_hit') or None
        success_metric = request.form['success_metric']
        action = request.form.get('action', 'finish')  # 'add_another' or 'finish'

        try:
            if target_distance is not None:
                target_distance = parse_int(target_distance, 'Target distance', 0)
            if balls_hit is not None:
                balls_hit = parse_int(balls_hit, 'Balls hit', 1)
        except ValueError as exc:
            return render_template('add_drill.html', session_id=session_id, error=str(exc))

        db.execute(
            'INSERT INTO drills (session_id, drill_name, club, target_distance, balls_hit, success_metric)'
            ' VALUES (?, ?, ?, ?, ?, ?)',
            (session_id, drill_name, club, target_distance, balls_hit, success_metric)
        )
        db.commit()
        
        if action == 'add_another':
            return redirect(url_for('add_drill', session_id=session_id))
        else:
            return redirect(url_for('session_details', session_id=session_id))
    return render_template('add_drill.html', session_id=session_id, error=None)

@app.route('/journal')
@login_required
def journal_list():
    db = get_db()
    entries = db.execute(
        'SELECT je.id, je.entry_date, c.name AS course_name, je.mental_state, je.physical_state, je.weather '
        'FROM journal_entries je LEFT JOIN courses c ON je.course_id = c.id '
        'WHERE je.user_id = ? '
        'ORDER BY je.entry_date DESC',
        (current_user.id,)
    ).fetchall()
    return render_template('journal_list.html', entries=entries)

@app.route('/add_journal_entry', methods=('GET', 'POST'))
@login_required
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
            'INSERT INTO journal_entries (course_id, notes_before_round, notes_after_round, mental_state, physical_state, weather, user_id)'
            ' VALUES (?, ?, ?, ?, ?, ?, ?)',
            (course_id if course_id else None, notes_before_round, notes_after_round, mental_state, physical_state, weather, current_user.id)
        )
        db.commit()
        new_journal_entry_id = cursor.lastrowid

        if course_id and course_id != '':
            return redirect(url_for('add_scorecard', journal_entry_id=new_journal_entry_id))
        else:
            return redirect(url_for('journal_list'))

    return render_template('add_journal_entry.html', courses=courses)

@app.route('/journal/<int:entry_id>')
@login_required
def journal_details(entry_id):
    db = get_db()
    entry = db.execute(
        'SELECT je.id, je.entry_date, c.name AS course_name, je.notes_before_round, je.notes_after_round, je.mental_state, je.physical_state, je.weather, je.course_id '
        'FROM journal_entries je LEFT JOIN courses c ON je.course_id = c.id '
        'WHERE je.id = ? AND je.user_id = ?',
        (entry_id, current_user.id)
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
@login_required
def course_list():
    db = get_db()
    courses = db.execute(
        'SELECT id, name, par, course_rating, slope, website_url FROM courses ORDER BY name'
    ).fetchall()
    return render_template('course_list.html', courses=courses)

@app.route('/courses/<int:course_id>')
@login_required
def course_details(course_id):
    db = get_db()
    selected_year = request.args.get('year')
    selected_month = request.args.get('month')
    selected_view = request.args.get('view', 'all')
    selected_limit = request.args.get('limit', '10')

    limit_value = None
    if selected_limit and selected_limit.lower() not in {'all', '0'}:
        try:
            limit_value = max(1, int(selected_limit))
        except ValueError:
            limit_value = 10

    course = db.execute(
        'SELECT id, name, par, course_rating, slope, website_url FROM courses WHERE id = ?',
        (course_id,)
    ).fetchone()

    if course is None:
        return "Course not found", 404

    holes = db.execute(
        'SELECT id, hole_number, par FROM holes WHERE course_id = ? ORDER BY hole_number',
        (course_id,)
    ).fetchall()

    years_rows = db.execute(
        "SELECT DISTINCT strftime('%Y', entry_date) AS year FROM journal_entries WHERE course_id = ? AND user_id = ? ORDER BY year DESC",
        (course_id, current_user.id)
    ).fetchall()
    available_years = [row['year'] for row in years_rows if row['year']]

    if selected_year:
        months_rows = db.execute(
            "SELECT DISTINCT strftime('%m', entry_date) AS month FROM journal_entries WHERE course_id = ? AND user_id = ? AND strftime('%Y', entry_date) = ? ORDER BY month DESC",
            (course_id, current_user.id, selected_year)
        ).fetchall()
    else:
        months_rows = db.execute(
            "SELECT DISTINCT strftime('%m', entry_date) AS month FROM journal_entries WHERE course_id = ? AND user_id = ? ORDER BY month DESC",
            (course_id, current_user.id)
        ).fetchall()
    available_months = [
        {'value': row['month'], 'label': calendar.month_name[int(row['month'])]}
        for row in months_rows if row['month']
    ]

    entries_query = 'SELECT id, entry_date FROM journal_entries WHERE course_id = ? AND user_id = ?'
    query_params = [course_id, current_user.id]

    if selected_year:
        entries_query += " AND strftime('%Y', entry_date) = ?"
        query_params.append(selected_year)
    if selected_month:
        selected_month = selected_month.zfill(2)
        entries_query += " AND strftime('%m', entry_date) = ?"
        query_params.append(selected_month)

    entries_query += ' ORDER BY entry_date DESC'
    if limit_value is not None:
        entries_query += ' LIMIT ?'
        query_params.append(limit_value)

    entries = db.execute(entries_query, tuple(query_params)).fetchall()

    scores_rows = db.execute(
        'SELECT s.journal_entry_id, h.hole_number, s.score '
        'FROM scores s '
        'JOIN holes h ON s.hole_id = h.id '
        'JOIN journal_entries je ON s.journal_entry_id = je.id '
        'WHERE h.course_id = ? AND je.user_id = ? '
        'ORDER BY s.journal_entry_id, h.hole_number',
        (course_id, current_user.id)
    ).fetchall()

    scores_by_entry = {}
    for row in scores_rows:
        scores_by_entry.setdefault(row['journal_entry_id'], {})[row['hole_number']] = row['score']

    par_out = sum(hole['par'] for hole in holes if hole['hole_number'] <= 9)
    par_in = sum(hole['par'] for hole in holes if hole['hole_number'] > 9)
    par_total = par_out + par_in

    entry_rows = []
    for entry in entries:
        entry_scores = scores_by_entry.get(entry['id'], {})
        score_values = [score for score in entry_scores.values() if score is not None]

        if score_values:
            out_total = sum(score for hole, score in entry_scores.items() if score is not None and hole <= 9)
            in_total = sum(score for hole, score in entry_scores.items() if score is not None and hole > 9)
            total = out_total + in_total
        else:
            out_total = None
            in_total = None
            total = None

        entry_label = entry['entry_date'].strftime('%b %d, %Y') if hasattr(entry['entry_date'], 'strftime') else str(entry['entry_date'])
        entry_rows.append({
            'id': entry['id'],
            'label': entry_label,
            'scores': entry_scores,
            'out_total': out_total,
            'in_total': in_total,
            'total': total,
            'to_par': (total - par_total) if total is not None else None,
        })

    totals_with_scores = [entry['total'] for entry in entry_rows if entry['total'] is not None]
    best_total = min(totals_with_scores) if totals_with_scores else None

    to_par_values = [entry['to_par'] for entry in entry_rows if entry['to_par'] is not None]
    best_to_par = min(to_par_values) if to_par_values else None

    for entry in entry_rows:
        entry['is_best'] = best_total is not None and entry['total'] == best_total
        entry['is_best_to_par'] = best_to_par is not None and entry['to_par'] == best_to_par

    if selected_view == 'best':
        entry_rows = [entry for entry in entry_rows if entry.get('is_best')]
    elif selected_view == 'best_to_par':
        entry_rows = [entry for entry in entry_rows if entry.get('is_best_to_par')]
    elif selected_view == 'average':
        averages = {}
        medians = {}
        for hole in holes:
            values = [row['scores'].get(hole['hole_number']) for row in entry_rows if row['scores'].get(hole['hole_number']) is not None]
            if values:
                averages[hole['hole_number']] = sum(values) / len(values)
                medians[hole['hole_number']] = statistics.median(values)

        if averages or medians:
            entry_rows = []

            if averages:
                average_out = sum(value for hole, value in averages.items() if hole <= 9)
                average_in = sum(value for hole, value in averages.items() if hole > 9)
                average_total = average_out + average_in
                entry_rows.append({
                    'id': None,
                    'label': 'Average',
                    'scores': averages,
                    'out_total': average_out,
                    'in_total': average_in,
                    'total': average_total,
                    'to_par': average_total - par_total,
                    'is_best': False,
                    'is_best_to_par': False,
                })

            if medians:
                median_out = sum(value for hole, value in medians.items() if hole <= 9)
                median_in = sum(value for hole, value in medians.items() if hole > 9)
                median_total = median_out + median_in
                entry_rows.append({
                    'id': None,
                    'label': 'Median',
                    'scores': medians,
                    'out_total': median_out,
                    'in_total': median_in,
                    'total': median_total,
                    'to_par': median_total - par_total,
                    'is_best': False,
                    'is_best_to_par': False,
                })
        else:
            entry_rows = []

    return render_template(
        'course_details.html',
        course=course,
        holes=holes,
        entry_rows=entry_rows,
        par_out=par_out,
        par_in=par_in,
        par_total=par_total,
        available_years=available_years,
        available_months=available_months,
        selected_year=selected_year,
        selected_month=selected_month,
        selected_view=selected_view,
        selected_limit=selected_limit,
    )

@app.route('/courses/<int:course_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_course(course_id):
    admin_guard = require_admin()
    if admin_guard:
        return admin_guard
    db = get_db()
    course = db.execute(
        'SELECT id, name, par, course_rating, slope, website_url FROM courses WHERE id = ?',
        (course_id,)
    ).fetchone()

    if course is None:
        return "Course not found", 404

    if request.method == 'POST':
        name = request.form['name']
        try:
            par = parse_int(request.form['par'], 'Par', 1)
            course_rating = parse_float(request.form['course_rating'], 'Course rating', 0)
            slope = parse_int(request.form['slope'], 'Slope', 55, 155)
        except ValueError as exc:
            return render_template('edit_course.html', course=course, error=str(exc))
        website_url = request.form.get('website_url') or None

        db.execute(
            'UPDATE courses SET name = ?, par = ?, course_rating = ?, slope = ?, website_url = ? WHERE id = ?',
            (name, par, course_rating, slope, website_url, course_id)
        )
        db.commit()
        return redirect(url_for('course_list'))

    return render_template('edit_course.html', course=course, error=None)

@app.route('/add_course', methods=('GET', 'POST'))
@login_required
def add_course():
    admin_guard = require_admin()
    if admin_guard:
        return admin_guard
    if request.method == 'POST':
        name = request.form['name']
        try:
            par = parse_int(request.form['par'], 'Par', 1)
            course_rating = parse_float(request.form['course_rating'], 'Course rating', 0)
            slope = parse_int(request.form['slope'], 'Slope', 55, 155)
        except ValueError as exc:
            return render_template('add_course.html', error=str(exc))
        website_url = request.form.get('website_url') or None

        db = get_db()
        db.execute(
            'INSERT INTO courses (name, par, course_rating, slope, website_url)'
            ' VALUES (?, ?, ?, ?, ?)',
            (name, par, course_rating, slope, website_url)
        )
        db.commit()
        return redirect(url_for('course_list'))
    return render_template('add_course.html', error=None)

@app.route('/add_holes_to_course/<int:course_id>', methods=('GET', 'POST'))
@login_required
def add_holes_to_course(course_id):
    admin_guard = require_admin()
    if admin_guard:
        return admin_guard
    db = get_db()
    course = db.execute('SELECT id, name, par FROM courses WHERE id = ?', (course_id,)).fetchone()

    if course is None:
        return "Course not found", 404

    if request.method == 'POST':
        holes_to_insert = []
        for i in range(1, 19): # Assuming 18 holes
            par_key = f'hole_{i}_par'
            distance_key = f'hole_{i}_distance'
            par_value = request.form.get(par_key)
            distance_value = request.form.get(distance_key)
            if par_value:
                try:
                    par_int = parse_int(par_value, f'Hole {i} par', 1, 7)
                    distance_int = None
                    if distance_value:
                        distance_int = parse_int(distance_value, f'Hole {i} distance', 0)
                except ValueError as exc:
                    existing_holes = db.execute(
                        'SELECT hole_number, par, distance FROM holes WHERE course_id = ? ORDER BY hole_number',
                        (course_id,)
                    ).fetchall()
                    holes_data = {hole['hole_number']: {'par': hole['par'], 'distance': hole['distance']} for hole in existing_holes}
                    holes_for_template = [{'hole_number': n, 'par': holes_data.get(n, {}).get('par', 4), 'distance': holes_data.get(n, {}).get('distance')} for n in range(1, 19)]
                    return render_template('add_holes_to_course.html', course=course, holes=holes_for_template, error=str(exc))

                holes_to_insert.append((course_id, i, par_int, distance_int))

        # Delete existing holes for this course first to allow re-defining
        db.execute('DELETE FROM holes WHERE course_id = ?', (course_id,))
        if holes_to_insert:
            db.executemany(
                'INSERT INTO holes (course_id, hole_number, par, distance) VALUES (?, ?, ?, ?)',
                holes_to_insert
            )
        db.commit()
        return redirect(url_for('course_list')) # Redirect back to course list

    # GET request: Prepare an empty form for 18 holes or show existing pars
    existing_holes = db.execute('SELECT hole_number, par, distance FROM holes WHERE course_id = ? ORDER BY hole_number', (course_id,)).fetchall()
    holes_data = {hole['hole_number']: {'par': hole['par'], 'distance': hole['distance']} for hole in existing_holes}

    # Create a list of 18 holes with default par 4, or existing par
    holes_for_template = []
    for i in range(1, 19):
        holes_for_template.append({
            'hole_number': i,
            'par': holes_data.get(i, {}).get('par', 4),
            'distance': holes_data.get(i, {}).get('distance')
        })

    return render_template('add_holes_to_course.html', course=course, holes=holes_for_template, error=None)

@app.route('/add_scorecard/<int:journal_entry_id>', methods=('GET', 'POST'))
@login_required
def add_scorecard(journal_entry_id):
    db = get_db()
    journal_entry = db.execute(
        'SELECT je.id, je.course_id, je.entry_date, c.name AS course_name '
        'FROM journal_entries je JOIN courses c ON je.course_id = c.id '
        'WHERE je.id = ? AND je.user_id = ?',
        (journal_entry_id, current_user.id)
    ).fetchone()

    if journal_entry is None or journal_entry['course_id'] is None:
        return "Journal entry not found or no course selected for this entry.", 404

    course_id = journal_entry['course_id']
    course_name = journal_entry['course_name']

    holes = db.execute(
        'SELECT id, hole_number, par, distance FROM holes WHERE course_id = ? ORDER BY hole_number',
        (course_id,)
    ).fetchall()

    if not holes:
        # If no holes are defined for the course, prompt to define them first
        return redirect(url_for('add_holes_to_course', course_id=course_id))

    existing_scores = db.execute(
        'SELECT h.hole_number, s.score FROM scores s JOIN holes h ON s.hole_id = h.id WHERE s.journal_entry_id = ? ORDER BY h.hole_number',
        (journal_entry_id,)
    ).fetchall()
    scores_data = {score['hole_number']: score['score'] for score in existing_scores}

    if request.method == 'POST':
        scores_to_insert = []
        for i in range(1, 19): # Assuming 18 holes for now
            hole_score_key = f'hole_{i}_score'
            hole_score = request.form.get(hole_score_key)
            if hole_score:
                try:
                    hole_score_int = parse_int(hole_score, f'Hole {i} score', 1)
                except ValueError as exc:
                    par_out = sum(hole['par'] for hole in holes if hole['hole_number'] <= 9)
                    par_in = sum(hole['par'] for hole in holes if hole['hole_number'] > 9)
                    par_total = par_out + par_in
                    return render_template(
                        'add_scorecard.html',
                        journal_entry=journal_entry,
                        course_name=course_name,
                        course_id=course_id,
                        holes=holes,
                        scores_data=scores_data,
                        par_out=par_out,
                        par_in=par_in,
                        par_total=par_total,
                        previous_entry_label=None,
                        last_scores={},
                        last_out=None,
                        last_in=None,
                        last_total=None,
                        error=str(exc),
                    )
                hole_id_result = db.execute(
                    'SELECT id FROM holes WHERE course_id = ? AND hole_number = ?',
                    (course_id, i)
                ).fetchone()
                if hole_id_result:
                    scores_to_insert.append((journal_entry_id, hole_id_result['id'], hole_score_int))

        # Delete existing scores for this journal entry first to allow re-entry
        db.execute('DELETE FROM scores WHERE journal_entry_id = ?', (journal_entry_id,))
        if scores_to_insert:
            db.executemany(
                'INSERT INTO scores (journal_entry_id, hole_id, score) VALUES (?, ?, ?)',
                scores_to_insert
            )
        db.commit()
        return redirect(url_for('journal_details', entry_id=journal_entry_id))

    par_out = sum(hole['par'] for hole in holes if hole['hole_number'] <= 9)
    par_in = sum(hole['par'] for hole in holes if hole['hole_number'] > 9)
    par_total = par_out + par_in

    previous_entry = db.execute(
        'SELECT id, entry_date FROM journal_entries WHERE course_id = ? AND user_id = ? AND id != ? ORDER BY entry_date DESC LIMIT 1',
        (course_id, current_user.id, journal_entry_id)
    ).fetchone()

    last_scores = {}
    last_out = None
    last_in = None
    last_total = None
    previous_entry_label = None

    if previous_entry is not None:
        previous_entry_label = previous_entry['entry_date'].strftime('%b %d, %Y') if hasattr(previous_entry['entry_date'], 'strftime') else str(previous_entry['entry_date'])
        last_scores_rows = db.execute(
            'SELECT h.hole_number, s.score FROM scores s JOIN holes h ON s.hole_id = h.id WHERE s.journal_entry_id = ? ORDER BY h.hole_number',
            (previous_entry['id'],)
        ).fetchall()
        last_scores = {score['hole_number']: score['score'] for score in last_scores_rows}

        last_score_values = [score for score in last_scores.values() if score is not None]
        if last_score_values:
            last_out = sum(score for hole, score in last_scores.items() if score is not None and hole <= 9)
            last_in = sum(score for hole, score in last_scores.items() if score is not None and hole > 9)
            last_total = last_out + last_in

    return render_template(
        'add_scorecard.html',
        journal_entry=journal_entry,
        course_name=course_name,
        course_id=course_id,
        holes=holes,
        scores_data=scores_data,
        par_out=par_out,
        par_in=par_in,
        par_total=par_total,
        previous_entry_label=previous_entry_label,
        last_scores=last_scores,
        last_out=last_out,
        last_in=last_in,
        last_total=last_total,
        error=None,
    )

@app.route('/export/sessions_csv')
@login_required
def export_sessions_csv():
    db = get_db()
    sessions = db.execute(
        'SELECT id, session_type, session_date, subjective_feel FROM sessions WHERE user_id = ?',
        (current_user.id,)
    ).fetchall()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Session Type', 'Session Date', 'Subjective Feel'])
    cw.writerows(sessions)
    
    response = make_response(si.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=golf_sessions.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

@app.route('/export/drills_csv/<int:session_id>')
@login_required
def export_drills_csv(session_id):
    db = get_db()
    session = db.execute(
        'SELECT id FROM sessions WHERE id = ? AND user_id = ?',
        (session_id, current_user.id)
    ).fetchone()
    if session is None:
        return "Session not found", 404
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
@login_required
def export_journal_csv():
    db = get_db()
    entries = db.execute(
        'SELECT id, entry_date, notes_before_round, notes_after_round, mental_state, physical_state, weather '
        'FROM journal_entries WHERE user_id = ?',
        (current_user.id,)
    ).fetchall()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Entry Date', 'Notes Before Round', 'Notes After Round', 'Mental State', 'Physical State', 'Weather'])
    cw.writerows(entries)
    
    response = make_response(si.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=golf_journal.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

@app.route('/session/<int:session_id>')
@login_required
def session_details(session_id):
    db = get_db()
    session = db.execute(
        'SELECT id, session_type, session_date, subjective_feel'
        ' FROM sessions'
        ' WHERE id = ? AND user_id = ?',
        (session_id, current_user.id)
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

@app.route('/session/<int:session_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_session(session_id):
    db = get_db()
    session = db.execute(
        'SELECT id, session_type, session_date, subjective_feel FROM sessions WHERE id = ? AND user_id = ?',
        (session_id, current_user.id)
    ).fetchone()
    
    if session is None:
        return "Session not found", 404
    
    if request.method == 'POST':
        session_type = request.form['session_type']
        try:
            subjective_feel = parse_int(request.form['subjective_feel'], 'Subjective feel', 1, 5)
        except ValueError as exc:
            return render_template('edit_session.html', session=session, error=str(exc))
        
        db.execute(
            'UPDATE sessions SET session_type = ?, subjective_feel = ? WHERE id = ? AND user_id = ?',
            (session_type, subjective_feel, session_id, current_user.id)
        )
        db.commit()
        return redirect(url_for('session_details', session_id=session_id))
    
    return render_template('edit_session.html', session=session, error=None)

@app.post('/session/<int:session_id>/delete')
@login_required
def delete_session(session_id):
    db = get_db()
    session = db.execute(
        'SELECT id FROM sessions WHERE id = ? AND user_id = ?',
        (session_id, current_user.id)
    ).fetchone()
    
    if session is None:
        return "Session not found", 404
    
    # Delete drills first (cascade should handle this, but being explicit)
    db.execute('DELETE FROM drills WHERE session_id = ?', (session_id,))
    db.execute('DELETE FROM sessions WHERE id = ? AND user_id = ?', (session_id, current_user.id))
    db.commit()
    return redirect(url_for('dashboard'))

@app.route('/drill/<int:drill_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_drill(drill_id):
    db = get_db()
    drill = db.execute(
        '''SELECT d.id, d.session_id, d.drill_name, d.club, d.target_distance, d.balls_hit, d.success_metric
           FROM drills d
           JOIN sessions s ON d.session_id = s.id
           WHERE d.id = ? AND s.user_id = ?''',
        (drill_id, current_user.id)
    ).fetchone()
    
    if drill is None:
        return "Drill not found", 404
    
    if request.method == 'POST':
        drill_name = request.form['drill_name']
        club = request.form['club']
        target_distance = request.form.get('target_distance') or None
        balls_hit = request.form.get('balls_hit') or None
        success_metric = request.form['success_metric']
        
        try:
            if target_distance is not None:
                target_distance = parse_int(target_distance, 'Target distance', 0)
            if balls_hit is not None:
                balls_hit = parse_int(balls_hit, 'Balls hit', 1)
        except ValueError as exc:
            return render_template('edit_drill.html', drill=drill, error=str(exc))
        
        db.execute(
            'UPDATE drills SET drill_name = ?, club = ?, target_distance = ?, balls_hit = ?, success_metric = ? WHERE id = ?',
            (drill_name, club, target_distance, balls_hit, success_metric, drill_id)
        )
        db.commit()
        return redirect(url_for('session_details', session_id=drill['session_id']))
    
    return render_template('edit_drill.html', drill=drill, error=None)

@app.post('/drill/<int:drill_id>/delete')
@login_required
def delete_drill(drill_id):
    db = get_db()
    drill = db.execute(
        '''SELECT d.id, d.session_id
           FROM drills d
           JOIN sessions s ON d.session_id = s.id
           WHERE d.id = ? AND s.user_id = ?''',
        (drill_id, current_user.id)
    ).fetchone()
    
    if drill is None:
        return "Drill not found", 404
    
    session_id = drill['session_id']
    db.execute('DELETE FROM drills WHERE id = ?', (drill_id,))
    db.commit()
    return redirect(url_for('session_details', session_id=session_id))

@app.route('/journal/<int:entry_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_journal_entry(entry_id):
    db = get_db()
    entry = db.execute(
        'SELECT id, course_id, notes_before_round, notes_after_round, mental_state, physical_state, weather FROM journal_entries WHERE id = ? AND user_id = ?',
        (entry_id, current_user.id)
    ).fetchone()
    
    if entry is None:
        return "Journal entry not found", 404
    
    courses = db.execute('SELECT id, name FROM courses ORDER BY name').fetchall()
    
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        notes_before_round = request.form['notes_before_round']
        notes_after_round = request.form['notes_after_round']
        mental_state = request.form['mental_state']
        physical_state = request.form['physical_state']
        weather = request.form['weather']
        
        db.execute(
            'UPDATE journal_entries SET course_id = ?, notes_before_round = ?, notes_after_round = ?, mental_state = ?, physical_state = ?, weather = ? WHERE id = ? AND user_id = ?',
            (course_id if course_id else None, notes_before_round, notes_after_round, mental_state, physical_state, weather, entry_id, current_user.id)
        )
        db.commit()
        return redirect(url_for('journal_details', entry_id=entry_id))
    
    return render_template('edit_journal_entry.html', entry=entry, courses=courses, error=None)

@app.post('/journal/<int:entry_id>/delete')
@login_required
def delete_journal_entry(entry_id):
    db = get_db()
    entry = db.execute(
        'SELECT id FROM journal_entries WHERE id = ? AND user_id = ?',
        (entry_id, current_user.id)
    ).fetchone()
    
    if entry is None:
        return "Journal entry not found", 404
    
    # Delete scores first
    db.execute('DELETE FROM scores WHERE journal_entry_id = ?', (entry_id,))
    db.execute('DELETE FROM journal_entries WHERE id = ? AND user_id = ?', (entry_id, current_user.id))
    db.commit()
    return redirect(url_for('journal_list'))

if __name__ == '__main__':
    debug_enabled = os.environ.get('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes'}
    app.run(debug=debug_enabled)
