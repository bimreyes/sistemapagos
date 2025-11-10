import sqlite3, os
from flask import g
from werkzeug.security import generate_password_hash

DATABASE = os.path.join(os.getcwd(), 'sistemapagos.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db(app=None):
    if app:
        with app.app_context():
            _init()
    else:
        _init()

def _init():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    
    # Main tables creation
    cur.executescript(r"""
        PRAGMA foreign_keys = ON;
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
            FOREIGN KEY(client_id) REFERENCES clients(id)
        );
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY, 
            client_id INTEGER NOT NULL, 
            filename TEXT NOT NULL, 
            stored_path TEXT NOT NULL, 
            uploaded_at TEXT NOT NULL, 
            thumb_path TEXT, 
            FOREIGN KEY(client_id) REFERENCES clients(id)
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
    
    # Additional tables for access logs and whatsapp queue
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
            created_at TEXT NOT NULL
        );
    """)
    
    # Create triggers
    cur.executescript(r"""
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
    
    # Commit all changes
    conn.commit()
    
    # Create default admin if no admins exist
    cur.execute("SELECT COUNT(*) FROM admins")
    if cur.fetchone()[0] == 0:
        pwd = generate_password_hash('admin')
        cur.execute("INSERT INTO admins(username, password, created_at) VALUES (?, ?, datetime('now'))", 
                   ('admin', pwd))
        conn.commit()
    
    # Close the connection
    conn.close()