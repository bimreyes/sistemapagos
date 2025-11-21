import os
import requests
from datetime import datetime

# Configuración de WhatsApp Business API
WHATSAPP_API_URL = "https://graph.facebook.com/v18.0"
WHATSAPP_PHONE_ID = os.getenv('WHATSAPP_PHONE_ID', 'TU_PHONE_NUMBER_ID')
WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN', 'TU_ACCESS_TOKEN')

def send_whatsapp_message_now(phone_number, message):
    """
    Envía un mensaje INMEDIATAMENTE por WhatsApp usando la API oficial
    
    Args:
        phone_number: Número de teléfono con código de país (ej: +51999888777)
        message: Texto del mensaje a enviar
        
    Returns:
        tuple: (success: bool, message_id: str or error: str)
    """
    
    # Validar configuración
    if WHATSAPP_PHONE_ID == 'TU_PHONE_NUMBER_ID' or WHATSAPP_ACCESS_TOKEN == 'TU_ACCESS_TOKEN':
        print("⚠️ WhatsApp no configurado. Usando modo DEMO.")
        print("📋 Configura WHATSAPP_PHONE_ID y WHATSAPP_ACCESS_TOKEN en .env")
        # Retornar éxito en modo demo para testing
        return True, "demo-message-id"
    
    # Limpiar número de teléfono
    clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
    
    # Construir URL
    url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_ID}/messages"
    
    # Headers
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Payload
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message
        }
    }
    
    try:
        # Enviar mensaje INMEDIATAMENTE
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Verificar respuesta
        if response.status_code == 200:
            data = response.json()
            message_id = data.get('messages', [{}])[0].get('id', 'unknown')
            print(f"✅ Mensaje enviado a {phone_number}: {message_id}")
            return True, message_id
        else:
            error_msg = response.json().get('error', {}).get('message', 'Error desconocido')
            print(f"❌ Error enviando a {phone_number}: {error_msg}")
            return False, error_msg
            
    except requests.exceptions.Timeout:
        error_msg = "Timeout: La API de WhatsApp no respondió a tiempo"
        print(f"❌ {error_msg}")
        return False, error_msg
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error de conexión: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Error inesperado: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg
