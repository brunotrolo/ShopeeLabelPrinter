"""
Módulo de logging: arquivo + console.
"""

import logging
import os
from datetime import datetime
from pathlib import Path


# Criar diretório de logs em %APPDATA%/ShopeeLabelPrinter
def _get_log_dir():
    if os.name == 'nt':  # Windows
        appdata = os.getenv('APPDATA')
        log_dir = Path(appdata) / 'ShopeeLabelPrinter'
    else:  # macOS/Linux
        log_dir = Path.home() / '.shopee_label_printer'

    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging(console_callback=None):
    """
    Configura logging em arquivo + console.

    Args:
        console_callback: função para enviar logs ao console da GUI
    """
    log_dir = _get_log_dir()
    log_file = log_dir / f"shopee_printer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Configurar logger
    logger = logging.getLogger('shopee_label_printer')
    logger.setLevel(logging.DEBUG)

    # Handler de arquivo
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

    # Handler de console (para callback da GUI)
    if console_callback:
        class CallbackHandler(logging.Handler):
            def emit(self, record):
                msg = self.format(record)
                console_callback(msg)

        ch = CallbackHandler()
        ch.setLevel(logging.INFO)
        logger.addHandler(ch)

    # Formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)

    logger.addHandler(fh)
    logger.info(f"Logging iniciado. Arquivo: {log_file}")

    return logger


def get_logger():
    """Obter logger existente."""
    return logging.getLogger('shopee_label_printer')
