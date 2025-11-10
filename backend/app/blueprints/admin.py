from flask import Blueprint, render_template, session, redirect, url_for, request, send_file, flash
from ..db import get_db
from werkzeug.security import generate_password_hash
import os
bp = Blueprint('admin', __name__, url_prefix='/admin')
def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper
@bp.route('/panel')
@login_required
def panel():
    db = get_db()
    cur = db.execute('SELECT COUNT(*) as c FROM clients')
    clients = cur.fetchone()['c']
    cur = db.execute("SELECT COUNT(*) as c FROM payments WHERE status='pending'")
    pending = cur.fetchone()['c']
    return render_template('panel.html', clients=clients, pending=pending)
@bp.route('/usuarios', methods=['GET','POST'])
@login_required
def usuarios():
    db = get_db()
    if request.method=='POST':
        db.execute('INSERT INTO admins(username,password,created_at) VALUES (?, ?, datetime("now"))', (request.form['username'], generate_password_hash(request.form['password'])))
        db.commit()
    cur = db.execute('SELECT id, username, created_at FROM admins')
    users = cur.fetchall()
    return render_template('usuarios.html', users=users)
@bp.route('/backup')
@login_required
def backup():
    dbfile = os.path.join(os.getcwd(), 'sistemapagos.db')
    if not os.path.exists(dbfile):
        flash('DB no encontrada')
        return redirect(url_for('admin.panel'))
    return send_file(dbfile, as_attachment=True)
@bp.route('/restore', methods=['POST'])
@login_required
def restore():
    if 'file' not in request.files:
        flash('No file')
        return redirect(url_for('admin.panel'))
    f = request.files['file']
    path = os.path.join(os.getcwd(), 'restore_upload.db')
    f.save(path)
    os.replace(path, os.path.join(os.getcwd(), 'sistemapagos.db'))
    flash('Base restaurada. Reinicie la app.')
    return redirect(url_for('admin.panel'))
@bp.route('/historial')
@login_required
def historial():
    db = get_db()
    cur = db.execute('SELECT * FROM historial_cambios ORDER BY fecha_hora DESC LIMIT 1000')
    rows = cur.fetchall()
    return render_template('historial.html', rows=rows)
