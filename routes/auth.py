from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import bcrypt
from db import get_db_connection

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Basic validation
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('auth/register.html')

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # Check if username or email already exists
            cursor.execute('SELECT id FROM users WHERE username = %s OR email = %s', (username, email))
            existing = cursor.fetchone()

            if existing:
                flash('Username or email already exists.', 'danger')
                cursor.close()
                conn.close()
                return render_template('auth/register.html')

            # Hash the password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Insert new user
            cursor.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)',
                (username, email, password_hash)
            )
            conn.commit()
            cursor.close()
            conn.close()

            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'danger')
            return render_template('auth/register.html')

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html')

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['email'] = user['email']
                flash(f"Welcome back, {user['username']}!", 'success')
                return redirect(url_for('dashboard.index'))
            else:
                flash('Invalid email or password.', 'danger')
                return render_template('auth/login.html')

        except Exception as e:
            flash(f'Login failed: {str(e)}', 'danger')
            return render_template('auth/login.html')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
