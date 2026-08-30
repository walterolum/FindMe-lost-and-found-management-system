import os
import secrets
import threading
from datetime import datetime, timedelta
from functools import wraps

import bcrypt
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_from_directory, abort
)
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from PIL import Image

from config import Config

app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def get_db():
    return mysql.connection


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _run_matcher_async(item_type, item_id):
    with app.app_context():
        try:
            db = get_db()
            from ai.matcher import find_potential_matches
            find_potential_matches(item_type, item_id, db)
        except Exception:
            pass


def save_image(file, folder=''):
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secrets.token_hex(16) + '.' + ext
    subfolder = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    os.makedirs(subfolder, exist_ok=True)
    filepath = os.path.join(subfolder, filename)

    img = Image.open(file)
    img.thumbnail((1200, 1200))

    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    img.save(filepath, optimize=True, quality=85)

    path = os.path.join(folder, filename) if folder else filename
    return path.replace('\\', '/')


def log_activity(user_id, action, description, entity_type=None, entity_id=None):
    db = get_db()
    cursor = db.cursor()
    ip = request.remote_addr
    cursor.execute(
        'INSERT INTO activity_logs (user_id, action, description, entity_type, entity_id, ip_address) VALUES (%s, %s, %s, %s, %s, %s)',
        (user_id, action, description, entity_type, entity_id, ip)
    )
    db.commit()
    cursor.close()


