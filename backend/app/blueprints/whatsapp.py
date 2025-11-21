from flask import Blueprint, request, jsonify, session, redirect, url_for
from ..db import get_db
from datetime import datetime
from ..utils.whatsapp_sender import send_whatsapp_message_now

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
    """
    Encola y ENVÍA INMEDIATAMENTE el mensaje por WhatsApp
    """
    data = request.json or request.form
    client_id = data.get('client_id')
    message = data.get('message')
    template = data.get('template')
    attachment = data.get('attachment')
    scheduled = data.get('scheduled_at')
    
    if not message:
        return jsonify({'error':'message required'}), 400
    
    db = get_db()
    
    # Obtener teléfono del cliente
    cur = db.execute('SELECT phone, name FROM clients WHERE id=?', (client_id,))
    client = cur.fetchone()
    
    if not client:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    
    phone = client['phone']
    
    if not phone:
        # Guardar en cola con status='failed' si no hay teléfono
        db.execute('''
            INSERT INTO whatsapp_queue(client_id, message, template, attachment, scheduled_at, status, created_at) 
            VALUES (?, ?, ?, ?, ?, 'failed', datetime("now"))
        ''', (client_id, message, template, attachment, scheduled))
        db.commit()
        return jsonify({'error': 'Cliente sin teléfono registrado'}), 400
    
    # ENVIAR INMEDIATAMENTE
    success, result = send_whatsapp_message_now(phone, message)
    
    # Guardar en cola con el resultado
    if success:
        status = 'sent'
        db.execute('''
            INSERT INTO whatsapp_queue(client_id, message, template, attachment, scheduled_at, status, attempts, created_at) 
            VALUES (?, ?, ?, ?, ?, 'sent', 1, datetime("now"))
        ''', (client_id, message, template, attachment, scheduled))
        db.commit()
        
        return jsonify({
            'ok': True, 
            'message_id': result,
            'status': 'sent',
            'phone': phone,
            'client_name': client['name']
        }), 201
    else:
        # Error al enviar
        db.execute('''
            INSERT INTO whatsapp_queue(client_id, message, template, attachment, scheduled_at, status, attempts, created_at) 
            VALUES (?, ?, ?, ?, ?, 'failed', 1, datetime("now"))
        ''', (client_id, message, template, attachment, scheduled))
        db.commit()
        
        return jsonify({
            'ok': False,
            'error': result,
            'status': 'failed'
        }), 500


@bp.route('/send_bulk', methods=['POST'])
@login_required
def send_bulk():
    """
    Envía mensajes masivos INMEDIATAMENTE
    """
    data = request.json or request.form
    year = data.get('year', datetime.now().year)
    
    db = get_db()
    
    # Obtener clientes con pagos pendientes
    cur = db.execute('''
        SELECT DISTINCT c.id, c.name, c.phone, c.monthly_amount
        FROM clients c
        JOIN payments p ON p.client_id = c.id
        WHERE c.active = 1 
        AND p.status = 'pending'
        AND p.year = ?
        AND c.phone IS NOT NULL
        AND c.phone != ''
    ''', (year,))
    
    clients = cur.fetchall()
    
    sent_count = 0
    failed_count = 0
    results = []
    
    for client in clients:
        # Obtener primer pago pendiente
        cur = db.execute('''
            SELECT month, amount 
            FROM payments 
            WHERE client_id = ? AND status = 'pending' AND year = ?
            ORDER BY month
            LIMIT 1
        ''', (client['id'], year))
        
        payment = cur.fetchone()
        
        if not payment:
            continue
        
        # Construir mensaje
        month_names = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                      'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        
        message = f"""Hola {client['name']}, 👋

Este es un recordatorio de tu pago pendiente:
💰 Monto: ${payment['amount']}
📅 Mes: {month_names[payment['month'] - 1]}

Por favor, realiza tu pago a la brevedad.
¡Gracias por tu preferencia! 🙏"""
        
        # ENVIAR INMEDIATAMENTE
        success, result = send_whatsapp_message_now(client['phone'], message)
        
        # Registrar en base de datos
        status = 'sent' if success else 'failed'
        db.execute('''
            INSERT INTO whatsapp_queue(client_id, message, template, status, attempts, created_at) 
            VALUES (?, ?, 'recordatorio', ?, 1, datetime("now"))
        ''', (client['id'], message, status))
        
        if success:
            sent_count += 1
        else:
            failed_count += 1
        
        results.append({
            'client_id': client['id'],
            'client_name': client['name'],
            'phone': client['phone'],
            'success': success,
            'result': result
        })
    
    db.commit()
    
    return jsonify({
        'ok': True,
        'sent': sent_count,
        'failed': failed_count,
        'total': len(clients),
        'results': results
    }), 200


@bp.route('/queue', methods=['GET'])
@login_required
def list_queue():
    """
    Lista el historial de mensajes enviados
    """
    db = get_db()
    cur = db.execute('''
        SELECT 
            wq.*,
            c.name as client_name,
            c.phone as client_phone
        FROM whatsapp_queue wq
        LEFT JOIN clients c ON c.id = wq.client_id
        ORDER BY wq.created_at DESC 
        LIMIT 200
    ''')
    rows = [dict(x) for x in cur.fetchall()]
    return jsonify(rows)
