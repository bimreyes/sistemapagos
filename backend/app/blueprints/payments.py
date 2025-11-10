from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, send_file
from ..db import get_db
from datetime import datetime
import csv, io, os
from ..utils.pdf import invoice_pdf
from ..utils.excel import payments_to_xlsx
bp = Blueprint('payments', __name__, url_prefix='/payments')
def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper
@bp.route('/client/<int:client_id>')
@login_required
def client_payments(client_id):
    year = int(request.args.get('year', datetime.now().year))
    db = get_db()
    cur = db.execute('SELECT * FROM clients WHERE id=?', (client_id,))
    client = cur.fetchone()
    cur = db.execute('SELECT * FROM payments WHERE client_id=? AND year=? ORDER BY month', (client_id, year))
    payments = cur.fetchall()
    cur = db.execute("SELECT SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending_count, SUM(CASE WHEN status='pending' THEN amount ELSE 0 END) as total_debt, SUM(CASE WHEN status='paid' THEN amount ELSE 0 END) as total_paid FROM payments WHERE client_id=?", (client_id,))
    summary = cur.fetchone()
    return render_template('pagos.html', client=client, payments=payments, year=year, summary=summary)
@bp.route('/mark_paid/<int:payment_id>', methods=['POST'])
@login_required
def mark_paid(payment_id):
    db = get_db()
    db.execute('UPDATE payments SET status=?, paid_date=?, payment_type=? WHERE id=?', ('paid', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), request.form.get('payment_type','manual'), payment_id))
    db.commit()
    return ('',204)
@bp.route('/morosos')
@login_required
def morosos():
    db = get_db()
    cur = db.execute("SELECT c.*, SUM(CASE WHEN p.status='pending' THEN 1 ELSE 0 END) as pending_count, SUM(CASE WHEN p.status='pending' THEN p.amount ELSE 0 END) as total_debt FROM clients c JOIN payments p ON p.client_id=c.id GROUP BY c.id HAVING pending_count>0 ORDER BY total_debt DESC")
    rows = cur.fetchall()
    return render_template('morosos.html', rows=rows)
@bp.route('/export/<int:client_id>')
@login_required
def export_client_payments(client_id):
    db = get_db()
    cur = db.execute('SELECT * FROM payments WHERE client_id=? ORDER BY year, month', (client_id,))
    rows = cur.fetchall()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['id','year','month','amount','status','paid_date','payment_type'])
    for r in rows:
        cw.writerow([r['id'], r['year'], r['month'], r['amount'], r['status'], r['paid_date'], r['payment_type']])
    output = si.getvalue()
    return current_app.response_class(output, mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename=payments_client_{client_id}.csv'})
@bp.route('/excel/<int:client_id>')
@login_required
def excel(client_id):
    db = get_db()
    cur = db.execute('SELECT * FROM payments WHERE client_id=? ORDER BY year, month', (client_id,))
    rows = [dict(r) for r in cur.fetchall()]
    out_path = os.path.join(current_app.config['REPORT_FOLDER'], f'payments_{client_id}.xlsx')
    os.makedirs(current_app.config['REPORT_FOLDER'], exist_ok=True)
    payments_to_xlsx(rows, out_path)
    return send_file(out_path, as_attachment=True)
@bp.route('/invoice/<int:client_id>')
@login_required
def invoice(client_id):
    db = get_db()
    cur = db.execute('SELECT * FROM clients WHERE id=?', (client_id,))
    client = dict(cur.fetchone())
    cur = db.execute("SELECT * FROM payments WHERE client_id=? AND status='paid' ORDER BY year,month", (client_id,))
    payments = [dict(x) for x in cur.fetchall()]
    out_path = os.path.join(current_app.config['REPORT_FOLDER'], f'invoice_{client_id}.pdf')
    os.makedirs(current_app.config['REPORT_FOLDER'], exist_ok=True)
    invoice_pdf(client, payments, out_path)
    return send_file(out_path, as_attachment=True)
