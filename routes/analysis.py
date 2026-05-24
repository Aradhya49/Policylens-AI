import os
import json
import requests
from flask import Blueprint, render_template, redirect, url_for, session, flash, current_app, send_file, request
from db import get_db_connection
from config import Config

analysis_bp = Blueprint('analysis', __name__)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def extract_text_from_file(filepath):
    ext = filepath.rsplit('.', 1)[-1].lower()
    if ext == 'txt':
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    if ext == 'pdf':
        try:
            from pypdf import PdfReader
            reader = PdfReader(filepath)
            text = ''
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + '\n'
            if text.strip():
                return text
        except Exception:
            pass
        try:
            import PyPDF2
            text = ''
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + '\n'
            if text.strip():
                return text
        except Exception:
            pass
    return ''


def detect_clauses(text_lower):
    """Hybrid keyword detection for consistent clause finding."""
    detected = {}

    if any(w in text_lower for w in ['interest', 'penalty', 'late payment', 'overdue', 'per month', '% per']):
        detected['late_payment'] = True
    if any(w in text_lower for w in ['auto-renew', 'automatic renewal', 'automatically renew']):
        detected['auto_renewal'] = True
    if any(w in text_lower for w in ['terminate', 'termination', 'cancellation', 'cancel']):
        detected['termination'] = True
    if any(w in text_lower for w in ['intellectual property', 'ip rights', 'ownership of', 'copyright', 'source code']):
        detected['ip_ownership'] = True
    if any(w in text_lower for w in ['arbitration', 'dispute', 'jurisdiction', 'governing law', 'courts of']):
        detected['dispute'] = True
    if any(w in text_lower for w in ['confidential', 'non-disclosure', 'nda', 'proprietary information']):
        detected['confidentiality'] = True
    if any(w in text_lower for w in ['indemnif', 'hold harmless', 'liability cap', 'limited to', 'shall not exceed']):
        detected['liability'] = True
    if any(w in text_lower for w in ['force majeure', 'act of god', 'unforeseeable', 'beyond control']):
        detected['force_majeure'] = True
    if any(w in text_lower for w in ['non-compete', 'non compete', 'not compete', 'restraint of trade']):
        detected['non_compete'] = True
    if any(w in text_lower for w in ['warranty', 'warrants', 'guarantee', 'defect']):
        detected['warranty'] = True
    if any(w in text_lower for w in ['data', 'privacy', 'personal information', 'gdpr', 'data protection']):
        detected['data_privacy'] = True
    if any(w in text_lower for w in ['payment', 'invoice', 'fee', 'amount', 'rupees', 'usd', 'inr', '$', '₹']):
        detected['payment'] = True
    if any(w in text_lower for w in ['sla', 'service level', 'uptime', 'availability', 'response time']):
        detected['sla'] = True
    if any(w in text_lower for w in ['exclusiv', 'sole provider', 'sole supplier']):
        detected['exclusivity'] = True

    return detected


def calculate_risk_score(detected, risk_level, risk_highlights):
    """Calculate a numerical risk score 0-100."""
    score = 0

    # Base score from risk level
    base = {'Low': 20, 'Medium': 50, 'High': 75}.get(risk_level, 40)
    score += base

    # Add points for risky detected clauses
    risky = ['late_payment', 'auto_renewal', 'non_compete', 'liability', 'ip_ownership']
    score += sum(8 for k in risky if k in detected)

    # Subtract points for protective clauses
    protective = ['warranty', 'dispute', 'force_majeure']
    score -= sum(5 for k in protective if k in detected)

    # Add points for high severity risks
    high_count = sum(1 for r in risk_highlights if isinstance(r, dict) and r.get('severity') == 'high')
    score += high_count * 6

    return max(0, min(100, score))


