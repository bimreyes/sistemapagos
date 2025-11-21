from flask import Blueprint, render_template, session, redirect, url_for, current_app
from ..db import get_db
import os
import matplotlib
matplotlib.use('Agg')
bp = Blueprint('reports', __name__, url_prefix='/reports')
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
def client_report(client_id):
    db = get_db()
    cur = db.execute('SELECT * FROM clients WHERE id=?', (client_id,))
    client = cur.fetchone()
    cur = db.execute('SELECT year, month, status, COUNT(*) as cnt FROM payments WHERE client_id=? GROUP BY year, month, status ORDER BY year, month', (client_id,))
    rows = cur.fetchall()
    labels=[]; paid=[]; pending=[]; seen={}
    for r in rows:
        key = f"{r['year']}-{int(r['month']):02d}"
        if key not in seen: seen[key]={'paid':0,'pending':0}
        if r['status']=='paid': seen[key]['paid']+=r['cnt']
        else: seen[key]['pending']+=r['cnt']
    keys = sorted(seen.keys())
    labels = keys[-24:]
    paid = [seen[k]['paid'] for k in labels]
    pending = [seen[k]['pending'] for k in labels]
    img_name = f"client_{client_id}_summary.png"
    img_path = os.path.join(current_app.root_path, '..', current_app.static_folder, 'reports', img_name)
    try:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10,3))
        x = range(len(labels))
        plt.bar(x, paid, label='pagado')
        plt.bar(x, pending, bottom=paid, label='pendiente')
        plt.xticks(x, labels, rotation=45, ha='right', fontsize=8)
        plt.legend()
        plt.tight_layout()
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        plt.savefig(img_path)
        plt.close()
    except Exception:
        img_path=None
    return render_template('report_client.html', client=client, img=('/static/reports/'+img_name) if img_path else None)
@bp.route('/global')
@login_required
def global_report():
    db = get_db()
    cur = db.execute('SELECT year, SUM(CASE WHEN status=\'paid\' THEN amount ELSE 0 END) as total_paid, SUM(CASE WHEN status=\'pending\' THEN amount ELSE 0 END) as total_pending FROM payments GROUP BY year ORDER BY year')
    rows = cur.fetchall()
    years = [r['year'] for r in rows]
    img_name = 'global_summary.png'
    img_path = os.path.join(current_app.root_path, '..', current_app.static_folder, 'reports', img_name)
    try:
        import matplotlib.pyplot as plt
        paid = [r['total_paid'] for r in rows]
        pending = [r['total_pending'] for r in rows]
        plt.figure(figsize=(6,3))
        x = range(len(years))
        plt.plot(x, paid, marker='o', label='pagado')
        plt.plot(x, pending, marker='o', label='pendiente')
        plt.xticks(x, years)
        plt.legend()
        plt.tight_layout()
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        plt.savefig(img_path)
        plt.close()
    except Exception:
        img_path=None
    return render_template('report_global.html', img=('/static/reports/'+img_name) if img_path else None)
