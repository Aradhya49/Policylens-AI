import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from db import get_db_connection

upload_bp = Blueprint('upload', __name__)

CATEGORIES = [
    'Privacy Policy',
    'Terms & Conditions',
    'Employment Agreement',
    'NDA',
    'Service Agreement'
]


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    allowed = {'pdf', 'txt'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


@upload_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_document():
    if request.method == 'POST':
        title    = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        file     = request.files.get('document')

        # If "Other" was chosen, category field holds the custom text
        # (the JS swaps the name attribute so custom_category becomes category)
        if not category:
            flash('Please select or enter a document category.', 'danger')
            return render_template('dashboard/upload.html', categories=CATEGORIES)

        if not title:
            flash('Document title is required.', 'danger')
            return render_template('dashboard/upload.html', categories=CATEGORIES)

        if not file or file.filename == '':
            flash('Please select a file to upload.', 'danger')
            return render_template('dashboard/upload.html', categories=CATEGORIES)

        if not allowed_file(file.filename):
            flash('Only PDF and TXT files are allowed.', 'danger')
            return render_template('dashboard/upload.html', categories=CATEGORIES)

        # Check file size (max 16 MB)
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        if file_size > 16 * 1024 * 1024:
            flash('File size exceeds 16 MB limit.', 'danger')
            return render_template('dashboard/upload.html', categories=CATEGORIES)

        try:
            ext = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO uploaded_documents (user_id, title, filename, category, file_size)
                   VALUES (%s, %s, %s, %s, %s)''',
                (session['user_id'], title, unique_filename, category, file_size)
            )
            conn.commit()
            doc_id = cursor.lastrowid
            cursor.close()
            conn.close()

            flash('Document uploaded successfully! Running AI analysis...', 'success')
            return redirect(url_for('analysis.analyze', doc_id=doc_id))

        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'danger')
            return render_template('dashboard/upload.html', categories=CATEGORIES)

    return render_template('dashboard/upload.html', categories=CATEGORIES)


@upload_bp.route('/documents')
@login_required
def my_documents():
    user_id = session['user_id']
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            '''SELECT ud.*, COALESCE(aa.risk_level, 'Not Analyzed') AS risk_level, aa.id AS analysis_id
               FROM uploaded_documents ud
               LEFT JOIN ai_analyses aa ON ud.id = aa.document_id
               WHERE ud.user_id = %s
               ORDER BY ud.uploaded_at DESC''',
            (user_id,)
        )
        documents = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('dashboard/documents.html', documents=documents)
    except Exception as e:
        flash(f'Error loading documents: {str(e)}', 'danger')
        return render_template('dashboard/documents.html', documents=[])
