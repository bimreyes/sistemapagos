SISTEMA PAGOS - VERSIÓN FINAL

Estructura:
- backend/app/ : código Flask modular
- backend/templates/ : plantillas Jinja2
- backend/static/ : css, reports, thumbs
- uploads/ : archivos de clientes
- sistemapagos.db : generado al iniciar la app

Características:
- Autenticación, sesiones
- CRUD clientes y pagos
- Historial inmutable con triggers
- Uploads con thumbnails
- Reportes PNG (matplotlib), export CSV/XLSX, generación PDF
- API básica y stub de WhatsApp para integración futura
- Backup/restore, Dockerfile

Ejecutar:
1. python3 -m venv venv
2. source venv/bin/activate (Windows: venv\Scripts\activate)
3. pip install -r requirements.txt
4. python run.py
5. Abrir http://127.0.0.1:5000/auth/login (admin/admin)
