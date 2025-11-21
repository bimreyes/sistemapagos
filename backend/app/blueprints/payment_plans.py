from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from ..db import get_db
from datetime import datetime

# Corregido: agregado __name__ como segundo parámetro
bp = Blueprint('payment_plans', __name__)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper

@bp.route('/payment-plans/panel')
@login_required
def panel():
    """Muestra el panel de planes de pago"""
    print("📄 Accediendo a /payment-plans/panel")
    db = get_db()
    cur = db.execute('SELECT * FROM clients WHERE active=1 ORDER BY name')
    clients = cur.fetchall()
    return render_template('payment_plans.html', clients=clients)

@bp.route('/api/payment-plans', methods=['GET'])
@login_required
def get_all_plans():
    """Obtener resumen de todos los planes de pago"""
    print("\n🔍 GET /api/payment-plans")
    
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    print(f"   month={month}, year={year}")
    
    if not month or not year:
        return jsonify({'error': 'Se requieren month y year'}), 400
    
    db = get_db()
    
    # Obtener todos los clientes activos
    cur = db.execute('SELECT id FROM clients WHERE active=1')
    clients = cur.fetchall()
    
    plans = {}
    
    for client in clients:
        client_id = client['id']
        
        # Obtener configuración del plan
        cur = db.execute('''
            SELECT payments_count, monthly_amount 
            FROM payment_plan_config 
            WHERE client_id=? AND month=? AND year=?
        ''', (client_id, month, year))
        
        config = cur.fetchone()
        
        if not config:
            # Usar valores por defecto
            cur = db.execute('SELECT monthly_amount FROM clients WHERE id=?', (client_id,))
            client_data = cur.fetchone()
            payments_count = 1
            monthly_amount = client_data['monthly_amount'] if client_data else 0
        else:
            payments_count = config['payments_count']
            monthly_amount = config['monthly_amount']
        
        # Obtener pagos realizados
        cur = db.execute('''
            SELECT COUNT(*) as paid_count, SUM(amount) as total_paid
            FROM payment_plan_payments
            WHERE client_id=? AND month=? AND year=? AND paid=1
        ''', (client_id, month, year))
        
        paid_data = cur.fetchone()
        paid_count = paid_data['paid_count'] or 0
        total_paid = paid_data['total_paid'] or 0
        
        plans[client_id] = {
            'payments_count': payments_count,
            'monthly_amount': monthly_amount,
            'paid_count': paid_count,
            'total_paid': total_paid,
            'total_pending': monthly_amount - total_paid
        }
    
    print(f"   ✅ Retornando planes de {len(plans)} clientes")
    return jsonify(plans)

@bp.route('/api/payment-plans/<int:client_id>', methods=['GET'])
@login_required
def get_client_plan(client_id):
    """Obtener plan detallado de un cliente"""
    print(f"\n🔍 GET /api/payment-plans/{client_id}")
    
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    print(f"   month={month}, year={year}")
    
    if not month or not year:
        return jsonify({'error': 'Se requieren month y year'}), 400
    
    db = get_db()
    
    # Verificar que el cliente existe
    cur = db.execute('SELECT id, name FROM clients WHERE id=?', (client_id,))
    client = cur.fetchone()
    
    if not client:
        print(f"   ❌ Cliente {client_id} no encontrado")
        return jsonify({'error': 'Cliente no encontrado'}), 404
    
    print(f"   ✅ Cliente: {client['name']}")
    
    # Obtener configuración del plan
    cur = db.execute('''
        SELECT payments_count, monthly_amount 
        FROM payment_plan_config 
        WHERE client_id=? AND month=? AND year=?
    ''', (client_id, month, year))
    
    config = cur.fetchone()
    
    if not config:
        # Usar valores por defecto del cliente
        cur = db.execute('SELECT monthly_amount FROM clients WHERE id=?', (client_id,))
        client_data = cur.fetchone()
        payments_count = 1
        monthly_amount = client_data['monthly_amount'] if client_data else 0
        print(f"   ℹ️  Usando valores por defecto: {payments_count} pagos de ${monthly_amount}")
    else:
        payments_count = config['payments_count']
        monthly_amount = config['monthly_amount']
        print(f"   ✅ Configuración encontrada: {payments_count} pagos de ${monthly_amount}")
    
    # Obtener todos los pagos
    cur = db.execute('''
        SELECT payment_number, amount, paid, paid_date
        FROM payment_plan_payments
        WHERE client_id=? AND month=? AND year=?
        ORDER BY payment_number
    ''', (client_id, month, year))
    
    payments = [dict(row) for row in cur.fetchall()]
    
    print(f"   📊 {len(payments)} pagos encontrados")
    
    return jsonify({
        'payments_count': payments_count,
        'monthly_amount': monthly_amount,
        'payments': payments
    })

