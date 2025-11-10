from flask import Blueprint, request, jsonify, session, redirect, url_for
from ..db import get_db
from datetime import datetime
bp = Blueprint('whatsapp', __name__, url_prefix='/whatsapp')
def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper
@bp.route('/enqueue', methods=['POST'])
@login_required
def enqueue():
    data = request.json or request.form
    client_id = data.get('client_id')
    message = data.get('message')
    template = data.get('template')
    attachment = data.get('attachment')
    scheduled = data.get('scheduled_at')  # optional
    if not message:
        return jsonify({'error':'message required'}), 400
    db = get_db()
    db.execute('INSERT INTO whatsapp_queue(client_id, message, template, attachment, scheduled_at, created_at) VALUES (?, ?, ?, ?, ?, datetime("now"))', (client_id, message, template, attachment, scheduled))
    db.commit()
    return jsonify({'ok':True}), 201
@bp.route('/queue', methods=['GET'])
@login_required
def list_queue():
    db = get_db()
    cur = db.execute('SELECT * FROM whatsapp_queue ORDER BY created_at DESC LIMIT 200')
    rows = [dict(x) for x in cur.fetchall()]
    return jsonify(rows)
