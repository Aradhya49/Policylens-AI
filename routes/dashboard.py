from flask import Blueprint, render_template, session, redirect, url_for
from db import get_db_connection

dashboard_bp = Blueprint('dashboard', __name__)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    user_id = session['user_id']

    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute('SELECT COUNT(*) AS total FROM uploaded_documents WHERE user_id = %s', (user_id,))
        total_docs = cursor.fetchone()['total']

        cursor.execute('SELECT COUNT(*) AS total FROM ai_analyses WHERE user_id = %s', (user_id,))
        total_analyses = cursor.fetchone()['total']

        cursor.execute(
            'SELECT COUNT(*) AS total FROM ai_analyses WHERE user_id = %s AND risk_level = %s',
            (user_id, 'High')
        )
        high_risk = cursor.fetchone()['total']

        cursor.execute(
            '''SELECT ud.id, ud.title, ud.category, ud.uploaded_at,
                      COALESCE(aa.risk_level, 'Not Analyzed') AS risk_level
               FROM uploaded_documents ud
               LEFT JOIN ai_analyses aa ON ud.id = aa.document_id
               WHERE ud.user_id = %s
               ORDER BY ud.uploaded_at DESC LIMIT 5''',
            (user_id,)
        )
        recent_uploads = cursor.fetchall()

        cursor.execute(
            '''SELECT category, COUNT(*) AS count
               FROM uploaded_documents WHERE user_id = %s
               GROUP BY category''',
            (user_id,)
        )
        category_data = cursor.fetchall()

        # Activity timeline — last 8 actions (uploads + analyses)
        cursor.execute(
            '''SELECT 'Uploaded' AS action, title, uploaded_at AS action_time, category
               FROM uploaded_documents WHERE user_id = %s
               UNION ALL
               SELECT 'Analyzed' AS action, ud.title, aa.analyzed_at AS action_time, ud.category
               FROM ai_analyses aa
               JOIN uploaded_documents ud ON aa.document_id = ud.id
               WHERE aa.user_id = %s
               ORDER BY action_time DESC LIMIT 8''',
            (user_id, user_id)
        )
        activities = cursor.fetchall()

        cursor.close()
        conn.close()

        chart_labels = [row['category'] for row in category_data]
        chart_values = [row['count']    for row in category_data]

        return render_template(
            'dashboard/index.html',
            total_docs=total_docs,
            total_analyses=total_analyses,
            high_risk=high_risk,
            recent_uploads=recent_uploads,
            chart_labels=chart_labels,
            chart_values=chart_values,
            activities=activities
        )

    except Exception as e:
        return render_template('dashboard/index.html',
                               total_docs=0, total_analyses=0,
                               high_risk=0, recent_uploads=[],
                               chart_labels=[], chart_values=[],
                               activities=[], error=str(e))