def build_prompt(document_text, category):
    if not document_text.strip():
        document_text = f'Document category: {category}. No extractable text found — provide a general analysis for this document type.'

    text_lower = document_text.lower()
    detected   = detect_clauses(text_lower)

    # Build hint for AI
    hints = []
    clause_map = {
        'late_payment':   'Late payment penalty/interest clause',
        'auto_renewal':   'Auto-renewal clause',
        'termination':    'Termination/cancellation clause',
        'ip_ownership':   'Intellectual property/ownership clause — classify as medium or high, not low, as it affects long-term rights',
        'dispute':        'Dispute resolution/jurisdiction clause',
        'confidentiality':'Confidentiality/NDA clause',
        'liability':      'Liability cap/indemnity clause',
        'force_majeure':  'Force majeure clause — be specific about what events qualify and their practical impact on timelines',
        'non_compete':    'Non-compete clause',
        'warranty':       'Warranty/guarantee clause',
        'data_privacy':   'Data privacy clause',
        'payment':        'Payment terms clause',
        'sla':            'Service Level Agreement clause',
        'exclusivity':    'Exclusivity clause',
    }
    for key, label in clause_map.items():
        if key in detected:
            hints.append(f'- {label}')

    # Detect missing important clauses
    missing = []
    if 'data_privacy' not in detected and category in ['Privacy Policy', 'Service Agreement', 'Employment Agreement']:
        missing.append('Data privacy obligations — not found, may be missing')
    if 'warranty' not in detected and category in ['Service Agreement', 'Employment Agreement']:
        missing.append('Warranty or quality guarantee — not found, may be missing')
    if 'sla' not in detected and category in ['Service Agreement']:
        missing.append('Service Level Agreement (SLA) — not found, may be missing')
    if 'dispute' not in detected:
        missing.append('Dispute resolution mechanism — not clearly specified')

    hint_text = ''
    if hints:
        hint_text += f'\n\nPre-detected clauses (verify and explain accurately):\n' + '\n'.join(hints)
    if missing:
        hint_text += f'\n\nPotentially missing clauses (flag if absent):\n' + '\n'.join(f'- {m}' for m in missing)

    return f"""You are a senior legal document analyst. Analyze this {category} document with precision.
Respond ONLY with valid JSON — absolutely no markdown, no code fences, no extra text outside the JSON.

Document:
\"\"\"
{document_text[:8000]}
\"\"\"{hint_text}

STRICT RULES:
1. Be legally accurate. Do not invent clauses not in the document.
2. Do not speculate or exaggerate. Stick to what the contract actually says.
3. Do not repeat similar risks. Each risk must be distinct.
4. Use clear, professional language — not overly casual, not overly technical.
5. Severity for IP ownership/retention by one party = at least "medium" (creates vendor lock-in risk).
6. Force majeure explanations must be specific: name the qualifying events and their practical impact.
7. Overall recommendation must be balanced — acknowledge both strengths and concerns.
8. Questions to ask must be practical and directly relevant to THIS document's specific clauses.

Return EXACTLY this JSON:
{{
  "summary": "Professional 4-6 sentence summary: parties involved, document purpose, key obligations of each party, payment terms, duration/timeline, and overall nature.",

  "simplified_explanation": "Plain English explanation for a non-lawyer in 5-7 sentences. Cover: what each party must do, what they receive, consequences of breach, any restrictions, and overall fairness.",

  "risk_level": "Low",

  "risk_score": {{
    "overall": 45,
    "financial": "Medium",
    "legal": "Low",
    "operational": "Medium"
  }},

  "overall_recommendation": "2-3 sentence professional recommendation about whether this agreement is balanced, what the main concerns are, and what to do before signing.",

  "risk_highlights": [
    {{"text": "Distinct specific risk with practical consequence for the signing party", "severity": "high"}},
    {{"text": "Another distinct risk — financial or legal consequence explained", "severity": "medium"}},
    {{"text": "Another distinct risk — why this matters in practice", "severity": "medium"}},
    {{"text": "IP, liability cap, or termination risk if present", "severity": "medium"}},
    {{"text": "Unusual clause or notable concern", "severity": "low"}}
  ],

  "missing_clauses": [
    "Important clause type not found in this document — explain why it matters",
    "Another missing clause — explain the risk of its absence"
  ],

  "protective_clauses": [
    "Clause that protects the signing party — explain how and why it benefits them",
    "Another protection with its practical benefit",
    "Another protection with its practical benefit"
  ],

  "key_clauses": [
    {{"clause": "Actual clause name from document", "description": "Clear explanation of what it means and why it matters", "severity": "high"}},
    {{"clause": "Actual clause name from document", "description": "Clear explanation of what it means and why it matters", "severity": "medium"}},
    {{"clause": "Actual clause name from document", "description": "Clear explanation of what it means and why it matters", "severity": "medium"}},
    {{"clause": "Actual clause name from document", "description": "Clear explanation of what it means and why it matters", "severity": "low"}},
    {{"clause": "Actual clause name from document", "description": "Clear explanation of what it means and why it matters", "severity": "low"}}
  ],

  "before_you_sign": [
    "Most critical thing to verify or negotiate before signing",
    "Second important caution or action item",
    "Third important caution or action item",
    "Fourth important caution or action item"
  ],

  "questions_to_ask": [
    "Practical question directly relevant to a specific clause in this document",
    "Another practical question the signing party should raise",
    "Another practical question",
    "Another practical question"
  ]
}}

Rules for risk_score.overall: integer 0-100. 0-30=Low, 31-60=Medium, 61-100=High.
Rules for risk_score.financial/legal/operational: exactly one of "Low", "Medium", "High".
Rules for risk_level: exactly one of "Low", "Medium", "High".
Rules for severity: exactly one of "high", "medium", "low".
missing_clauses: only list if genuinely absent from the document. Empty array [] if nothing is missing."""