def paginated_query(cursor, base_query, count_query, params, page, per_page=20):
    offset = (page - 1) * per_page
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    cursor.execute(base_query + ' LIMIT %s OFFSET %s', params + [per_page, offset])
    items = cursor.fetchall()
    total_pages = max(1, (total + per_page - 1) // per_page)
    return items, page, total_pages, total


def get_role_name(role_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT name FROM roles WHERE id = %s', (role_id,))
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else 'Unknown'

def get_reference_name(ref_id, table, name_col='name'):
    if not ref_id:
        return None
    db = get_db()
    cursor = db.cursor()
    cursor.execute(f'SELECT {name_col} FROM {table} WHERE id = %s', (ref_id,))
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def get_faculty_name(faculty_id):
    if not faculty_id:
        return None
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT name FROM faculties WHERE id = %s', (faculty_id,))
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def get_course_name(course_id):
    if not course_id:
        return None
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT name FROM courses WHERE id = %s', (course_id,))
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def get_category_name(cat_id):
    if not cat_id:
        return None
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT name FROM categories WHERE id = %s', (cat_id,))
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def get_location_name(loc_id):
    if not loc_id:
        return None
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT name FROM locations WHERE id = %s', (loc_id,))
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def generate_reference(prefix, item_type):
    VALID_TYPES = {'lost', 'found'}
    if item_type not in VALID_TYPES:
        raise ValueError(f"Invalid item type: {item_type}")
    db = get_db()
    cursor = db.cursor()
    cursor.execute(f"SELECT MAX(id) FROM {item_type}_items")
    max_id = cursor.fetchone()[0]
    cursor.close()
    count = (max_id if max_id else 0) + 1
    year = datetime.now().year
    return f"{prefix}-{year}-{count:05d}"


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('role_id') != 3:
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def role_required(*role_names):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            user_role = session.get('role_name')
            if user_role not in role_names:
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ==================== AUTH ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            'SELECT id, full_name, email, password_hash, role_id, is_active, student_staff_id, phone, faculty_id, course_id, profile_image FROM users WHERE email = %s',
            (email,)
        )
        user = cursor.fetchone()
        cursor.close()
        

        if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            if not user[5]:
                flash('Your account has been deactivated. Contact an administrator.', 'danger')
                return render_template('login.html')

            session['user_id'] = user[0]
            session['full_name'] = user[1]
            session['email'] = user[2]
            session['role_id'] = user[4]
            session['role_name'] = get_role_name(user[4])
            session['student_staff_id'] = user[6]
            session['phone'] = user[7]
            session['faculty_id'] = user[8]
            session['course_id'] = user[9]
            session['profile_image'] = user[10]

            log_activity(user[0], 'login', 'User logged in')
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, name FROM faculties WHERE is_active = TRUE ORDER BY name')
    faculties = cursor.fetchall()
    cursor.execute('SELECT id, name FROM courses WHERE is_active = TRUE ORDER BY name')
    courses = cursor.fetchall()
    cursor.close()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        student_staff_id = request.form.get('student_id', '').strip() or request.form.get('student_staff_id', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role_name = request.form.get('user_type', 'Student')
        faculty_id = request.form.get('faculty_id')
        course_id = request.form.get('course_id')

        if role_name not in ('Student', 'Lecturer'):
            role_name = 'Student'

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html', faculties=faculties, courses=courses)

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html', faculties=faculties, courses=courses)

        cursor2 = db.cursor()
        cursor2.execute('SELECT id FROM users WHERE email = %s', (email,))
        if cursor2.fetchone():
            flash('An account with this email already exists.', 'danger')
            cursor2.close()
            return render_template('register.html', faculties=faculties, courses=courses)

        cursor2.execute('SELECT id FROM roles WHERE name = %s', (role_name,))
        role_row = cursor2.fetchone()
        if not role_row:
            flash('Invalid user type.', 'danger')
            cursor2.close()
            return render_template('register.html', faculties=faculties, courses=courses)
        role_id = role_row[0]

        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor2.execute(
            'INSERT INTO users (full_name, email, phone, student_staff_id, password_hash, role_id, faculty_id, course_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
            (full_name, email, phone, student_staff_id, password_hash, role_id, faculty_id or None, course_id or None)
        )
        db.commit()
        user_id = cursor2.lastrowid

        log_activity(user_id, 'registration', 'New user registered')
        cursor2.close()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', faculties=faculties, courses=courses)


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        

        if user:
            flash('If an account with that email exists, a password reset link has been sent.', 'info')
        else:
            flash('If an account with that email exists, a password reset link has been sent.', 'info')

        return render_template('forgot_password.html')

    return render_template('forgot_password.html')


@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log_activity(user_id, 'logout', 'User logged out')
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT password_hash FROM users WHERE id = %s', (session['user_id'],))
        row = cursor.fetchone()

        if not row or not bcrypt.checkpw(current_password.encode('utf-8'), row[0].encode('utf-8')):
            flash('Current password is incorrect.', 'danger')
            cursor.close()
            
            return render_template('change_password.html')

        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            cursor.close()
            
            return render_template('change_password.html')

        if len(new_password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            cursor.close()
            
            return render_template('change_password.html')

        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s', (new_hash, session['user_id']))
        db.commit()
        cursor.close()
        

        flash('Password changed successfully.', 'success')
        return redirect(url_for('profile'))

    return render_template('change_password.html')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    return redirect(url_for('settings'))


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cursor.fetchone()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        student_staff_id = request.form.get('student_staff_id', '').strip()

        profile_image = request.files.get('profile_image')
        image_path = user[11] if user else None

        if profile_image and profile_image.filename:
            allowed = {'jpg', 'jpeg', 'png', 'webp'}
            ext = profile_image.filename.rsplit('.', 1)[1].lower() if '.' in profile_image.filename else ''
            if ext not in allowed:
                flash('Invalid image type. Use JPG, PNG, or WebP.', 'danger')
                return redirect(url_for('settings'))
            profile_image.seek(0, 2)
            size = profile_image.tell()
            profile_image.seek(0)
            if size > 5 * 1024 * 1024:
                flash('Image must be under 5 MB.', 'danger')
                return redirect(url_for('settings'))
            image_path = save_image(profile_image, 'avatars')

        cursor.execute(
            'UPDATE users SET full_name = %s, phone = %s, student_staff_id = %s, profile_image = %s WHERE id = %s',
            (full_name, phone, student_staff_id, image_path, session['user_id'])
        )
        db.commit()
        session['full_name'] = full_name
        session['phone'] = phone
        session['student_staff_id'] = student_staff_id
        session['profile_image'] = image_path

        log_activity(session['user_id'], 'profile_update', 'Updated profile')
        flash('Profile updated successfully.', 'success')
        cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()

    cursor.execute('SELECT id, name FROM faculties WHERE is_active = TRUE ORDER BY name')
    faculties = cursor.fetchall()
    cursor.execute('SELECT id, name FROM courses WHERE is_active = TRUE ORDER BY name')
    courses = cursor.fetchall()
    role_name = get_role_name(user[6]) if user else 'Unknown'
    is_admin = session.get('role_name') == 'Administrator'
    cursor.close()

    return render_template(
        'settings.html', user=user, faculties=faculties,
        courses=courses, role_name=role_name, is_admin=is_admin
    )


@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    cursor = db.cursor()
    user_id = session['user_id']

    cursor.execute(
        "SELECT "
        "(SELECT COUNT(*) FROM lost_items WHERE reporter_id = %s) AS total_lost, "
        "(SELECT COUNT(*) FROM found_items WHERE finder_id = %s) AS total_found, "
        "(SELECT COUNT(*) FROM lost_items WHERE reporter_id = %s AND status = 'reported') AS pending_reports, "
        "(SELECT COUNT(*) FROM matches m JOIN lost_items li ON m.lost_item_id = li.id "
        "   JOIN found_items fi ON m.found_item_id = fi.id "
        "   WHERE m.status = 'pending' AND (li.reporter_id = %s OR fi.finder_id = %s)) AS pending_matches, "
        "(SELECT COUNT(*) FROM matches m JOIN lost_items li ON m.lost_item_id = li.id "
        "   JOIN found_items fi ON m.found_item_id = fi.id "
        "   WHERE m.status = 'approved' AND (li.reporter_id = %s OR fi.finder_id = %s)) AS approved_matches, "
        "(SELECT COUNT(*) FROM recoveries r JOIN matches m ON r.match_id = m.id "
        "   JOIN lost_items li ON m.lost_item_id = li.id "
        "   JOIN found_items fi ON m.found_item_id = fi.id "
        "   WHERE r.status = 'completed' AND (li.reporter_id = %s OR fi.finder_id = %s)) AS recovered",
        (user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id)
    )
    row = cursor.fetchone()
    total_lost, total_found, pending_reports, pending_matches, approved_matches, recovered = row

    cursor.execute(
        "SELECT * FROM lost_items WHERE reporter_id = %s ORDER BY created_at DESC LIMIT 5",
        (user_id,)
    )
    recent_lost = cursor.fetchall()

    cursor.execute(
        "SELECT * FROM found_items WHERE finder_id = %s ORDER BY created_at DESC LIMIT 5",
        (user_id,)
    )
    recent_found = cursor.fetchall()

    cursor.execute(
        "SELECT m.*, li.reference as lost_ref, li.item_name as lost_name, "
        "fi.reference as found_ref, fi.item_name as found_name "
        "FROM matches m JOIN lost_items li ON m.lost_item_id = li.id "
        "JOIN found_items fi ON m.found_item_id = fi.id "
        "WHERE li.reporter_id = %s OR fi.finder_id = %s "
        "ORDER BY m.created_at DESC LIMIT 5",
        (user_id, user_id)
    )
    recent_matches = cursor.fetchall()

    cursor.execute(
        "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT 10",
        (user_id,)
    )
    notifications = cursor.fetchall()

    cursor.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id = %s AND is_read = FALSE",
        (user_id,)
    )
    unread_count = cursor.fetchone()[0]

    cursor.close()

    session['_unread_count'] = unread_count

    stats = {
        'total_lost': total_lost,
        'total_found': total_found,
        'pending_matches': pending_matches,
        'approved_matches': approved_matches,
        'recovered': recovered,
        'pending_reports': pending_reports,
    }

    return render_template(
        'dashboard.html',
        stats=stats,
        recent_lost=recent_lost,
        recent_found=recent_found,
        recent_matches=recent_matches,
        notifications=notifications,
        unread_count=unread_count
    )


# ==================== REPORT LOST ITEM ====================

@app.route('/report-lost', methods=['GET', 'POST'])
@login_required
def report_lost():
    if request.method == 'POST':
        item_name = request.form.get('item_name', '').strip()
        category_id = request.form.get('category_id')
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        color = request.form.get('color', '').strip()
        shape = request.form.get('shape', '').strip()
        serial_number = request.form.get('serial_number', '').strip()
        unique_marks = request.form.get('unique_marks', '').strip()
        description = request.form.get('description', '').strip()
        approximate_value = request.form.get('approximate_value')
        date_lost = request.form.get('date_lost')
        time_lost = request.form.get('time_lost')
        location_id = request.form.get('location_id')
        location_detail = request.form.get('location_detail', '').strip()
        additional_details = request.form.get('additional_details', '').strip()

        if not item_name or not date_lost:
            flash('Item name and date lost are required.', 'danger')
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id, name FROM categories WHERE is_active = TRUE ORDER BY name')
            categories = cursor.fetchall()
            cursor.execute('SELECT id, name FROM locations WHERE is_active = TRUE ORDER BY name')
            locations = cursor.fetchall()
            cursor.close()

            return render_template('report_lost.html', categories=categories, locations=locations)

        image_path = None
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            if file and allowed_file(file.filename):
                image_path = save_image(file, 'lost')

        reference = generate_reference('FM', 'lost')

        try:
            approx_value = float(approximate_value) if approximate_value else None
        except (ValueError, TypeError):
            approx_value = None

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO lost_items
            (reference, reporter_id, item_name, category_id, brand, model, color, shape,
             serial_number, unique_marks, description, approximate_value, date_lost, time_lost, location_id,
             location_detail, additional_details, image_path, shape_data, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'reported')""",
            (reference, session['user_id'], item_name, category_id or None, brand, model, color,
             shape or None, serial_number or None, unique_marks or None, description or None,
             approx_value, date_lost, time_lost or None,
             location_id or None, location_detail or None, additional_details or None, image_path, None)
        )
        db.commit()
        item_id = cursor.lastrowid
        log_activity(session['user_id'], 'report_lost', f'Reported lost item: {reference}')
        cursor.close()


        threading.Thread(target=_run_matcher_async, args=('lost', item_id), daemon=True).start()

        flash('Lost item reported successfully!', 'success')
        return redirect(url_for('my_reports'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, name FROM categories WHERE is_active = TRUE ORDER BY name')
    categories = cursor.fetchall()
    cursor.execute('SELECT id, name FROM locations WHERE is_active = TRUE ORDER BY name')
    locations = cursor.fetchall()
    cursor.close()

    return render_template('report_lost.html', categories=categories, locations=locations)


# ==================== REPORT FOUND ITEM ====================

@app.route('/report-found', methods=['GET', 'POST'])
@login_required
def report_found():
    if request.method == 'POST':
        item_name = request.form.get('item_name', '').strip()
        category_id = request.form.get('category_id')
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        color = request.form.get('color', '').strip()
        shape = request.form.get('shape', '').strip()
        serial_number = request.form.get('serial_number', '').strip()
        unique_marks = request.form.get('unique_marks', '').strip()
        approximate_value = request.form.get('approximate_value')
        description = request.form.get('description', '').strip()
        date_found = request.form.get('date_found')
        time_found = request.form.get('time_found')
        location_id = request.form.get('location_id')
        location_detail = request.form.get('location_detail', '').strip()
        current_location = request.form.get('current_location', '').strip()
        additional_details = request.form.get('additional_details', '').strip()

        if not item_name or not date_found:
            flash('Item name and date found are required.', 'danger')
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id, name FROM categories WHERE is_active = TRUE ORDER BY name')
            categories = cursor.fetchall()
            cursor.execute('SELECT id, name FROM locations WHERE is_active = TRUE ORDER BY name')
            locations = cursor.fetchall()
            cursor.close()

            return render_template('report_found.html', categories=categories, locations=locations)

        image_path = None
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            if file and allowed_file(file.filename):
                image_path = save_image(file, 'found')

        reference = generate_reference('FM', 'found')

        try:
            approx_value = float(approximate_value) if approximate_value else None
        except (ValueError, TypeError):
            approx_value = None

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO found_items
            (reference, finder_id, item_name, category_id, brand, model, color, shape,
             serial_number, unique_marks, approximate_value, description,
             date_found, time_found, location_id, location_detail, current_location, additional_details, image_path, shape_data, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'reported')""",
            (reference, session['user_id'], item_name, category_id or None, brand, model, color,
             shape or None, serial_number or None, unique_marks or None, approx_value,
             description or None, date_found, time_found or None, location_id or None,
             location_detail or None, current_location or None, additional_details or None, image_path, None)
        )
        db.commit()
        item_id = cursor.lastrowid
        log_activity(session['user_id'], 'report_found', f'Reported found item: {reference}')
        cursor.close()


        threading.Thread(target=_run_matcher_async, args=('found', item_id), daemon=True).start()

        flash('Found item reported successfully!', 'success')
        return redirect(url_for('my_reports'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, name FROM categories WHERE is_active = TRUE ORDER BY name')
    categories = cursor.fetchall()
    cursor.execute('SELECT id, name FROM locations WHERE is_active = TRUE ORDER BY name')
    locations = cursor.fetchall()
    cursor.close()

    return render_template('report_found.html', categories=categories, locations=locations)


# ==================== MY REPORTS ====================

@app.route('/my-reports')
@login_required
def my_reports():
    db = get_db()
    cursor = db.cursor()
    user_id = session['user_id']

    cursor.execute(
        'SELECT li.*, c.name as category_name FROM lost_items li LEFT JOIN categories c ON li.category_id = c.id WHERE li.reporter_id = %s ORDER BY li.created_at DESC LIMIT 50',
        (user_id,)
    )
    lost_reports = cursor.fetchall()

    cursor.execute(
        'SELECT fi.*, c.name as category_name FROM found_items fi LEFT JOIN categories c ON fi.category_id = c.id WHERE fi.finder_id = %s ORDER BY fi.created_at DESC LIMIT 50',
        (user_id,)
    )
    found_reports = cursor.fetchall()

    cursor.close()


    return render_template(
        'my_reports.html',
        lost_reports=lost_reports,
        found_reports=found_reports
    )


# ==================== SEARCH ====================

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category_id')
    location_id = request.args.get('location_id')
    report_type = request.args.get('type', '')
    status = request.args.get('status', '')

    db = get_db()
    cursor = db.cursor()

    results = []
    if query or category_id or location_id or report_type or status:
        where_clauses = []
        params_lost = []
        params_found = []

        if query:
            clause = '(item_name LIKE %s OR description LIKE %s OR brand LIKE %s OR color LIKE %s)'
            where_clauses.append(clause)
            params_lost.extend([f'%{query}%'] * 4)
            params_found.extend([f'%{query}%'] * 4)

        if category_id:
            where_clauses.append('category_id = %s')
            params_lost.append(category_id)
            params_found.append(category_id)

        if location_id:
            where_clauses.append('location_id = %s')
            params_lost.append(location_id)
            params_found.append(location_id)

        if status:
            where_clauses.append('status = %s')
            params_lost.append(status)
            params_found.append(status)

        where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'

        results = []
        if report_type in ('', 'lost'):
            cursor.execute(
                f"""SELECT 'lost' as type, id as item_id, reference, item_name, category_id, brand, 
                color, description, date_lost as date, location_id, location_detail, status, image_path 
                FROM lost_items WHERE {where_sql}
                ORDER BY created_at DESC LIMIT 100""",
                params_lost
            )
            results.extend(cursor.fetchall())

        if report_type in ('', 'found'):
            cursor.execute(
                f"""SELECT 'found' as type, id as item_id, reference, item_name, category_id, brand, 
                color, description, date_found as date, location_id, location_detail, status, image_path 
                FROM found_items WHERE {where_sql}
                ORDER BY created_at DESC LIMIT 100""",
                params_found
            )
            results.extend(cursor.fetchall())

    cursor.execute('SELECT id, name FROM categories WHERE is_active = TRUE ORDER BY name')
    categories = cursor.fetchall()
    cursor.execute('SELECT id, name FROM locations WHERE is_active = TRUE ORDER BY name')
    locations = cursor.fetchall()
    cursor.close()


    return render_template(
        'search.html',
        results=results,
        categories=categories,
        locations=locations,
        q=query,
        category_id=category_id,
        location_id=location_id,
        report_type=report_type,
        status=status
    )


# ==================== ITEM DETAIL ====================

@app.route('/item/<item_type>/<int:item_id>')
@login_required
def item_detail(item_type, item_id):
    db = get_db()
    cursor = db.cursor()

    if item_type == 'lost':
        cursor.execute('SELECT * FROM lost_items WHERE id = %s', (item_id,))
        item = cursor.fetchone()
        if not item:
            abort(404)
        reporter_id = item[2]
        cursor.execute('SELECT full_name, email FROM users WHERE id = %s', (reporter_id,))
        reporter = cursor.fetchone()
    else:
        cursor.execute('SELECT * FROM found_items WHERE id = %s', (item_id,))
        item = cursor.fetchone()
        if not item:
            abort(404)
        finder_id = item[2]
        cursor.execute('SELECT full_name, email FROM users WHERE id = %s', (finder_id,))
        reporter = cursor.fetchone()

    cursor.execute('SELECT id, name FROM categories WHERE is_active = TRUE ORDER BY name')
    categories = cursor.fetchall()
    cursor.execute('SELECT id, name FROM locations WHERE is_active = TRUE ORDER BY name')
    locations = cursor.fetchall()
    cursor.close()

    return render_template(
        'item_detail.html',
        item=item,
        item_type=item_type,
        reporter=reporter,
        categories=categories,
        locations=locations
    )


# ==================== AI MATCHES ====================

@app.route('/matches')
@login_required
def matches():
    db = get_db()
    cursor = db.cursor()
    user_id = session['user_id']

    cursor.execute(
        """SELECT m.*, 
        li.reference as lost_ref, li.item_name as lost_name, li.color as lost_color, li.shape as lost_shape,
        fi.reference as found_ref, fi.item_name as found_name, fi.color as found_color, fi.shape as found_shape,
        u1.full_name as lost_reporter, u2.full_name as found_reporter
        FROM matches m 
        JOIN lost_items li ON m.lost_item_id = li.id 
        JOIN found_items fi ON m.found_item_id = fi.id 
        LEFT JOIN users u1 ON li.reporter_id = u1.id 
        LEFT JOIN users u2 ON fi.finder_id = u2.id 
        WHERE li.reporter_id = %s OR fi.finder_id = %s 
        ORDER BY m.created_at DESC LIMIT 100""",
        (user_id, user_id)
    )
    user_matches = cursor.fetchall()

    cursor.close()

    return render_template('matches.html', matches=user_matches)


@app.route('/match/<int:match_id>')
@login_required
def match_detail(match_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT m.*, 
        li.reference as lost_ref, li.item_name as lost_name, li.description as lost_desc, li.color as lost_color, li.shape as lost_shape, li.serial_number as lost_serial, li.unique_marks as lost_marks, li.approximate_value as lost_value, li.brand as lost_brand, li.image_path as lost_image, li.location_detail as lost_loc,
        fi.reference as found_ref, fi.item_name as found_name, fi.description as found_desc, fi.color as found_color, fi.shape as found_shape, fi.serial_number as found_serial, fi.unique_marks as found_marks, fi.approximate_value as found_value, fi.brand as found_brand, fi.image_path as found_image, fi.location_detail as found_loc,
        u1.full_name as lost_reporter, u2.full_name as found_reporter
        FROM matches m 
        JOIN lost_items li ON m.lost_item_id = li.id 
        JOIN found_items fi ON m.found_item_id = fi.id 
        LEFT JOIN users u1 ON li.reporter_id = u1.id 
        LEFT JOIN users u2 ON fi.finder_id = u2.id
        WHERE m.id = %s
    ''', (match_id,))
    match = cursor.fetchone()

    cursor.close()


    if not match:
        abort(404)

    return render_template('match_detail.html', match=match)


# ==================== NOTIFICATIONS ====================

@app.route('/notifications')
@login_required
def notifications():
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        'SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT 50',
        (session['user_id'],)
    )
    notifs = cursor.fetchall()

    cursor.execute(
        'UPDATE notifications SET is_read = TRUE WHERE user_id = %s',
        (session['user_id'],)
    )
    db.commit()

    cursor.close()


    return render_template('notifications.html', notifications=notifs, unread_count=0)


# ==================== ADMIN ROUTES ====================

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role_id = 1")
    total_students = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role_id = 2")
    total_lecturers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role_id = 3")
    total_admins = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM lost_items")
    total_lost = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM found_items")
    total_found = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM matches WHERE status = 'pending'")
    pending_matches = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM matches WHERE status = 'approved'")
    approved_matches = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM recoveries WHERE status = 'completed'")
    recovered = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM lost_items WHERE status = 'reported'")
    pending_reports = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM lost_items ORDER BY created_at DESC LIMIT 5")
    recent_lost = cursor.fetchall()

    cursor.execute("SELECT * FROM found_items ORDER BY created_at DESC LIMIT 5")
    recent_found = cursor.fetchall()

    cursor.execute("SELECT m.*, li.reference as lost_ref, fi.reference as found_ref FROM matches m JOIN lost_items li ON m.lost_item_id = li.id JOIN found_items fi ON m.found_item_id = fi.id WHERE m.status = 'pending' ORDER BY m.created_at DESC LIMIT 5")
    pending_match_list = cursor.fetchall()

    cursor.execute("SELECT action, description, created_at FROM activity_logs ORDER BY created_at DESC LIMIT 10")
    recent_logs = cursor.fetchall()

    cursor.close()


    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_students=total_students,
        total_lecturers=total_lecturers,
        total_admins=total_admins,
        total_lost=total_lost,
        total_found=total_found,
        pending_matches=pending_matches,
        approved_matches=approved_matches,
        recovered=recovered,
        pending_reports=pending_reports,
        recent_lost=recent_lost,
        recent_found=recent_found,
        pending_match_list=pending_match_list,
        recent_logs=recent_logs
    )


@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    db = get_db()
    cursor = db.cursor()
    base = '''SELECT u.id, u.full_name, u.email, u.phone, u.student_staff_id, u.is_active, u.created_at, 
               r.name as role_name, f.name as faculty_name, c.name as course_name 
        FROM users u 
        JOIN roles r ON u.role_id = r.id 
        LEFT JOIN faculties f ON u.faculty_id = f.id 
        LEFT JOIN courses c ON u.course_id = c.id'''
    users, page, total_pages, total = paginated_query(
        cursor,
        base + ' ORDER BY u.created_at DESC',
        'SELECT COUNT(*) FROM users',
        [], page
    )
    cursor.close()

    return render_template('admin/users.html', users=users, page=page, total_pages=total_pages, total=total)


@app.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_user(user_id):
    if user_id == session['user_id']:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin_users'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT is_active FROM users WHERE id = %s', (user_id,))
    row = cursor.fetchone()
    if row:
        new_status = not row[0]
        cursor.execute('UPDATE users SET is_active = %s WHERE id = %s', (new_status, user_id))
        db.commit()
        status = 'active' if new_status else 'deactivated'
        log_activity(session['user_id'], 'toggle_user', f'Toggled user {user_id} to {status}')
        flash(f'User {status} successfully.', 'success')
    cursor.close()

    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    if user_id == session['user_id']:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_users'))

    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT full_name FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        flash('User not found.', 'danger')
        return redirect(url_for('admin_users'))

    user_name = user[0]

    cursor.execute('DELETE FROM notifications WHERE user_id = %s', (user_id,))
    cursor.execute('DELETE FROM activity_logs WHERE user_id = %s', (user_id,))
    cursor.execute('DELETE FROM verification_requests WHERE requester_id = %s OR claimer_id = %s', (user_id, user_id))
    cursor.execute('DELETE FROM recoveries WHERE recovered_by_id = %s', (user_id,))
    cursor.execute('UPDATE matches SET reviewed_by = NULL WHERE reviewed_by = %s', (user_id,))
    cursor.execute('UPDATE lost_items SET verified_by = NULL WHERE verified_by = %s', (user_id,))
    cursor.execute('UPDATE found_items SET verified_by = NULL WHERE verified_by = %s', (user_id,))

    cursor.execute('SELECT id FROM lost_items WHERE reporter_id = %s', (user_id,))
    lost_ids = [r[0] for r in cursor.fetchall()]
    cursor.execute('SELECT id FROM found_items WHERE finder_id = %s', (user_id,))
    found_ids = [r[0] for r in cursor.fetchall()]

    for lid in lost_ids:
        cursor.execute('DELETE FROM recoveries WHERE match_id IN (SELECT id FROM matches WHERE lost_item_id = %s)', (lid,))
    for fid in found_ids:
        cursor.execute('DELETE FROM recoveries WHERE match_id IN (SELECT id FROM matches WHERE found_item_id = %s)', (fid,))

    for lid in lost_ids:
        cursor.execute('DELETE FROM matches WHERE lost_item_id = %s', (lid,))
    for fid in found_ids:
        cursor.execute('DELETE FROM matches WHERE found_item_id = %s', (fid,))

    cursor.execute('DELETE FROM item_images WHERE item_id IN (SELECT id FROM lost_items WHERE reporter_id = %s)', (user_id,))
    cursor.execute('DELETE FROM lost_items WHERE reporter_id = %s', (user_id,))
    cursor.execute('DELETE FROM found_items WHERE finder_id = %s', (user_id,))
    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))

    db.commit()
    cursor.close()

    log_activity(session['user_id'], 'delete_user', f'Permanently deleted user: {user_name} (ID: {user_id})')
    flash(f'User "{user_name}" and all their data have been permanently deleted.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/faculties', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_faculties():
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        if name:
            cursor.execute(
                'INSERT INTO faculties (name, description) VALUES (%s, %s)',
                (name, description or None)
            )
            db.commit()
            log_activity(session['user_id'], 'add_faculty', f'Added faculty: {name}')
            flash('Faculty added successfully.', 'success')
            return redirect(url_for('admin_faculties'))

    cursor.execute('SELECT * FROM faculties ORDER BY created_at DESC')
    faculties = cursor.fetchall()
    cursor.close()

    return render_template('admin/faculties.html', faculties=faculties)


@app.route('/admin/faculties/<int:faculty_id>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_faculty(faculty_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT name, is_active FROM faculties WHERE id = %s', (faculty_id,))
    row = cursor.fetchone()
    if row:
        new_status = not row[1]
        cursor.execute('UPDATE faculties SET is_active = %s WHERE id = %s', (new_status, faculty_id))
        db.commit()
        log_activity(session['user_id'], 'toggle_faculty', f'Toggled faculty {faculty_id}')
        flash(f'Faculty {row[0]} {("activated" if new_status else "deactivated")}.', 'success')
    cursor.close()

    return redirect(url_for('admin_faculties'))


@app.route('/admin/courses', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_courses():
    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT id, name FROM faculties WHERE is_active = TRUE ORDER BY name')
    faculties_list = cursor.fetchall()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip()
        faculty_id = request.form.get('faculty_id')
        if name and faculty_id:
            cursor.execute(
                'INSERT INTO courses (name, code, faculty_id) VALUES (%s, %s, %s)',
                (name, code or None, faculty_id)
            )
            db.commit()
            log_activity(session['user_id'], 'add_course', f'Added course: {name}')
            flash('Course added successfully.', 'success')
            return redirect(url_for('admin_courses'))

    cursor.execute('SELECT c.*, f.name as faculty_name FROM courses c JOIN faculties f ON c.faculty_id = f.id ORDER BY c.created_at DESC')
    courses = cursor.fetchall()
    cursor.close()

    return render_template('admin/courses.html', courses=courses, faculties=faculties_list)


@app.route('/admin/courses/<int:course_id>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_course(course_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT name, is_active FROM courses WHERE id = %s', (course_id,))
    row = cursor.fetchone()
    if row:
        new_status = not row[1]
        cursor.execute('UPDATE courses SET is_active = %s WHERE id = %s', (new_status, course_id))
        db.commit()
        log_activity(session['user_id'], 'toggle_course', f'Toggled course {course_id}')
        flash(f'Course {row[0]} {("activated" if new_status else "deactivated")}.', 'success')
    cursor.close()

    return redirect(url_for('admin_courses'))


@app.route('/admin/categories', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_categories():
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        if name:
            cursor.execute(
                'INSERT INTO categories (name, description) VALUES (%s, %s)',
                (name, description or None)
            )
            db.commit()
            log_activity(session['user_id'], 'add_category', f'Added category: {name}')
            flash('Category added successfully.', 'success')
            return redirect(url_for('admin_categories'))

    cursor.execute('SELECT * FROM categories ORDER BY created_at DESC')
    categories = cursor.fetchall()
    cursor.close()

    return render_template('admin/categories.html', categories=categories)


@app.route('/admin/categories/<int:cat_id>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_category(cat_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT name, is_active FROM categories WHERE id = %s', (cat_id,))
    row = cursor.fetchone()
    if row:
        new_status = not row[1]
        cursor.execute('UPDATE categories SET is_active = %s WHERE id = %s', (new_status, cat_id))
        db.commit()
        log_activity(session['user_id'], 'toggle_category', f'Toggled category {cat_id}')
        flash(f'Category {row[0]} {("activated" if new_status else "deactivated")}.', 'success')
    cursor.close()

    return redirect(url_for('admin_categories'))


@app.route('/admin/locations', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_locations():
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        if name:
            cursor.execute(
                'INSERT INTO locations (name, description) VALUES (%s, %s)',
                (name, description or None)
            )
            db.commit()
            log_activity(session['user_id'], 'add_location', f'Added location: {name}')
            flash('Location added successfully.', 'success')
            return redirect(url_for('admin_locations'))

    cursor.execute('SELECT * FROM locations ORDER BY created_at DESC')
    locations = cursor.fetchall()
    cursor.close()

    return render_template('admin/locations.html', locations=locations)


@app.route('/admin/locations/<int:loc_id>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_location(loc_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT name, is_active FROM locations WHERE id = %s', (loc_id,))
    row = cursor.fetchone()
    if row:
        new_status = not row[1]
        cursor.execute('UPDATE locations SET is_active = %s WHERE id = %s', (new_status, loc_id))
        db.commit()
        log_activity(session['user_id'], 'toggle_location', f'Toggled location {loc_id}')
        flash(f'Location {row[0]} {("activated" if new_status else "deactivated")}.', 'success')
    cursor.close()

    return redirect(url_for('admin_locations'))


@app.route('/admin/lost-items')
@login_required
@admin_required
def admin_lost_items():
    page = request.args.get('page', 1, type=int)
    db = get_db()
    cursor = db.cursor()
    base = '''SELECT li.*, u.full_name as reporter_name, c.name as category_name, l.name as location_name 
        FROM lost_items li 
        JOIN users u ON li.reporter_id = u.id 
        LEFT JOIN categories c ON li.category_id = c.id 
        LEFT JOIN locations l ON li.location_id = l.id'''
    items, page, total_pages, total = paginated_query(
        cursor,
        base + ' ORDER BY li.created_at DESC',
        'SELECT COUNT(*) FROM lost_items',
        [], page
    )
    cursor.close()

    return render_template('admin/lost_items.html', items=items, page=page, total_pages=total_pages, total=total)


@app.route('/admin/found-items')
@login_required
@admin_required
def admin_found_items():
    page = request.args.get('page', 1, type=int)
    db = get_db()
    cursor = db.cursor()
    base = '''SELECT fi.*, u.full_name as finder_name, c.name as category_name, l.name as location_name 
        FROM found_items fi 
        JOIN users u ON fi.finder_id = u.id 
        LEFT JOIN categories c ON fi.category_id = c.id 
        LEFT JOIN locations l ON fi.location_id = l.id'''
    items, page, total_pages, total = paginated_query(
        cursor,
        base + ' ORDER BY fi.created_at DESC',
        'SELECT COUNT(*) FROM found_items',
        [], page
    )
    cursor.close()

    return render_template('admin/found_items.html', items=items, page=page, total_pages=total_pages, total=total)


@app.route('/admin/matches')
@login_required
@admin_required
def admin_matches():
    page = request.args.get('page', 1, type=int)
    db = get_db()
    cursor = db.cursor()
    status_filter = request.args.get('status', 'pending')
    all_statuses = ['pending', 'approved', 'rejected', 'uncertain']
    base = '''SELECT m.*, 
            li.reference as lost_ref, li.item_name as lost_name, li.color as lost_color, li.shape as lost_shape, li.serial_number as lost_serial, li.unique_marks as lost_marks, li.approximate_value as lost_value, li.image_path as lost_image,
            fi.reference as found_ref, fi.item_name as found_name, fi.color as found_color, fi.shape as found_shape, fi.serial_number as found_serial, fi.unique_marks as found_marks, fi.approximate_value as found_value, fi.image_path as found_image,
            u1.full_name as lost_reporter, u2.full_name as found_reporter
            FROM matches m 
            JOIN lost_items li ON m.lost_item_id = li.id 
            JOIN found_items fi ON m.found_item_id = fi.id 
            LEFT JOIN users u1 ON li.reporter_id = u1.id 
            LEFT JOIN users u2 ON fi.finder_id = u2.id'''
    if status_filter in all_statuses:
        items, page, total_pages, total = paginated_query(
            cursor,
            base + ' WHERE m.status = %s ORDER BY m.created_at DESC',
            'SELECT COUNT(*) FROM matches WHERE status = %s',
            [status_filter], page
        )
    else:
        items, page, total_pages, total = paginated_query(
            cursor,
            base + ' ORDER BY m.created_at DESC',
            'SELECT COUNT(*) FROM matches',
            [], page
        )
        status_filter = 'all'
    cursor.close()

    return render_template('admin/ai_matches.html', matches=items, status_filter=status_filter, page=page, total_pages=total_pages, total=total)


@app.route('/admin/match/<int:match_id>/approve', methods=['POST'])
@login_required
@admin_required
def admin_approve_match(match_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE matches SET status = "approved", reviewed_by = %s, reviewed_at = NOW() WHERE id = %s',
                   (session['user_id'], match_id))
    db.commit()

    cursor.execute('SELECT lost_item_id, found_item_id FROM matches WHERE id = %s', (match_id,))
    match = cursor.fetchone()
    if match:
        cursor.execute('UPDATE lost_items SET status = "match_approved" WHERE id = %s', (match[0],))
        cursor.execute('UPDATE found_items SET status = "match_approved" WHERE id = %s', (match[1],))
        db.commit()

        cursor.execute(
            'SELECT li.reporter_id, fi.finder_id FROM lost_items li JOIN found_items fi ON fi.id = %s WHERE li.id = %s',
            (match[1], match[0])
        )
        users = cursor.fetchone()
        if users:
            cursor.execute(
                'INSERT INTO notifications (user_id, title, message, type, related_type, related_id) VALUES (%s, %s, %s, %s, %s, %s)',
                (users[0], 'Match Approved', 'Your lost item has been matched. Check your matches.', 'match', 'match', match_id)
            )
            cursor.execute(
                'INSERT INTO notifications (user_id, title, message, type, related_type, related_id) VALUES (%s, %s, %s, %s, %s, %s)',
                (users[1], 'Match Approved', 'Your found item has been matched. Check your matches.', 'match', 'match', match_id)
            )
        db.commit()

    log_activity(session['user_id'], 'approve_match', f'Approved match {match_id}')
    cursor.close()
    flash('Match approved successfully.', 'success')
    return redirect(url_for('admin_matches'))


@app.route('/admin/match/<int:match_id>/reject', methods=['POST'])
@login_required
@admin_required
def admin_reject_match(match_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE matches SET status = "rejected", reviewed_by = %s, reviewed_at = NOW() WHERE id = %s',
                   (session['user_id'], match_id))
    db.commit()
    log_activity(session['user_id'], 'reject_match', f'Rejected match {match_id}')
    cursor.close()
    flash('Match rejected.', 'info')
    return redirect(url_for('admin_matches'))


@app.route('/admin/verifications')
@login_required
@admin_required
def admin_verifications():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT v.*, m.id as match_id,
        li.reference as lost_ref, li.item_name as lost_name,
        fi.reference as found_ref, fi.item_name as found_name,
        u.full_name as requester_name
        FROM verification_requests v
        JOIN matches m ON v.match_id = m.id
        JOIN lost_items li ON m.lost_item_id = li.id
        JOIN found_items fi ON m.found_item_id = fi.id
        JOIN users u ON v.requester_id = u.id
        WHERE v.status = 'pending'
        ORDER BY v.created_at DESC
    ''')
    verifications = cursor.fetchall()
    cursor.close()

    return render_template('admin/verifications.html', verifications=verifications)


@app.route('/admin/verification/<int:ver_id>/approve', methods=['POST'])
@login_required
@admin_required
def admin_approve_verification(ver_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM verification_requests WHERE id = %s', (ver_id,))
    ver = cursor.fetchone()
    if ver:
        cursor.execute('UPDATE verification_requests SET status = "approved", reviewed_by = %s, reviewed_at = NOW() WHERE id = %s',
                       (session['user_id'], ver_id))
        db.commit()

        cursor.execute('UPDATE matches SET status = "approved", reviewed_by = %s, reviewed_at = NOW() WHERE id = %s',
                       (session['user_id'], ver[1]))
        db.commit()

        cursor.execute(
            'INSERT INTO notifications (user_id, title, message, type, related_type, related_id) VALUES (%s, %s, %s, %s, %s, %s)',
            (ver[3], 'Verification Approved', 'Your ownership verification has been approved.', 'recovery', 'match', ver[1])
        )
        cursor.execute(
            'INSERT INTO notifications (user_id, title, message, type, related_type, related_id) VALUES (%s, %s, %s, %s, %s, %s)',
            (ver[2], 'Verification Approved', 'The ownership verification has been approved.', 'recovery', 'match', ver[1])
        )
        db.commit()

        log_activity(session['user_id'], 'approve_verification', f'Approved verification {ver_id}')
        flash('Verification approved and match confirmed.', 'success')

    cursor.close()

    return redirect(url_for('admin_verifications'))


@app.route('/admin/verification/<int:ver_id>/reject', methods=['POST'])
@login_required
@admin_required
def admin_reject_verification(ver_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE verification_requests SET status = "rejected", reviewed_by = %s, reviewed_at = NOW() WHERE id = %s',
                   (session['user_id'], ver_id))
    db.commit()
    log_activity(session['user_id'], 'reject_verification', f'Rejected verification {ver_id}')
    cursor.close()

    flash('Verification rejected.', 'info')
    return redirect(url_for('admin_verifications'))


@app.route('/admin/recoveries')
@login_required
@admin_required
def admin_recoveries():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT r.*, m.id as match_id,
        li.reference as lost_ref, li.item_name as lost_name,
        fi.reference as found_ref, fi.item_name as found_name,
        u.full_name as recovered_by_name
        FROM recoveries r
        JOIN matches m ON r.match_id = m.id
        JOIN lost_items li ON m.lost_item_id = li.id
        JOIN found_items fi ON m.found_item_id = fi.id
        JOIN users u ON r.recovered_by_id = u.id
        ORDER BY r.created_at DESC
    ''')
    recoveries_list = cursor.fetchall()
    cursor.close()

    return render_template('admin/recoveries.html', recoveries=recoveries_list)


@app.route('/admin/recovery/<int:recovery_id>/complete', methods=['POST'])
@login_required
@admin_required
def admin_complete_recovery(recovery_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE recoveries SET status = "completed", recovered_date = CURDATE() WHERE id = %s', (recovery_id,))
    db.commit()

    cursor.execute('SELECT match_id FROM recoveries WHERE id = %s', (recovery_id,))
    recovery = cursor.fetchone()
    if recovery:
        cursor.execute('UPDATE matches SET status = "approved" WHERE id = %s', (recovery[0],))
        cursor.execute(
            'UPDATE lost_items SET status = "recovered" WHERE id = (SELECT lost_item_id FROM matches WHERE id = %s)',
            (recovery[0],)
        )
        cursor.execute(
            'UPDATE found_items SET status = "recovered" WHERE id = (SELECT found_item_id FROM matches WHERE id = %s)',
            (recovery[0],)
        )
        db.commit()
        log_activity(session['user_id'], 'complete_recovery', f'Completed recovery {recovery_id}')

    cursor.close()

    flash('Recovery marked as completed.', 'success')
    return redirect(url_for('admin_recoveries'))


@app.route('/admin/reports')
@login_required
@admin_required
def admin_reports():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM lost_items")
    total_lost = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM found_items")
    total_found = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM matches WHERE status = 'pending'")
    pending_matches = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM matches WHERE status = 'approved'")
    approved_matches = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM matches WHERE status = 'rejected'")
    rejected_matches = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM recoveries WHERE status = 'completed'")
    total_recovered = cursor.fetchone()[0]

    cursor.execute('''
        SELECT c.name as category_name,
               COALESCE(l.cnt, 0) as lost_count,
               COALESCE(f.cnt, 0) as found_count
        FROM categories c
        LEFT JOIN (SELECT category_id, COUNT(*) as cnt FROM lost_items GROUP BY category_id) l ON c.id = l.category_id
        LEFT JOIN (SELECT category_id, COUNT(*) as cnt FROM found_items GROUP BY category_id) f ON c.id = f.category_id
        ORDER BY c.name
    ''')
    by_category = cursor.fetchall()

    cursor.close()

    return render_template(
        'admin/reports.html',
        total_lost=total_lost,
        total_found=total_found,
        pending_matches=pending_matches,
        approved_matches=approved_matches,
        rejected_matches=rejected_matches,
        total_recovered=total_recovered,
        by_category=by_category
    )


@app.route('/admin/activity-logs')
@login_required
@admin_required
def admin_activity_logs():
    page = request.args.get('page', 1, type=int)
    db = get_db()
    cursor = db.cursor()
    base = '''SELECT al.*, u.full_name as user_name 
        FROM activity_logs al 
        LEFT JOIN users u ON al.user_id = u.id'''
    logs, page, total_pages, total = paginated_query(
        cursor,
        base + ' ORDER BY al.created_at DESC',
        'SELECT COUNT(*) FROM activity_logs',
        [], page, per_page=50
    )
    cursor.close()

    return render_template('admin/activity_logs.html', logs=logs, page=page, total_pages=total_pages, total=total)


ITEM_STATUSES = {
    'reported', 'under_review', 'potential_match', 'match_pending_approval',
    'match_approved', 'match_rejected', 'owner_verification_pending',
    'owner_verified', 'recovered', 'closed', 'archived'
}


@app.route('/admin/lost-items/<int:item_id>/edit-status', methods=['POST'])
@login_required
@admin_required
def admin_edit_lost_status(item_id):
    db = get_db()
    cursor = db.cursor()
    new_status = request.form.get('status')
    if new_status in ITEM_STATUSES:
        cursor.execute('UPDATE lost_items SET status = %s WHERE id = %s', (new_status, item_id))
        db.commit()
        log_activity(session['user_id'], 'update_lost_status', f'Updated lost item {item_id} status to {new_status}')
    else:
        flash('Invalid status value.', 'danger')
    cursor.close()

    return redirect(url_for('admin_lost_items'))


@app.route('/admin/found-items/<int:item_id>/edit-status', methods=['POST'])
@login_required
@admin_required
def admin_edit_found_status(item_id):
    db = get_db()
    cursor = db.cursor()
    new_status = request.form.get('status')
    if new_status in ITEM_STATUSES:
        cursor.execute('UPDATE found_items SET status = %s WHERE id = %s', (new_status, item_id))
        db.commit()
        log_activity(session['user_id'], 'update_found_status', f'Updated found item {item_id} status to {new_status}')
    else:
        flash('Invalid status value.', 'danger')
    cursor.close()

    return redirect(url_for('admin_found_items'))


@app.route('/admin/settings')
@login_required
@admin_required
def admin_settings():
    return redirect(url_for('settings'))


@app.route('/admin/reset', methods=['POST'])
@login_required
@admin_required
def admin_reset_data():
    db = get_db()
    cursor = db.cursor()

    confirm = request.form.get('confirm', '').strip()
    if confirm != 'RESET':
        flash('Type RESET to confirm.', 'danger')
        return redirect(url_for('settings'))

    reset_type = request.form.get('reset_type', 'activity')

    if reset_type not in ('activity', 'all'):
        flash('Invalid reset type.', 'danger')
        return redirect(url_for('settings'))

    tables = [
        'activity_logs', 'recoveries', 'verification_requests',
        'notifications', 'matches', 'item_images',
        'found_items', 'lost_items'
    ]
    for t in tables:
        cursor.execute(f'DELETE FROM {t}')
    if reset_type == 'all':
        cursor.execute('DELETE FROM users WHERE role_id != 3')
        cursor.execute('UPDATE users SET profile_image = NULL WHERE role_id != 3')

    db.commit()
    cursor.close()

    log_activity(session['user_id'], 'system_reset', f'Reset all {reset_type} data')
    flash(f'All {reset_type} data has been reset.', 'success')
    return redirect(url_for('settings'))


# ==================== IMAGE ACCESS ====================

@app.route('/uploads/<path:filename>')
def serve_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.errorhandler(413)
def request_entity_too_large(error):
    flash('File too large. Maximum size is 16MB.', 'danger')
    return redirect(request.referrer or url_for('dashboard'))


@app.context_processor
def inject_now():
    now = datetime.now()
    unread_count = session.get('_unread_count', 0)
    return {'now': now, 'unread_count': unread_count}


# ==================== RUN ====================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)