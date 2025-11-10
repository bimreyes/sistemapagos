from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..db import get_db
from werkzeug.security import check_password_hash
bp = Blueprint('auth', __name__, url_prefix='/auth')
@bp.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cur = db.execute('SELECT * FROM admins WHERE username=?', (username,))
        row = cur.fetchone()
        if row and check_password_hash(row['password'], password):
            session['admin'] = row['username']
            return redirect(url_for('admin.panel'))
        flash('Usuario o contraseña incorrectos')
    return render_template('login.html')
@bp.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('auth.login'))