@bp.route('/api/payment-plans/update', methods=['POST'])
@login_required
def update_plan():
    """Actualizar configuración del plan de un cliente"""
    print("\n🔧 POST /api/payment-plans/update")
    
    try:
        data = request.json
        print(f"📥 Datos recibidos: {data}")
        
        client_id = data.get('client_id')
        month = data.get('month')
        year = data.get('year')
        payments_count = data.get('payments_count')
        monthly_amount = data.get('monthly_amount')
        
        print(f"📊 Procesando:")
        print(f"   client_id: {client_id}")
        print(f"   month: {month}")
        print(f"   year: {year}")
        print(f"   payments_count: {payments_count}")
        print(f"   monthly_amount: {monthly_amount}")
        
        # Validar datos requeridos
        if not all([client_id, month is not None, year is not None, payments_count, monthly_amount is not None]):
            missing = []
            if not client_id: missing.append('client_id')
            if month is None: missing.append('month')
            if year is None: missing.append('year')
            if not payments_count: missing.append('payments_count')
            if monthly_amount is None: missing.append('monthly_amount')
            
            error_msg = f"Faltan campos: {', '.join(missing)}"
            print(f"   ❌ {error_msg}")
            return jsonify({'ok': False, 'error': error_msg}), 400
        
        db = get_db()
        
        # Verificar si existe configuración
        cur = db.execute('''
            SELECT id FROM payment_plan_config 
            WHERE client_id=? AND month=? AND year=?
        ''', (client_id, month, year))
        
        existing = cur.fetchone()
        
        if existing:
            # Actualizar
            print(f"🔄 Actualizando configuración existente ID {existing['id']}")
            db.execute('''
                UPDATE payment_plan_config 
                SET payments_count=?, monthly_amount=?, updated_at=datetime('now')
                WHERE id=?
            ''', (payments_count, monthly_amount, existing['id']))
            print("   ✅ UPDATE exitoso")
        else:
            # Insertar
            print(f"➕ Insertando nueva configuración")
            db.execute('''
                INSERT INTO payment_plan_config 
                (client_id, month, year, payments_count, monthly_amount, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            ''', (client_id, month, year, payments_count, monthly_amount))
            print("   ✅ INSERT exitoso")
        
        # Calcular monto por pago
        amount_per_payment = monthly_amount / payments_count if payments_count > 0 else 0
        
        print(f"\n📝 Actualizando pagos individuales (${amount_per_payment:.2f} cada uno)")
        
        # Crear o actualizar pagos individuales
        for payment_num in range(1, payments_count + 1):
            cur = db.execute('''
                SELECT id FROM payment_plan_payments
                WHERE client_id=? AND month=? AND year=? AND payment_number=?
            ''', (client_id, month, year, payment_num))
            
            existing_payment = cur.fetchone()
            
            if existing_payment:
                # Actualizar solo si no está pagado
                db.execute('''
                    UPDATE payment_plan_payments 
                    SET amount=?, updated_at=datetime('now')
                    WHERE id=? AND paid=0
                ''', (amount_per_payment, existing_payment['id']))
            else:
                # Crear nuevo pago
                db.execute('''
                    INSERT INTO payment_plan_payments
                    (client_id, month, year, payment_number, amount, paid, created_at)
                    VALUES (?, ?, ?, ?, ?, 0, datetime('now'))
                ''', (client_id, month, year, payment_num, amount_per_payment))
        
        db.commit()
        print("💾 COMMIT exitoso")
        print(f"✅ Plan actualizado: {payments_count} pagos de ${amount_per_payment:.2f}\n")
        
        return jsonify({
            'ok': True,
            'payments_count': payments_count,
            'amount_per_payment': round(amount_per_payment, 2)
        })
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/payment-plans/toggle', methods=['POST'])
@login_required
def toggle_payment():
    """Marcar/desmarcar un pago como pagado - VERSION CON DEBUG COMPLETO"""
    print("\n" + "="*60)
    print("🔵 INICIO toggle_payment")
    print("="*60)
    
    try:
        # VERIFICACIÓN INICIAL: ¿Existe la tabla?
        print("\n🔍 VERIFICACIÓN INICIAL: Comprobando existencia de tabla")
        db = get_db()
        
        try:
            check_table = db.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='payment_plan_payments'
            """)
            table_exists = check_table.fetchone()
            
            if table_exists:
                print("   ✅ Tabla 'payment_plan_payments' existe")
                
                # Mostrar estructura de la tabla
                print("\n📊 Estructura de la tabla:")
                columns_info = db.execute("PRAGMA table_info(payment_plan_payments)")
                for col in columns_info.fetchall():
                    print(f"   - {col[1]} ({col[2]}) {'NOT NULL' if col[3] else 'NULL'}")
            else:
                print("   ❌ ERROR: La tabla 'payment_plan_payments' NO EXISTE")
                print("   💡 Ejecuta: python run.py para crear las tablas")
                return jsonify({
                    'ok': False, 
                    'error': 'Tabla payment_plan_payments no existe. Reinicia el servidor.'
                }), 500
        except Exception as e:
            print(f"   ❌ Error al verificar tabla: {str(e)}")
        
        # Continúa con el resto de la lógica...
        print("\n📥 Step 1: Recibiendo datos del request")
        data = request.json
        print(f"   Datos completos: {data}")
        
        client_id = data.get('client_id')
        month = data.get('month')
        year = data.get('year')
        payment_number = data.get('payment_number')
        paid = data.get('paid')
        amount = data.get('amount')
        
        print(f"\n📊 Datos extraídos:")
        print(f"   client_id: {client_id}")
        print(f"   month: {month}")
        print(f"   year: {year}")
        print(f"   payment_number: {payment_number}")
        print(f"   paid: {paid}")
        print(f"   amount: {amount}")
        
        # Validación
        if not all([client_id, month is not None, year is not None, payment_number is not None]):
            missing = []
            if not client_id: missing.append('client_id')
            if month is None: missing.append('month')
            if year is None: missing.append('year')
            if payment_number is None: missing.append('payment_number')
            
            error_msg = f"Faltan campos: {', '.join(missing)}"
            print(f"   ❌ {error_msg}")
            return jsonify({'ok': False, 'error': error_msg}), 400
        
        print("   ✅ Validación OK")
        
        # Buscar pago existente
        print(f"\n🔍 Buscando pago: client={client_id}, mes={month}, año={year}, #={payment_number}")
        
        cur = db.execute('''
            SELECT id, paid, amount FROM payment_plan_payments
            WHERE client_id=? AND month=? AND year=? AND payment_number=?
        ''', (client_id, month, year, payment_number))
        
        existing = cur.fetchone()
        
        if existing:
            print(f"   ✅ Encontrado: ID={existing['id']}, paid={existing['paid']}, amount={existing['amount']}")
        else:
            print(f"   ℹ️  No existe, se creará nuevo")
        
        paid_date = datetime.now().strftime('%Y-%m-%d') if paid else None
        
        if existing:
            print(f"\n🔄 ACTUALIZANDO pago ID {existing['id']}")
            print(f"   paid: {existing['paid']} → {1 if paid else 0}")
            print(f"   paid_date: → {paid_date}")
            
            db.execute('''
                UPDATE payment_plan_payments 
                SET paid=?, paid_date=?, updated_at=datetime('now')
                WHERE id=?
            ''', (1 if paid else 0, paid_date, existing['id']))
            
            print("   ✅ UPDATE exitoso")
        else:
            # Obtener amount si no viene
            if amount is None:
                print(f"\n⚠️  amount no proporcionado, buscando monthly_amount del cliente {client_id}")
                client_cur = db.execute('SELECT monthly_amount FROM clients WHERE id=?', (client_id,))
                client = client_cur.fetchone()
                
                if client:
                    amount = client['monthly_amount']
                    print(f"   ✅ amount={amount} obtenido del cliente")
                else:
                    print(f"   ❌ Cliente {client_id} no encontrado")
                    return jsonify({'ok': False, 'error': f'Cliente {client_id} no existe'}), 404
            
            print(f"\n➕ INSERTANDO nuevo pago")
            print(f"   client_id={client_id}, month={month}, year={year}")
            print(f"   payment_number={payment_number}, amount={amount}, paid={1 if paid else 0}")
            
            db.execute('''
                INSERT INTO payment_plan_payments 
                (client_id, month, year, payment_number, amount, paid, paid_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (client_id, month, year, payment_number, amount, 1 if paid else 0, paid_date))
            
            print("   ✅ INSERT exitoso")
        
        print("\n💾 Ejecutando COMMIT...")
        db.commit()
        print("   ✅ COMMIT exitoso")
        
        print("\n" + "="*60)
        print("🟢 toggle_payment completado exitosamente")
        print("="*60 + "\n")
        
        return jsonify({'ok': True})
    
    except Exception as e:
        print("\n" + "="*60)
        print("🔴 ERROR CRÍTICO")
        print("="*60)
        print(f"❌ Error: {str(e)}")
        print(f"❌ Tipo: {type(e).__name__}")
        
        import traceback
        print(f"\n📋 Stack trace:")
        traceback.print_exc()
        
        print("="*60 + "\n")
        
        return jsonify({
            'ok': False, 
            'error': str(e),
            'error_type': type(e).__name__
        }), 500

@bp.route('/api/export-client-plan/<int:client_id>')
@login_required
def export_client_plan(client_id):
    """Exportar plan de pagos de un cliente"""
    print(f"\n📤 GET /api/export-client-plan/{client_id}")
    
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    print(f"   month={month}, year={year}")
    
    if not month or not year:
        return jsonify({'error': 'Se requieren month y year'}), 400
    
    db = get_db()
    cur = db.execute('SELECT name FROM clients WHERE id=?', (client_id,))
    client = cur.fetchone()
    
    if not client:
        print(f"   ❌ Cliente {client_id} no encontrado")
        return jsonify({'error': 'Cliente no encontrado'}), 404
    
    print(f"   ✅ Cliente: {client['name']}")
    print(f"   ℹ️  Funcionalidad de exportación en desarrollo")
    
    # Aquí implementarías la exportación a Excel/PDF
    # Por ahora retornamos un JSON
    
    return jsonify({
        'client_name': client['name'],
        'month': month,
        'year': year,
        'message': 'Exportación en desarrollo'
    })