def parse_ai_response(raw):
    raw = raw.strip()
    if '```' in raw:
        parts = raw.split('```')
        for part in parts:
            part = part.strip()
            if part.startswith('json'):
                part = part[4:].strip()
            if part.startswith('{'):
                raw = part
                break
    start = raw.find('{')
    end   = raw.rfind('}')
    if start != -1 and end != -1:
        raw = raw[start:end+1]

    result = json.loads(raw)

    if result.get('risk_level') not in ['Low', 'Medium', 'High']:
        result['risk_level'] = 'Medium'

    # Normalize risk_highlights
    rh = result.get('risk_highlights', [])
    normalized_rh = []
    for item in rh:
        if isinstance(item, dict):
            normalized_rh.append({'text': item.get('text', ''), 'severity': item.get('severity', 'medium')})
        elif isinstance(item, str):
            normalized_rh.append({'text': item, 'severity': 'medium'})
    result['risk_highlights'] = normalized_rh

    # Normalize key_clauses
    kc = result.get('key_clauses', [])
    normalized_kc = []
    for item in kc:
        if isinstance(item, dict):
            normalized_kc.append({
                'clause':      item.get('clause', ''),
                'description': item.get('description', ''),
                'severity':    item.get('severity', 'medium')
            })
    result['key_clauses'] = normalized_kc

    # Normalize risk_score
    rs = result.get('risk_score', {})
    if not isinstance(rs, dict):
        rs = {}
    result['risk_score'] = {
        'overall':     rs.get('overall', 40),
        'financial':   rs.get('financial', 'Medium'),
        'legal':       rs.get('legal', 'Low'),
        'operational': rs.get('operational', 'Medium'),
    }

    # Default all list fields
    for field in ['protective_clauses', 'before_you_sign', 'questions_to_ask', 'missing_clauses']:
        if not isinstance(result.get(field), list):
            result[field] = []

    if not result.get('overall_recommendation'):
        result['overall_recommendation'] = ''

    return result


