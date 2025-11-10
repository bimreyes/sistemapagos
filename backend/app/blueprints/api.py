from flask import Blueprint, jsonify
from ..db import get_db
bp = Blueprint('api', __name__)
@bp.route('/clients', methods=['GET'])
def api_clients():
    db = get_db()
    cur = db.execute('SELECT id,name,phone,monthly_amount,signup_date,active FROM clients')
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)
@bp.route('/client/<int:client_id>/payments', methods=['GET'])
def api_client_payments(client_id):
    db = get_db()
    cur = db.execute('SELECT * FROM payments WHERE client_id=? ORDER BY year,month', (client_id,))
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)
