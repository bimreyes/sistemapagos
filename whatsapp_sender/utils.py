"""
Utilidades para el módulo WhatsApp Sender
"""
import re
import logging
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def validate_phone(phone: str, country_code: str = "51") -> Tuple[bool, str, str]:
    """
    Valida y normaliza un número telefónico
    
    Returns:
        Tuple[is_valid, normalized_number, error_message]
    """
    if not phone:
        return False, "", "Número vacío"
    
    # Limpiar caracteres no numéricos excepto +
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    
    if not cleaned:
        return False, "", "Número inválido"
    
    # Normalizar
    if cleaned.startswith('+'):
        normalized = cleaned[1:]
    elif cleaned.startswith('00'):
        normalized = cleaned[2:]
    elif cleaned.startswith('0'):
        normalized = country_code + cleaned[1:]
    elif len(cleaned) == 9:  # Número local (Perú)
        normalized = country_code + cleaned
    else:
        normalized = cleaned
    
    # Validar longitud (número internacional típico: 10-15 dígitos)
    if len(normalized) < 10 or len(normalized) > 15:
        return False, normalized, f"Longitud inválida: {len(normalized)} dígitos"
    
    # Verificar que sean solo dígitos
    if not normalized.isdigit():
        return False, normalized, "Contiene caracteres no numéricos"
    
    return True, normalized, ""


def format_phone_display(phone: str) -> str:
    """Formatea un número para mostrar de forma legible"""
    if not phone:
        return ""
    
    # Limpiar
    cleaned = re.sub(r'[^\d]', '', phone)
    
    if len(cleaned) == 11 and cleaned.startswith('51'):
        # Perú: +51 999 999 999
        return f"+{cleaned[:2]} {cleaned[2:5]} {cleaned[5:8]} {cleaned[8:]}"
    elif len(cleaned) >= 10:
        # Genérico: +XX XXX XXX XXXX
        return f"+{cleaned[:2]} {cleaned[2:5]} {cleaned[5:8]} {cleaned[8:]}"
    
    return phone


def sanitize_message(message: str) -> str:
    """
    Sanitiza un mensaje para envío seguro
    - Elimina caracteres problemáticos
    - Limita longitud
    - Normaliza saltos de línea
    """
    if not message:
        return ""
    
    # Normalizar saltos de línea
    sanitized = message.replace('\r\n', '\n').replace('\r', '\n')
    
    # Eliminar múltiples espacios
    sanitized = re.sub(r' +', ' ', sanitized)
    
    # Eliminar múltiples saltos de línea (máximo 2)
    sanitized = re.sub(r'\n{3,}', '\n\n', sanitized)
    
    # Limitar longitud (WhatsApp permite ~65000 pero mejor mantenerlo corto)
    max_length = 4096
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length-3] + "..."
        logger.warning(f"Mensaje truncado a {max_length} caracteres")
    
    return sanitized.strip()


def is_within_sending_hours(start_hour: int = 9, end_hour: int = 20) -> bool:
    """Verifica si estamos en horario de envío"""
    current_hour = datetime.now().hour
    return start_hour <= current_hour < end_hour


def is_allowed_day(allowed_days: tuple = (0, 1, 2, 3, 4)) -> bool:
    """Verifica si hoy es un día permitido para envíos (0=Lun, 6=Dom)"""
    return datetime.now().weekday() in allowed_days


def calculate_delay(messages_sent: int, base_min: int = 45, base_max: int = 120) -> Tuple[int, int]:
    """
    Calcula delays adaptativos según cantidad de mensajes enviados
    A más mensajes, más conservador el delay
    """
    factor = 1 + (messages_sent // 50) * 0.2  # Aumenta 20% cada 50 mensajes
    
    min_delay = int(base_min * factor)
    max_delay = int(base_max * factor)
    
    # Límites
    min_delay = min(min_delay, 300)  # Máximo 5 minutos de delay mínimo
    max_delay = min(max_delay, 600)  # Máximo 10 minutos de delay máximo
    
    return min_delay, max_delay


def get_greeting() -> str:
    """Retorna saludo según hora del día"""
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "Buenos días"
    elif 12 <= hour < 19:
        return "Buenas tardes"
    else:
        return "Buenas noches"


def mask_phone(phone: str) -> str:
    """Enmascara un número telefónico para logs (privacidad)"""
    if not phone or len(phone) < 6:
        return "***"
    
    return phone[:3] + "****" + phone[-3:]


def parse_whatsapp_url(url: str) -> Optional[str]:
    """Extrae número telefónico de una URL de WhatsApp"""
    patterns = [
        r'wa\.me/(\d+)',
        r'whatsapp\.com/send\?phone=(\d+)',
        r'api\.whatsapp\.com/send\?phone=(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def estimate_send_time(num_messages: int, min_delay: int = 45, max_delay: int = 120,
                       batch_size: int = 15, batch_delay: int = 300) -> str:
    """
    Estima tiempo total de envío
    
    Returns:
        String con tiempo estimado legible
    """
    avg_delay = (min_delay + max_delay) / 2
    
    # Tiempo por mensajes
    message_time = num_messages * avg_delay
    
    # Tiempo por pausas entre batches
    num_batches = num_messages // batch_size
    batch_time = num_batches * batch_delay
    
    total_seconds = message_time + batch_time
    
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    
    if hours > 0:
        return f"{hours}h {minutes}min"
    else:
        return f"{minutes} minutos"


class RateLimiter:
    """Rate limiter simple para controlar envíos"""
    
    def __init__(self, max_per_hour: int = 30, max_per_day: int = 200):
        self.max_per_hour = max_per_hour
        self.max_per_day = max_per_day
        self.hourly_count = 0
        self.daily_count = 0
        self.current_hour = datetime.now().hour
        self.current_day = datetime.now().day
    
    def can_send(self) -> Tuple[bool, str]:
        """Verifica si se puede enviar"""
        now = datetime.now()
        
        # Reset horario
        if now.hour != self.current_hour:
            self.hourly_count = 0
            self.current_hour = now.hour
        
        # Reset diario
        if now.day != self.current_day:
            self.daily_count = 0
            self.current_day = now.day
        
        if self.hourly_count >= self.max_per_hour:
            return False, f"Límite horario alcanzado ({self.max_per_hour})"
        
        if self.daily_count >= self.max_per_day:
            return False, f"Límite diario alcanzado ({self.max_per_day})"
        
        return True, ""
    
    def record_send(self):
        """Registra un envío"""
        self.hourly_count += 1
        self.daily_count += 1
    
    def get_stats(self) -> dict:
        """Retorna estadísticas actuales"""
        return {
            'hourly_count': self.hourly_count,
            'hourly_limit': self.max_per_hour,
            'hourly_remaining': self.max_per_hour - self.hourly_count,
            'daily_count': self.daily_count,
            'daily_limit': self.max_per_day,
            'daily_remaining': self.max_per_day - self.daily_count
        }