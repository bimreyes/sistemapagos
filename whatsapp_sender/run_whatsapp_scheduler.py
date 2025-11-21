#!/usr/bin/env python3
"""
Script para ejecutar el scheduler de WhatsApp como servicio independiente
Puede ejecutarse con cron o como daemon

Uso:
    python run_whatsapp_scheduler.py --daemon        # Ejecutar como daemon
    python run_whatsapp_scheduler.py --once-monthly  # Ejecutar recordatorios una vez
    python run_whatsapp_scheduler.py --once-overdue  # Ejecutar avisos morosos una vez
    python run_whatsapp_scheduler.py --test          # Modo prueba
"""

import argparse
import signal
import sys
import time
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('whatsapp_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Importar módulos de WhatsApp
from whatsapp_sender.scheduler import MessageScheduler
from whatsapp_sender.config import WhatsAppConfig
from whatsapp_sender.db_models import get_config, init_whatsapp_tables


def signal_handler(signum, frame):
    """Manejador de señales para shutdown graceful"""
    logger.info("Señal de terminación recibida. Cerrando...")
    sys.exit(0)


def run_daemon():
    """Ejecuta el scheduler como daemon"""
    logger.info("Iniciando WhatsApp Scheduler como daemon...")
    
    # Inicializar tablas de BD
    init_whatsapp_tables()
    
    # Obtener configuración de BD
    reminder_day = int(get_config('monthly_reminder_day', '5'))
    overdue_day = int(get_config('overdue_reminder_day', '15'))
    start_hour = int(get_config('daily_start_hour', '10'))
    
    # Crear scheduler con configuración
    config = WhatsAppConfig()
    scheduler = MessageScheduler(config)
    
    # Programar tareas
    scheduler.schedule_monthly_job(day=reminder_day, hour=start_hour, minute=0)
    scheduler.schedule_overdue_job(day=overdue_day, hour=start_hour + 1, minute=0)
    
    # Mostrar trabajos programados
    jobs = scheduler.get_scheduled_jobs()
    logger.info(f"Trabajos programados: {len(jobs)}")
    for job in jobs:
        logger.info(f"  - {job['name']}: próxima ejecución {job['next_run']}")
    
    # Iniciar scheduler
    scheduler.start()
    
    # Configurar señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Scheduler ejecutándose. Presiona Ctrl+C para detener.")
    
    try:
        # Mantener el proceso vivo
        while True:
            time.sleep(60)
            # Log de estado cada hora
            if datetime.now().minute == 0:
                logger.info("Scheduler activo - verificando trabajos pendientes")
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
        logger.info("Scheduler detenido correctamente")


def run_once_monthly():
    """Ejecuta los recordatorios mensuales una sola vez"""
    logger.info("Ejecutando recordatorios mensuales...")
    
    init_whatsapp_tables()
    scheduler = MessageScheduler()
    result = scheduler.send_monthly_reminders()
    
    if 'error' in result:
        logger.error(f"Error: {result['error']}")
        return 1
    
    logger.info(f"Completado - Enviados: {result['sent']}, Fallidos: {result['failed']}")
    return 0


def run_once_overdue():
    """Ejecuta los avisos a morosos una sola vez"""
    logger.info("Ejecutando avisos a morosos...")
    
    init_whatsapp_tables()
    scheduler = MessageScheduler()
    result = scheduler.send_overdue_reminders()
    
    if 'error' in result:
        logger.error(f"Error: {result['error']}")
        return 1
    
    logger.info(f"Completado - Enviados: {result['sent']}, Fallidos: {result['failed']}")
    return 0


def run_test():
    """Ejecuta en modo prueba"""
    logger.info("Ejecutando en modo prueba...")
    
    init_whatsapp_tables()
    
    from whatsapp_sender.sender import WhatsAppSender
    
    sender = WhatsAppSender()
    
    logger.info("Iniciando navegador...")
    if not sender.start_browser():
        logger.error("No se pudo iniciar el navegador")
        return 1
    
    logger.info("Abriendo WhatsApp Web...")
    if not sender.login(wait_for_scan=True):
        logger.error("No se pudo completar el login")
        sender.close()
        return 1
    
    logger.info("Login exitoso!")
    logger.info("Sesión de WhatsApp configurada correctamente")
    logger.info("Puedes cerrar el navegador o presionar Ctrl+C")
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        sender.close()
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='WhatsApp Scheduler - Sistema de mensajería automatizada'
    )
    
    parser.add_argument(
        '--daemon', 
        action='store_true',
        help='Ejecutar como daemon (servicio continuo)'
    )
    parser.add_argument(
        '--once-monthly',
        action='store_true',
        help='Ejecutar recordatorios mensuales una vez y terminar'
    )
    parser.add_argument(
        '--once-overdue',
        action='store_true',
        help='Ejecutar avisos a morosos una vez y terminar'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Modo prueba - solo iniciar sesión de WhatsApp'
    )
    
    args = parser.parse_args()
    
    if args.daemon:
        run_daemon()
    elif args.once_monthly:
        sys.exit(run_once_monthly())
    elif args.once_overdue:
        sys.exit(run_once_overdue())
    elif args.test:
        sys.exit(run_test())
    else:
        # Por defecto mostrar ayuda
        parser.print_help()
        print("\n📌 Ejemplos de uso:")
        print("  python run_whatsapp_scheduler.py --test          # Configurar sesión")
        print("  python run_whatsapp_scheduler.py --daemon        # Ejecutar como servicio")
        print("  python run_whatsapp_scheduler.py --once-monthly  # Enviar recordatorios ahora")


if __name__ == '__main__':
    main()