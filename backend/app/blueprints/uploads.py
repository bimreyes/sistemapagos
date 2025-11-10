from flask import Blueprint, request, redirect, url_for, session, current_app, send_from_directory, flash
from ..db import get_db
import os
from werkzeug.utils import secure_filename
from datetime import datetime
bp = Blueprint('uploads', __name__, url_prefix='/uploads')
ALLOWED_EXT = set(['png','jpg','jpeg','pdf','gif'])
def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper
@bp.route('/upload/<int:client_id>', methods=['POST'])
@login_required
def upload(client_id):
    if 'file' not in request.files:
        flash('No file')
        return redirect(url_for('clients.detail', client_id=client_id))
    f = request.files['file']
    if f.filename=='':
        flash('No filename')
        return redirect(url_for('clients.detail', client_id=client_id))
    filename = secure_filename(f.filename)
    client_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(client_id))
    os.makedirs(client_folder, exist_ok=True)
    path = os.path.join(client_folder, filename)
    f.save(path)
    thumb_path = None
    try:
        from PIL import Image
        ext = filename.rsplit('.',1)[1].lower()
        if ext in ('png','jpg','jpeg'):
            img = Image.open(path)
            img.thumbnail((200,200))
            thumb_folder = os.path.join(current_app.static_folder, 'uploads_thumbs')
            os.makedirs(thumb_folder, exist_ok=True)
            thumb_name = f"{client_id}_{filename}"
            thumb_full = os.path.join(thumb_folder, thumb_name)
            img.save(thumb_full)
            thumb_path = '/static/uploads_thumbs/' + thumb_name
    except Exception:
        thumb_path = None
    db = get_db()
    db.execute('INSERT INTO uploads(client_id, filename, stored_path, uploaded_at, thumb_path) VALUES (?, ?, ?, ?, ?)', (client_id, filename, path, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), thumb_path))
    db.commit()
    return redirect(url_for('clients.detail', client_id=client_id))
@bp.route('/download/<int:client_id>/<path:filename>')
@login_required
def download(client_id, filename):
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(client_id))
    return send_from_directory(folder, filename, as_attachment=True)
