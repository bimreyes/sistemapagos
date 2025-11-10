from flask import Blueprint, render_template, request, redirect, url_for, session
from ..db import get_db
from datetime import datetime
bp = Blueprint('clients', __name__, url_prefix='/clients')
def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper
@bp.route('/')
@login_required
def index():
    q = request.args.get('q','').strip()
    db = get_db()
    if q:
        cur = db.execute("SELECT * FROM clients WHERE name LIKE ? OR phone LIKE ?", ('%'+q+'%','%'+q+'%'))
    else:
        cur = db.execute('SELECT * FROM clients ORDER BY name')
    rows = cur.fetchall()
    return render_template('clientes.html', clients=rows, q=q)
@bp.route('/add', methods=['GET','POST'])
@login_required
def add():
    if request.method=='POST':
        name = request.form['name']
        phone = request.form.get('phone')
        amount = float(request.form.get('monthly_amount') or 0)
        signup = request.form.get('signup_date') or datetime.now().strftime('%Y-%m-%d')
        db = get_db()
        cur = db.execute('INSERT INTO clients(name, phone, monthly_amount, signup_date) VALUES (?, ?, ?, ?)', (name, phone, amount, signup))
        db.commit()
        client_id = cur.lastrowid
        _generate_payments_for_client(db, client_id, signup, amount)
        return redirect(url_for('clients.index'))
    return render_template('detalle_cliente.html', client=None)
@bp.route('/edit/<int:client_id>', methods=['GET','POST'])
@login_required
def edit(client_id):
    db = get_db()
    if request.method=='POST':
        name = request.form['name']
        phone = request.form.get('phone')
        amount = float(request.form.get('monthly_amount') or 0)
        active = 1 if request.form.get('active')=='on' else 0
        db.execute('UPDATE clients SET name=?, phone=?, monthly_amount=?, active=? WHERE id=?', (name, phone, amount, active, client_id))
        db.commit()
        return redirect(url_for('clients.index'))
    cur = db.execute('SELECT * FROM clients WHERE id=?', (client_id,))
    client = cur.fetchone()
    return render_template('detalle_cliente.html', client=client)
@bp.route('/detail/<int:client_id>')
@login_required
def detail(client_id):
    db = get_db()
    cur = db.execute('SELECT * FROM clients WHERE id=?', (client_id,))
    client = cur.fetchone()
    cur = db.execute('SELECT * FROM payments WHERE client_id=? ORDER BY year, month', (client_id,))
    payments = cur.fetchall()
    cur = db.execute('SELECT * FROM uploads WHERE client_id=? ORDER BY uploaded_at DESC', (client_id,))
    uploads = cur.fetchall()
    return render_template('detalle_cliente.html', client=client, payments=payments, uploads=uploads)
def _generate_payments_for_client(db, client_id, signup_date, monthly_amount):
    from datetime import datetime
    sd = datetime.strptime(signup_date.split('T')[0], '%Y-%m-%d')
    today = datetime.now()
    year = sd.year
    month = sd.month
    while (year < today.year) or (year==today.year and month<=today.month):
        cur = db.execute('SELECT COUNT(*) FROM payments WHERE client_id=? AND year=? AND month=?', (client_id, year, month))
        if cur.fetchone()[0]==0:
            db.execute('INSERT INTO payments(client_id, year, month, amount, status) VALUES (?, ?, ?, ?, ?)', (client_id, year, month, monthly_amount, 'pending'))
        month += 1
        if month>12:
            month=1
            year+=1
    db.commit()
