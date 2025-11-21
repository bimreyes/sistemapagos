from backend.app import create_app
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

app = create_app()

if __name__ == '__main__':
    print("🚀 Iniciando servidor...")
    print("📱 WhatsApp configurado para envío INMEDIATO")
    
    # Verificar configuración
    if os.getenv('WHATSAPP_PHONE_ID') and os.getenv('WHATSAPP_PHONE_ID') != 'tu_phone_number_id_aqui':
        print("✅ WhatsApp API configurada correctamente")
    else:
        print("⚠️  WhatsApp en modo DEMO (configura .env para envíos reales)")
    
    app.run(host='0.0.0.0', port=5000, debug=False)