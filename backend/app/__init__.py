import os
from flask import Flask, render_template
from .db import init_db, close_connection

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static")
    )

    app.config.update({
        'SECRET_KEY': 'cambia-esta-clave',
        'UPLOAD_FOLDER': 'uploads',
        'REPORT_FOLDER': 'static/reports'
    })

    init_db(app)

    # register blueprints
    from .blueprints.auth import bp as auth_bp
    from .blueprints.clients import bp as clients_bp
    from .blueprints.payments import bp as payments_bp
    from .blueprints.uploads import bp as uploads_bp
    from .blueprints.admin import bp as admin_bp
    from .blueprints.reports import bp as reports_bp
    from .blueprints.api import bp as api_bp
    from .blueprints.whatsapp import bp as whatsapp_bp
    from .blueprints.payment_plans import bp as payment_plans_bp


    app.register_blueprint(auth_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(payment_plans_bp)
    
    @app.route('/')
    def index():
        return render_template('login.html')

    @app.teardown_appcontext
    def teardown(exc):
        close_connection(exc)

    return app
