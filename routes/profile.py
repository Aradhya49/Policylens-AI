import os
import uuid
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, current_app
from db import get_db_connection

profile_bp = Blueprint('profile', __name__)

ALLOWED_IMAGE_EXTS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTS


def get_user_safe(user_id):
    """Fetch user — works whether or not profile_picture column exists."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Try with profile_picture column first
        cursor.execute(
            'SELECT id, username, email, created_at, profile_picture FROM users WHERE id = %s',
            (user_id,)
        )
    except Exception:
        # Column doesn't exist yet — fetch without it
        cursor.execute(
            'SELECT id, username, email, created_at FROM users WHERE id = %s',
            (user_id,)
        )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user and 'profile_picture' not in user:
        user['profile_picture'] = None
    return user


@profile_bp.route('/profile')
@login_required
def index():
    user_id = session['user_id']
    try:
        user = get_user_safe(user_id)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT COUNT(*) AS total FROM uploaded_documents WHERE user_id = %s', (user_id,))
        total_docs = cursor.fetchone()['total']
        cursor.execute('SELECT COUNT(*) AS total FROM ai_analyses WHERE user_id = %s', (user_id,))
        total_analyses = cursor.fetchone()['total']
        cursor.close()
        conn.close()

        return render_template('profile/index.html',
                               user=user,
                               total_docs=total_docs,
                               total_analyses=total_analyses)
    except Exception as e:
        flash(f'Error loading profile: {str(e)}', 'danger')
        return render_template('profile/index.html',
                               user={'username': session.get('username', ''),
                                     'email': session.get('email', ''),
                                     'created_at': None,
                                     'profile_picture': None},
                               total_docs=0,
                               total_analyses=0)


@profile_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    user_id      = session['user_id']
    new_username = request.form.get('username', '').strip()
    new_email    = request.form.get('email', '').strip()
    new_password = request.form.get('new_password', '').strip()
    confirm_pw   = request.form.get('confirm_new_password', '').strip()

    if not new_username or not new_email:
        flash('Username and email cannot be empty.', 'danger')
        return redirect(url_for('profile.index'))

    # Validate password if provided
    if new_password:
        if len(new_password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('profile.index'))
        if new_password != confirm_pw:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('profile.index'))

    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check for duplicates excluding current user
        cursor.execute(
            'SELECT id FROM users WHERE (username=%s OR email=%s) AND id != %s',
            (new_username, new_email, user_id)
        )
        if cursor.fetchone():
            flash('That username or email is already taken.', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('profile.index'))

        # Update username and email
        if new_password:
            import bcrypt
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute(
                'UPDATE users SET username=%s, email=%s, password_hash=%s WHERE id=%s',
                (new_username, new_email, password_hash, user_id)
            )
            flash('Profile and password updated successfully!', 'success')
        else:
            cursor.execute(
                'UPDATE users SET username=%s, email=%s WHERE id=%s',
                (new_username, new_email, user_id)
            )
            flash('Profile updated successfully!', 'success')

        conn.commit()
        cursor.close()
        conn.close()

        session['username'] = new_username
        session['email']    = new_email

    except Exception as e:
        flash(f'Update failed: {str(e)}', 'danger')

    return redirect(url_for('profile.index'))


@profile_bp.route('/profile/upload-picture', methods=['POST'])
@login_required
def upload_picture():
    user_id = session['user_id']
    file    = request.files.get('profile_picture')

    if not file or file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('profile.index'))

    if not allowed_image(file.filename):
        flash('Only PNG, JPG, JPEG, GIF, WEBP images are allowed.', 'danger')
        return redirect(url_for('profile.index'))

    try:
        ext      = file.filename.rsplit('.', 1)[1].lower()
        filename = f"profile_{user_id}_{uuid.uuid4().hex[:8]}.{ext}"

        profile_dir = os.path.join(current_app.root_path, 'static', 'images', 'profiles')
        os.makedirs(profile_dir, exist_ok=True)

        # Delete old picture if any
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute('SELECT profile_picture FROM users WHERE id=%s', (user_id,))
            row = cursor.fetchone()
            if row and row.get('profile_picture'):
                old_path = os.path.join(profile_dir, row['profile_picture'])
                if os.path.exists(old_path):
                    os.remove(old_path)
            file.save(os.path.join(profile_dir, filename))
            cursor.execute('UPDATE users SET profile_picture=%s WHERE id=%s', (filename, user_id))
            conn.commit()
            flash('Profile picture updated!', 'success')
        except Exception:
            # profile_picture column might not exist — run the migration SQL
            flash('Please run migrate_profile_picture.sql in MySQL first, then try again.', 'warning')
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        flash(f'Upload failed: {str(e)}', 'danger')

    return redirect(url_for('profile.index'))


@profile_bp.route('/profile/delete-account', methods=['POST'])
@login_required
def delete_account():
    user_id = session['user_id']
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get all uploaded filenames to delete from disk
        cursor.execute('SELECT filename FROM uploaded_documents WHERE user_id = %s', (user_id,))
        docs = cursor.fetchall()

        # Get profile picture
        cursor.execute('SELECT profile_picture FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()

        # Delete user (cascades to documents + analyses)
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()

        # Delete files from disk
        upload_folder = current_app.config['UPLOAD_FOLDER']
        for doc in docs:
            path = os.path.join(upload_folder, doc['filename'])
            if os.path.exists(path):
                os.remove(path)

        if user and user.get('profile_picture'):
            pic_path = os.path.join(current_app.root_path, 'static', 'images', 'profiles', user['profile_picture'])
            if os.path.exists(pic_path):
                os.remove(pic_path)

        session.clear()
        flash('Your account has been deleted successfully.', 'info')
        return redirect(url_for('auth.register'))

    except Exception as e:
        flash(f'Account deletion failed: {str(e)}', 'danger')
        return redirect(url_for('profile.index'))
@login_required
def remove_picture():
    user_id = session['user_id']
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT profile_picture FROM users WHERE id=%s', (user_id,))
        row = cursor.fetchone()
        if row and row.get('profile_picture'):
            profile_dir = os.path.join(current_app.root_path, 'static', 'images', 'profiles')
            old_path    = os.path.join(profile_dir, row['profile_picture'])
            if os.path.exists(old_path):
                os.remove(old_path)
        cursor.execute('UPDATE users SET profile_picture=NULL WHERE id=%s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Profile picture removed.', 'info')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('profile.index'))
