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
# Agregar estas rutas al archivo existente
@bp.route('/payment-plans', methods=['GET'])
def api_payment_plans():
    from ..blueprints.payment_plans import get_all_plans
    return get_all_plans()

@bp.route('/payment-plans/<int:client_id>', methods=['GET'])
def api_client_plan(client_id):
    from ..blueprints.payment_plans import get_client_plan
    return get_client_plan(client_id)