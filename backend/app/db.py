import sqlite3
import os
from flask import g
from werkzeug.security import generate_password_hash

DATABASE = os.path.join(os.getcwd(), 'sistemapagos.db')

def get_db():
    """Obtiene la conexión a la base de datos del contexto de Flask"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def close_connection(exception):
    """Cierra la conexión a la base de datos"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db(app=None):
    """Inicializa la base de datos y ejecuta migraciones"""
    if app:
        with app.app_context():
            _init()
            _run_migrations()
    else:
        _init()
        _run_migrations()

def _init():
    """Crea las tablas iniciales si no existen"""
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    
    try:
        # Habilitar foreign keys
        cur.execute("PRAGMA foreign_keys = ON")
        
        # Main tables creation
        cur.executescript(r"""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY, 
                username TEXT UNIQUE NOT NULL, 
                password TEXT NOT NULL, 
                created_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, 
                value TEXT
            );
            
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY, 
                name TEXT NOT NULL, 
                phone TEXT, 
                monthly_amount REAL NOT NULL DEFAULT 0, 
                signup_date TEXT NOT NULL, 
                active INTEGER NOT NULL DEFAULT 1
            );
            
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY, 
                client_id INTEGER NOT NULL, 
                year INTEGER NOT NULL, 
                month INTEGER NOT NULL, 
                amount REAL NOT NULL, 
                status TEXT NOT NULL DEFAULT 'pending', 
                paid_date TEXT, 
                payment_type TEXT, 
                FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY, 
                client_id INTEGER NOT NULL, 
                filename TEXT NOT NULL, 
                stored_path TEXT NOT NULL, 
                uploaded_at TEXT NOT NULL, 
                thumb_path TEXT, 
                FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS historial_cambios (
                id INTEGER PRIMARY KEY, 
                tabla TEXT NOT NULL, 
                operacion TEXT NOT NULL, 
                usuario TEXT, 
                fecha_hora TEXT NOT NULL, 
                old_values TEXT, 
                new_values TEXT
            );
        """)
        
        # Tablas adicionales para planes de pago personalizados
        cur.executescript(r"""
            -- Configuración de planes de pago por mes
            CREATE TABLE IF NOT EXISTS payment_plan_config (
                id INTEGER PRIMARY KEY,
                client_id INTEGER NOT NULL,
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                payments_count INTEGER NOT NULL DEFAULT 1,
                monthly_amount REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE,
                UNIQUE(client_id, month, year)
            );
            
            -- Pagos individuales dentro de un mes (múltiples pagos por mes)
            CREATE TABLE IF NOT EXISTS payment_plan_payments (
                id INTEGER PRIMARY KEY,
                client_id INTEGER NOT NULL,
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                payment_number INTEGER NOT NULL,
                amount REAL NOT NULL,
                paid INTEGER NOT NULL DEFAULT 0,
                paid_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE,
                UNIQUE(client_id, month, year, payment_number)
            );
            
            -- Índices para mejorar rendimiento
            CREATE INDEX IF NOT EXISTS idx_plan_config_client 
            ON payment_plan_config(client_id, month, year);
            
            CREATE INDEX IF NOT EXISTS idx_plan_payments_client 
            ON payment_plan_payments(client_id, month, year);
            
            CREATE INDEX IF NOT EXISTS idx_payments_client_date
            ON payments(client_id, year, month);
        """)
        
        # Tablas adicionales del sistema
        cur.executescript(r"""
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY,
                username TEXT,
                ip TEXT,
                user_agent TEXT,
                action TEXT,
                created_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS whatsapp_queue (
                id INTEGER PRIMARY KEY,
                client_id INTEGER,
                message TEXT NOT NULL,
                template TEXT,
                attachment TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                scheduled_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
            );
        """)
        
        # Triggers para historial de cambios
        cur.executescript(r"""
            -- Triggers para la tabla clients
            CREATE TRIGGER IF NOT EXISTS trg_clients_insert 
            AFTER INSERT ON clients 
            BEGIN 
                INSERT INTO historial_cambios(tabla, operacion, usuario, fecha_hora, old_values, new_values) 
                VALUES('clients','INSERT', COALESCE(NEW.id || '', 'system'), datetime('now'), NULL, 
                       json_object('id', NEW.id, 'name', NEW.name, 'phone', NEW.phone, 
                                  'monthly_amount', NEW.monthly_amount, 'signup_date', NEW.signup_date, 
                                  'active', NEW.active)); 
            END;
            
            CREATE TRIGGER IF NOT EXISTS trg_clients_update 
            AFTER UPDATE ON clients 
            BEGIN 
                INSERT INTO historial_cambios(tabla, operacion, usuario, fecha_hora, old_values, new_values) 
                VALUES('clients','UPDATE', COALESCE(NEW.id || '', 'system'), datetime('now'), 
                       json_object('id', OLD.id, 'name', OLD.name, 'phone', OLD.phone, 
                                  'monthly_amount', OLD.monthly_amount, 'signup_date', OLD.signup_date, 
                                  'active', OLD.active), 
                       json_object('id', NEW.id, 'name', NEW.name, 'phone', NEW.phone, 
                                  'monthly_amount', NEW.monthly_amount, 'signup_date', NEW.signup_date, 
                                  'active', NEW.active)); 
            END;
            
            CREATE TRIGGER IF NOT EXISTS trg_clients_delete 
            AFTER DELETE ON clients 
            BEGIN 
                INSERT INTO historial_cambios(tabla, operacion, usuario, fecha_hora, old_values, new_values) 
                VALUES('clients','DELETE', COALESCE(OLD.id || '', 'system'), datetime('now'), 
                       json_object('id', OLD.id, 'name', OLD.name, 'phone', OLD.phone, 
                                  'monthly_amount', OLD.monthly_amount, 'signup_date', OLD.signup_date, 
                                  'active', OLD.active), NULL); 
            END;
            
            -- Triggers para la tabla payments
            CREATE TRIGGER IF NOT EXISTS trg_payments_insert 
            AFTER INSERT ON payments 
            BEGIN 
                INSERT INTO historial_cambios(tabla, operacion, usuario, fecha_hora, old_values, new_values) 
                VALUES('payments','INSERT', COALESCE(NEW.client_id || '', 'system'), datetime('now'), NULL, 
                       json_object('id', NEW.id, 'client_id', NEW.client_id, 'year', NEW.year, 
                                  'month', NEW.month, 'amount', NEW.amount, 'status', NEW.status, 
                                  'paid_date', NEW.paid_date, 'payment_type', NEW.payment_type)); 
            END;
            
            CREATE TRIGGER IF NOT EXISTS trg_payments_update 
            AFTER UPDATE ON payments 
            BEGIN 
                INSERT INTO historial_cambios(tabla, operacion, usuario, fecha_hora, old_values, new_values) 
                VALUES('payments','UPDATE', COALESCE(NEW.client_id || '', 'system'), datetime('now'), 
                       json_object('id', OLD.id, 'client_id', OLD.client_id, 'year', OLD.year, 
                                  'month', OLD.month, 'amount', OLD.amount, 'status', OLD.status, 
                                  'paid_date', OLD.paid_date, 'payment_type', OLD.payment_type), 
                       json_object('id', NEW.id, 'client_id', NEW.client_id, 'year', NEW.year, 
                                  'month', NEW.month, 'amount', NEW.amount, 'status', NEW.status, 
                                  'paid_date', NEW.paid_date, 'payment_type', NEW.payment_type)); 
            END;
            
            CREATE TRIGGER IF NOT EXISTS trg_payments_delete 
            AFTER DELETE ON payments 
            BEGIN 
                INSERT INTO historial_cambios(tabla, operacion, usuario, fecha_hora, old_values, new_values) 
                VALUES('payments','DELETE', COALESCE(OLD.client_id || '', 'system'), datetime('now'), 
                       json_object('id', OLD.id, 'client_id', OLD.client_id, 'year', OLD.year, 
                                  'month', OLD.month, 'amount', OLD.amount, 'status', OLD.status, 
                                  'paid_date', OLD.paid_date, 'payment_type', OLD.payment_type), NULL); 
            END;
            
            -- Triggers para la tabla uploads
            CREATE TRIGGER IF NOT EXISTS trg_uploads_insert 
            AFTER INSERT ON uploads 
            BEGIN 
                INSERT INTO historial_cambios(tabla, operacion, usuario, fecha_hora, old_values, new_values) 
                VALUES('uploads','INSERT', COALESCE(NEW.client_id || '', 'system'), datetime('now'), NULL, 
                       json_object('id', NEW.id, 'client_id', NEW.client_id, 'filename', NEW.filename, 
                                  'stored_path', NEW.stored_path, 'uploaded_at', NEW.uploaded_at)); 
            END;
            
            CREATE TRIGGER IF NOT EXISTS trg_uploads_delete 
            AFTER DELETE ON uploads 
            BEGIN 
                INSERT INTO historial_cambios(tabla, operacion, usuario, fecha_hora, old_values, new_values) 
                VALUES('uploads','DELETE', COALESCE(OLD.client_id || '', 'system'), datetime('now'), 
                       json_object('id', OLD.id, 'client_id', OLD.client_id, 'filename', OLD.filename, 
                                  'stored_path', OLD.stored_path, 'uploaded_at', OLD.uploaded_at), NULL); 
            END;
            
            -- Protección del historial (inmutable)
            CREATE TRIGGER IF NOT EXISTS protect_historial_update 
            BEFORE UPDATE ON historial_cambios 
            BEGIN 
                SELECT RAISE(ABORT, 'historial_cambios is immutable'); 
            END;
            
            CREATE TRIGGER IF NOT EXISTS protect_historial_delete 
            BEFORE DELETE ON historial_cambios 
            BEGIN 
                SELECT RAISE(ABORT, 'historial_cambios is immutable'); 
            END;
        """)
        
        conn.commit()
        print("✅ Tablas creadas correctamente")
        
        # Crear admin por defecto si no existe
        cur.execute("SELECT COUNT(*) FROM admins")
        if cur.fetchone()[0] == 0:
            pwd = generate_password_hash('admin')
            cur.execute("INSERT INTO admins(username, password, created_at) VALUES (?, ?, datetime('now'))", 
                       ('admin', pwd))
            conn.commit()
            print("✅ Usuario admin creado (usuario: admin, contraseña: admin)")
    
    except sqlite3.Error as e:
        print(f"❌ Error al crear tablas: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def _run_migrations():
    """
    Ejecuta migraciones para actualizar bases de datos existentes.
    Esta función se ejecuta automáticamente después de _init().
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    migrations_applied = []
    
    try:
        # MIGRACIÓN 1: Agregar columna custom_amount a payments
        cursor.execute("PRAGMA table_info(payments)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'custom_amount' not in columns:
            print("🔄 Ejecutando migración: agregar custom_amount...")
            cursor.execute('ALTER TABLE payments ADD COLUMN custom_amount REAL')
            
            # Migrar datos existentes: copiar amount a custom_amount
            cursor.execute('''
                UPDATE payments 
                SET custom_amount = amount 
                WHERE custom_amount IS NULL
            ''')
            
            conn.commit()
            migrations_applied.append("custom_amount agregado a payments")
            print("   ✅ custom_amount agregado")
        
        # MIGRACIÓN 2: Verificar que paid_date exista en payments
        cursor.execute("PRAGMA table_info(payments)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'paid_date' not in columns:
            print("🔄 Ejecutando migración: agregar paid_date...")
            cursor.execute('ALTER TABLE payments ADD COLUMN paid_date TEXT')
            conn.commit()
            migrations_applied.append("paid_date agregado a payments")
            print("   ✅ paid_date agregado")
        
        # MIGRACIÓN 3: Verificar que payment_type exista en payments
        if 'payment_type' not in columns:
            print("🔄 Ejecutando migración: agregar payment_type...")
            cursor.execute('ALTER TABLE payments ADD COLUMN payment_type TEXT')
            conn.commit()
            migrations_applied.append("payment_type agregado a payments")
            print("   ✅ payment_type agregado")
        
        # MIGRACIÓN 4: Actualizar pagos sin custom_amount
        cursor.execute('''
            UPDATE payments 
            SET custom_amount = amount 
            WHERE custom_amount IS NULL
        ''')
        conn.commit()
        
        # MIGRACIÓN 5: Crear índices si no existen
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_payments_status 
            ON payments(status)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_payments_client_status
            ON payments(client_id, status)
        ''')
        
        conn.commit()
        migrations_applied.append("Índices optimizados")
        
        # Resumen de migraciones
        if migrations_applied:
            print(f"✅ Migraciones completadas: {len(migrations_applied)}")
            for migration in migrations_applied:
                print(f"   - {migration}")
        else:
            print("ℹ️  No hay migraciones pendientes")
    
    except sqlite3.Error as e:
        print(f"❌ Error en migraciones: {str(e)}")
        conn.rollback()
    except Exception as e:
        print(f"❌ Error inesperado en migraciones: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def verify_database_integrity():
    """
    Verifica la integridad de la base de datos.
    Útil para debugging.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        print("\n🔍 Verificando integridad de la base de datos...")
        
        # Verificar integridad
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        
        if result == "ok":
            print("   ✅ Integridad: OK")
        else:
            print(f"   ⚠️  Problemas de integridad: {result}")
        
        # Contar registros en tablas principales
        tables = ['clients', 'payments', 'admins', 'uploads', 'historial_cambios']
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   📊 {table}: {count} registros")
            except sqlite3.Error:
                print(f"   ⚠️  Tabla {table} no existe")
        
        # Verificar foreign keys
        cursor.execute("PRAGMA foreign_key_check")
        fk_errors = cursor.fetchall()
        
        if fk_errors:
            print(f"   ⚠️  Errores de foreign keys: {len(fk_errors)}")
            for error in fk_errors:
                print(f"      - {error}")
        else:
            print("   ✅ Foreign keys: OK")
        
        print("✅ Verificación completada\n")
        
    except Exception as e:
        print(f"❌ Error en verificación: {str(e)}")
    finally:
        conn.close()

# Ejecutar verificación solo si se ejecuta directamente
if __name__ == '__main__':
    print("🚀 Inicializando base de datos...")
    _init()
    _run_migrations()
    verify_database_integrity()