"""
WhatsApp Sender Module - Sistema de mensajería automatizada gratuita
Usa Selenium + WhatsApp Web para envío masivo sin API de pago
"""

__version__ = "1.0.0"
__author__ = "Sistema Pagos"

from .config import WhatsAppConfig
from .sender import WhatsAppSender
from .scheduler import MessageScheduler
from .templates import MessageTemplates

__all__ = [
    'WhatsAppConfig',
    'WhatsAppSender', 
    'MessageScheduler',
    'MessageTemplates'
]