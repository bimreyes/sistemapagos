import os, sqlite3, time
from datetime import datetime
DB = os.path.join(os.getcwd(), 'sistemapagos.db')
def _send_stub(client_id, message, attachment):
    # simulate sending via WhatsApp Business Cloud API (stub)
    # In production replace with actual API call and error handling
    time.sleep(0.1)
    return True, 'message-id-stub'
def process_queue(limit=20):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # fetch pending items
    cur.execute("SELECT * FROM whatsapp_queue WHERE status='pending' ORDER BY created_at LIMIT ?", (limit,))
    rows = cur.fetchall()
    for r in rows:
        try:
            cur.execute("UPDATE whatsapp_queue SET status='sending', attempts=attempts+1 WHERE id=?", (r['id'],))
            conn.commit()
            ok, mid = _send_stub(r['client_id'], r['message'], r['attachment'])
            if ok:
                cur.execute("UPDATE whatsapp_queue SET status='sent' WHERE id=?", (r['id'],))
            else:
                cur.execute("UPDATE whatsapp_queue SET status='failed' WHERE id=?", (r['id'],))
            conn.commit()
        except Exception as e:
            cur.execute("UPDATE whatsapp_queue SET status='failed' WHERE id=?", (r['id'],))
            conn.commit()
    conn.close()
    return len(rows)
