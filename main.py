import logging
from logging.handlers import RotatingFileHandler
from app import settings

if __name__ == '__main__':
    log_path = settings.PATH.parent / 'gesture-control.log'
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=2, encoding='utf-8')
    logging.basicConfig(level=logging.WARNING, handlers=[handler], format='%(asctime)s %(levelname)s %(message)s')
    try:
        from app.ui import main
        main()
    except Exception:
        logging.exception('Application startup failed')
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, f'Не удалось запустить программу. Подробности: {log_path}', 'Gesture Control', 0x10)
