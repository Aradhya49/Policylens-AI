import json
import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from db import get_db_connection

reports_bp = Blueprint('reports', __name__)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@reports_bp.route('/reports')
@login_required
def index():
    user_id    = session['user_id']
    search_q   = request.args.get('q', '').strip()
    risk_filter = request.args.get('risk', '').strip()

    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query  = '''SELECT aa.id AS analysis_id, aa.risk_level, aa.analyzed_at,
                           ud.id AS doc_id, ud.title, ud.category, ud.uploaded_at, ud.file_size
                    FROM uploaded_documents ud
                    LEFT JOIN ai_analyses aa ON ud.id = aa.document_id
                    WHERE ud.user_id = %s'''
        params = [user_id]

        if search_q:
            query  += ' AND (ud.title LIKE %s OR ud.category LIKE %s)'
            params += [f'%{search_q}%', f'%{search_q}%']

        if risk_filter:
            query  += ' AND aa.risk_level = %s'
            params.append(risk_filter)

        query += ' ORDER BY ud.uploaded_at DESC'
        cursor.execute(query, params)
        reports = cursor.fetchall()

        # Badge count — total docs
        cursor.execute('SELECT COUNT(*) AS total FROM uploaded_documents WHERE user_id = %s', (user_id,))
        doc_count = cursor.fetchone()['total']

        cursor.close()
        conn.close()

        return render_template('reports/index.html',
                               reports=reports,
                               search_q=search_q,
                               risk_filter=risk_filter,
                               doc_count=doc_count)
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'danger')
        return render_template('reports/index.html',
                               reports=[], search_q='',
                               risk_filter='', doc_count=0)


@reports_bp.route('/reports/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete_report(doc_id):
    user_id = session['user_id']
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT filename FROM uploaded_documents WHERE id = %s AND user_id = %s',
            (doc_id, user_id)
        )
        doc = cursor.fetchone()
        if not doc:
            flash('Document not found.', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('reports.index'))

        cursor.execute('DELETE FROM ai_analyses WHERE document_id = %s', (doc_id,))
        cursor.execute('DELETE FROM uploaded_documents WHERE id = %s AND user_id = %s', (doc_id, user_id))
        conn.commit()
        cursor.close()
        conn.close()

        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, doc['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)

        flash('Document deleted successfully.', 'success')
    except Exception as e:
        flash(f'Delete failed: {str(e)}', 'danger')

    return redirect(url_for('reports.index'))
