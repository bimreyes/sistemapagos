from flask import Blueprint, jsonify
bp = Blueprint('openapi', __name__)
@bp.route('/openapi.json')
def openapi():
    return jsonify({"openapi": "3.0.0", "info": {"title": "Sistemapagos API", "version": "1.0.0"}, "paths": {"/api/clients": {"get": {"summary": "List clients", "responses": {"200": {"description": "OK"}}}}, "/whatsapp/enqueue": {"post": {"summary": "Enqueue WhatsApp message", "responses": {"201": {"description": "Created"}}}}}})