def analyze_with_groq(document_text, category):
    url     = 'https://api.groq.com/openai/v1/chat/completions'
    headers = {'Authorization': f'Bearer {Config.GROQ_API_KEY}', 'Content-Type': 'application/json'}
    payload = {
        'model': 'llama-3.3-70b-versatile', 'temperature': 0.2, 'max_tokens': 2500,
        'messages': [
            {'role': 'system', 'content': 'You are a legal document analysis assistant. Always respond with valid JSON only.'},
            {'role': 'user',   'content': build_prompt(document_text, category)}
        ]
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code != 200:
        raise Exception(f'Groq error {response.status_code}: {response.text[:300]}')
    return parse_ai_response(response.json()['choices'][0]['message']['content'])


def analyze_with_openrouter(document_text, category):
    url     = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {Config.OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'http://localhost:5001',
        'X-Title': 'PolicyLens AI'
    }
    payload = {
        'model': 'mistralai/mistral-7b-instruct:free', 'temperature': 0.2, 'max_tokens': 1500,
        'messages': [
            {'role': 'system', 'content': 'You are a legal document analysis assistant. Always respond with valid JSON only.'},
            {'role': 'user',   'content': build_prompt(document_text, category)}
        ]
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code != 200:
        raise Exception(f'OpenRouter error {response.status_code}: {response.text[:300]}')
    return parse_ai_response(response.json()['choices'][0]['message']['content'])


def analyze_document(document_text, category):
    errors = []
    try:
        result = analyze_with_groq(document_text, category)
        result['_provider'] = 'Groq'
        return result
    except Exception as e:
        errors.append(f'Groq: {str(e)}')
    try:
        result = analyze_with_openrouter(document_text, category)
        result['_provider'] = 'OpenRouter'
        return result
    except Exception as e:
        errors.append(f'OpenRouter: {str(e)}')
    raise Exception(' | '.join(errors))


def count_words(text):
    return len(text.split()) if text.strip() else 0


# ── ROUTES ────────────────────────────────────────────────

@analysis_bp.route('/analyze/<int:doc_id>')
@login_required
def analyze(doc_id):
    user_id  = session['user_id']
    reanalyze = request.args.get('reanalyze', '0') == '1'

    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute('SELECT * FROM uploaded_documents WHERE id = %s AND user_id = %s', (doc_id, user_id))
        document = cursor.fetchone()
        if not document:
            flash('Document not found.', 'danger')
            cursor.close(); conn.close()
            return redirect(url_for('dashboard.index'))

        # Check existing analysis
        cursor.execute('SELECT * FROM ai_analyses WHERE document_id = %s AND user_id = %s', (doc_id, user_id))
        existing = cursor.fetchone()

        # If exists and not re-analyzing, return existing
        if existing and not reanalyze:
            try:
                kc_data = json.loads(existing['key_clauses'] or '{}')
                if isinstance(kc_data, dict):
                    existing['key_clauses']            = kc_data.get('clauses', [])
                    existing['protective_clauses']     = kc_data.get('protective_clauses', [])
                    existing['before_you_sign']        = kc_data.get('before_you_sign', [])
                    existing['questions_to_ask']       = kc_data.get('questions_to_ask', [])
                    existing['missing_clauses']        = kc_data.get('missing_clauses', [])
                    existing['overall_recommendation'] = kc_data.get('overall_recommendation', '')
                    existing['risk_score']             = kc_data.get('risk_score', {})
                else:
                    existing['key_clauses']            = kc_data
                    existing['protective_clauses']     = []
                    existing['before_you_sign']        = []
                    existing['questions_to_ask']       = []
                    existing['missing_clauses']        = []
                    existing['overall_recommendation'] = ''
                    existing['risk_score']             = {}

                rh_raw     = json.loads(existing['risk_highlights'] or '[]')
                normalized = []
                for item in rh_raw:
                    if isinstance(item, dict):
                        normalized.append(item)
                    elif isinstance(item, str):
                        normalized.append({'text': item, 'severity': 'medium'})
                existing['risk_highlights'] = normalized
            except Exception:
                existing['key_clauses']            = []
                existing['risk_highlights']        = []
                existing['protective_clauses']     = []
                existing['before_you_sign']        = []
                existing['questions_to_ask']       = []
                existing['missing_clauses']        = []
                existing['overall_recommendation'] = ''
                existing['risk_score']             = {}
            cursor.close(); conn.close()

            upload_folder = current_app.config['UPLOAD_FOLDER']
            file_path     = os.path.join(upload_folder, document['filename'])
            doc_text      = extract_text_from_file(file_path)
            word_count    = count_words(doc_text)

            return render_template('analysis/result.html',
                                   document=document,
                                   analysis=existing,
                                   word_count=word_count,
                                   has_existing=True)

        # If re-analyzing, delete old analysis
        if existing and reanalyze:
            cursor.execute('DELETE FROM ai_analyses WHERE document_id = %s AND user_id = %s', (doc_id, user_id))
            conn.commit()

        cursor.close(); conn.close()

        # Extract text
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path     = os.path.join(upload_folder, document['filename'])
        document_text = extract_text_from_file(file_path)
        word_count    = count_words(document_text)

        if not document_text.strip():
            flash('⚠ Could not extract text. AI will analyze based on document category.', 'warning')

        result   = analyze_document(document_text, document['category'])
        provider = result.pop('_provider', 'AI')

        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO ai_analyses
               (document_id, user_id, summary, simplified_explanation, risk_level, key_clauses, risk_highlights)
               VALUES (%s, %s, %s, %s, %s, %s, %s)''',
            (doc_id, user_id,
             result['summary'],
             result['simplified_explanation'],
             result['risk_level'],
             json.dumps({
                 'clauses':               result['key_clauses'],
                 'protective_clauses':    result.get('protective_clauses', []),
                 'before_you_sign':       result.get('before_you_sign', []),
                 'questions_to_ask':      result.get('questions_to_ask', []),
                 'missing_clauses':       result.get('missing_clauses', []),
                 'overall_recommendation':result.get('overall_recommendation', ''),
                 'risk_score':            result.get('risk_score', {}),
             }),
             json.dumps(result['risk_highlights']))
        )
        conn.commit()
        analysis_id = cursor.lastrowid
        cursor.close(); conn.close()

        analysis = {
            'id':                     analysis_id,
            'summary':                result['summary'],
            'simplified_explanation': result['simplified_explanation'],
            'risk_level':             result['risk_level'],
            'risk_score':             result.get('risk_score', {}),
            'overall_recommendation': result.get('overall_recommendation', ''),
            'key_clauses':            result['key_clauses'],
            'protective_clauses':     result.get('protective_clauses', []),
            'before_you_sign':        result.get('before_you_sign', []),
            'questions_to_ask':       result.get('questions_to_ask', []),
            'missing_clauses':        result.get('missing_clauses', []),
            'risk_highlights':        result['risk_highlights'],
        }

        msg = 'Re-analysis completed!' if reanalyze else f'Analysis completed using {provider}!'
        flash(msg, 'success')
        return render_template('analysis/result.html',
                               document=document,
                               analysis=analysis,
                               word_count=word_count,
                               has_existing=False)

    except json.JSONDecodeError:
        flash('AI returned unexpected response. Please try again.', 'danger')
        return redirect(url_for('upload.my_documents'))
    except Exception as e:
        flash(f'Analysis failed: {str(e)}', 'danger')
        return redirect(url_for('upload.my_documents'))


@analysis_bp.route('/analysis')
@login_required
def analysis_list():
    user_id = session['user_id']
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            '''SELECT aa.*, ud.title, ud.category
               FROM ai_analyses aa
               JOIN uploaded_documents ud ON aa.document_id = ud.id
               WHERE aa.user_id = %s ORDER BY aa.analyzed_at DESC''',
            (user_id,)
        )
        analyses = cursor.fetchall()
        cursor.close(); conn.close()
        return render_template('analysis/list.html', analyses=analyses)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('analysis/list.html', analyses=[])


@analysis_bp.route('/analysis/download/<int:doc_id>')
@login_required
def download_pdf(doc_id):
    user_id = session['user_id']
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM uploaded_documents WHERE id = %s AND user_id = %s', (doc_id, user_id))
        document = cursor.fetchone()
        cursor.execute('SELECT * FROM ai_analyses WHERE document_id = %s AND user_id = %s', (doc_id, user_id))
        analysis = cursor.fetchone()
        cursor.close(); conn.close()

        if not document or not analysis:
            flash('Document or analysis not found.', 'danger')
            return redirect(url_for('reports.index'))

        key_clauses     = json.loads(analysis['key_clauses']     or '[]')
        risk_highlights = json.loads(analysis['risk_highlights'] or '[]')

        # Generate PDF with reportlab
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
        import io

        buffer = io.BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                   topMargin=1.5*cm, bottomMargin=2*cm,
                                   leftMargin=2*cm, rightMargin=2*cm)

        styles  = getSampleStyleSheet()
        primary = colors.HexColor('#4361ee')
        danger  = colors.HexColor('#e63946')
        warning = colors.HexColor('#f4a261')
        success = colors.HexColor('#2dc653')
        dark    = colors.HexColor('#1e293b')
        muted   = colors.HexColor('#64748b')
        white   = colors.HexColor('#ffffff')
        light   = colors.HexColor('#f8fafc')

        risk_color = {'Low': success, 'Medium': warning, 'High': danger}.get(analysis['risk_level'], muted)
        risk_bg    = {
            'Low':    colors.HexColor('#f0fff4'),
            'Medium': colors.HexColor('#fffbeb'),
            'High':   colors.HexColor('#fff1f2')
        }.get(analysis['risk_level'], light)

        heading_style = ParagraphStyle('H', parent=styles['Normal'],
                                       fontSize=13, textColor=dark,
                                       fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6)
        body_style = ParagraphStyle('Body', parent=styles['Normal'],
                                    fontSize=10, textColor=dark,
                                    leading=15, spaceAfter=8)
        body_muted = ParagraphStyle('BodyMuted', parent=styles['Normal'],
                                    fontSize=10, textColor=muted,
                                    leading=15, spaceAfter=4)
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'],
                                      fontSize=8, textColor=muted, alignment=TA_CENTER)

        story = []

        # ── HEADER BLOCK (colored table) ──────────────────
        header_brand = ParagraphStyle('Brand', parent=styles['Normal'],
                                      fontSize=24, textColor=white,
                                      fontName='Helvetica-Bold', spaceAfter=2)
        header_sub   = ParagraphStyle('BrandSub', parent=styles['Normal'],
                                      fontSize=11, textColor=colors.HexColor('#c7d2fe'),
                                      spaceAfter=0)

        header_data = [[
            Paragraph('PolicyLens AI', header_brand),
            ''
        ], [
            Paragraph('AI-Powered Legal Document Analysis Report', header_sub),
            ''
        ]]
        header_table = Table(header_data, colWidths=['100%', 0])
        header_table.setStyle(TableStyle([
            ('BACKGROUND',  (0,0), (-1,-1), primary),
            ('TOPPADDING',  (0,0), (-1,-1), 18),
            ('BOTTOMPADDING',(0,0),(-1,-1), 18),
            ('LEFTPADDING', (0,0), (-1,-1), 20),
            ('RIGHTPADDING',(0,0), (-1,-1), 20),
            ('ROWBACKGROUNDS',(0,0),(-1,-1),[primary, primary]),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 16))

        # ── DOCUMENT INFO BLOCK ───────────────────────────
        info_title = ParagraphStyle('InfoTitle', parent=styles['Normal'],
                                    fontSize=11, textColor=muted,
                                    fontName='Helvetica-Bold', spaceAfter=2)
        info_value = ParagraphStyle('InfoValue', parent=styles['Normal'],
                                    fontSize=13, textColor=dark,
                                    fontName='Helvetica-Bold', spaceAfter=0)

        info_data = [
            [Paragraph('DOCUMENT', info_title), Paragraph('CATEGORY', info_title), Paragraph('ANALYZED ON', info_title)],
            [Paragraph(document["title"], info_value),
             Paragraph(document["category"], info_value),
             Paragraph(analysis["analyzed_at"].strftime("%B %d, %Y"), info_value)],
        ]
        info_table = Table(info_data, colWidths=['40%', '35%', '25%'])
        info_table.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,-1), light),
            ('TOPPADDING',   (0,0), (-1,-1), 10),
            ('BOTTOMPADDING',(0,0), (-1,-1), 10),
            ('LEFTPADDING',  (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
            ('ROUNDEDCORNERS', [6]),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
            ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor('#e2e8f0')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 12))

        # ── RISK LEVEL BANNER ─────────────────────────────
        risk_label = ParagraphStyle('RiskLabel', parent=styles['Normal'],
                                    fontSize=10, textColor=muted,
                                    fontName='Helvetica-Bold', spaceAfter=2)
        risk_value = ParagraphStyle('RiskValue', parent=styles['Normal'],
                                    fontSize=16, textColor=risk_color,
                                    fontName='Helvetica-Bold', spaceAfter=0)

        risk_data = [[
            Paragraph('RISK LEVEL', risk_label),
        ],[
            Paragraph(f'● {analysis["risk_level"]}', risk_value),
        ]]
        risk_table = Table(risk_data, colWidths=['100%'])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,-1), risk_bg),
            ('TOPPADDING',   (0,0), (-1,-1), 10),
            ('BOTTOMPADDING',(0,0), (-1,-1), 10),
            ('LEFTPADDING',  (0,0), (-1,-1), 14),
            ('RIGHTPADDING', (0,0), (-1,-1), 14),
            ('BOX', (0,0), (-1,-1), 2, risk_color),
        ]))
        story.append(risk_table)
        story.append(Spacer(1, 14))

        # Summary
        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=8))
        story.append(Paragraph('Summary', heading_style))
        story.append(Paragraph(analysis['summary'], body_style))

        # Risk Highlights
        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=8))
        story.append(Paragraph('Risk Highlights', heading_style))
        for rh in risk_highlights:
            story.append(Paragraph(f'• {rh}', body_style))

        # Key Clauses
        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=8))
        story.append(Paragraph('Key Clauses', heading_style))
        for kc in key_clauses:
            story.append(Paragraph(f'<b>{kc.get("clause","")}</b>', body_style))
            story.append(Paragraph(kc.get('description', ''), body_style))
            story.append(Spacer(1, 4))

        # Simple Breakdown
        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=8))
        story.append(Paragraph('Simple Breakdown', heading_style))
        story.append(Paragraph(analysis['simplified_explanation'], body_style))

        # Footer
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=6))
        story.append(Paragraph('Generated by PolicyLens AI — AI-Powered Legal Document Simplifier', footer_style))

        doc.build(story)
        buffer.seek(0)

        safe_title = document['title'].replace(' ', '_').replace('/', '-')
        return send_file(buffer, as_attachment=True,
                         download_name=f'PolicyLens_{safe_title}_Analysis.pdf',
                         mimetype='application/pdf')

    except ImportError:
        flash('reportlab not installed. Run: pip install reportlab', 'danger')
        return redirect(url_for('analysis.analyze', doc_id=doc_id))
    except Exception as e:
        flash(f'PDF generation failed: {str(e)}', 'danger')
        return redirect(url_for('analysis.analyze', doc_id=doc_id))
