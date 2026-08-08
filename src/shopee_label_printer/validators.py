"""
Módulo de validação: checagens adicionais para robustez.
"""

import logging

logger = logging.getLogger(__name__)


def validate_zpl_label(data: bytes) -> bool:
    """
    Valida se os bytes parecem ser um rótulo ZPL/TSPL válido.

    Checks básicos:
    - Não vazio
    - Contém marcadores ZPL (^XA) ou TSPL (~DG)
    - Tamanho razoável (não exceder 10MB)

    Args:
        data: Bytes do rótulo

    Returns:
        True se parece válido, False caso contrário
    """
    if not data:
        logger.warning("Rótulo vazio")
        return False

    if len(data) > 10 * 1024 * 1024:  # 10MB
        logger.warning(f"Rótulo muito grande: {len(data)} bytes")
        return False

    try:
        text = data.decode('latin-1')
    except UnicodeDecodeError:
        logger.warning("Rótulo não é texto válido (latin-1)")
        return False

    # Verificar marcadores ZPL/TSPL
    has_zpl = '^XA' in text or '^xa' in text.lower()
    has_tspl = '~DG' in text or '~dg' in text.lower()

    if not (has_zpl or has_tspl):
        logger.warning("Rótulo não contém marcadores ZPL/TSPL válidos")
        return False

    return True


def validate_file_extension(filename: str) -> bool:
    """
    Valida se a extensão do arquivo é suportada.

    Args:
        filename: Nome do arquivo

    Returns:
        True se extensão é suportada
    """
    from pathlib import Path

    from .parser import LABEL_EXTENSIONS

    ext = Path(filename).suffix.lower()
    return ext in LABEL_EXTENSIONS


def estimate_label_size(data: bytes) -> str:
    """
    Estima tamanho legível do rótulo.

    Args:
        data: Bytes do rótulo

    Returns:
        String formatada (ex: "2.5 KB")
    """
    size = len(data)
    for unit in ['B', 'KB', 'MB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def count_zpl_objects(data: bytes) -> dict:
    """
    Conta objetos ZPL comuns no rótulo.

    Args:
        data: Bytes do rótulo

    Returns:
        Dict com contagem de objetos (text_fields, barcodes, images, etc)
    """
    try:
        text = data.decode('latin-1')
    except UnicodeDecodeError:
        return {}

    return {
        'text_fields': text.count('^FD'),
        'barcodes': text.count('^B'),
        'qr_codes': text.count('^BQ'),
        'images': text.count('~DG'),
        'lines': text.count('^A'),
        'boxes': text.count('^GB'),
    }
