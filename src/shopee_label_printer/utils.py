"""
Utilidades variadas.
"""

import logging

logger = logging.getLogger(__name__)


def sort_printers(printer_list: list[str], prefer_thermal: bool = True) -> list[str]:
    """
    Ordena lista de impressoras, colocando impressoras térmicas em primeiro.

    Args:
        printer_list: Lista de nomes de impressoras
        prefer_thermal: Se True, coloca impressoras térmicas primeiro

    Returns:
        Lista ordenada
    """
    if not prefer_thermal:
        return printer_list

    thermal_keywords = ['fy', 'térm', 'thermal', 'label', 'zebra', 'honeywell']

    thermal = []
    other = []

    for printer in printer_list:
        if any(keyword in printer.lower() for keyword in thermal_keywords):
            thermal.append(printer)
        else:
            other.append(printer)

    return thermal + other


def format_print_summary(ok: int, fail: int) -> tuple[str, str]:
    """
    Formata resumo de impressão.

    Args:
        ok: Número de etiquetas impressas com sucesso
        fail: Número de etiquetas que falharam

    Returns:
        Tupla (título, mensagem)
    """
    if ok == 0 and fail == 0:
        return "Nenhuma etiqueta", "Nenhuma etiqueta foi selecionada."

    title = "Concluído com sucesso" if fail == 0 else "Impressão com erros"

    msg = f"{ok} etiqueta(s) enviada(s) com sucesso"
    if fail:
        msg += f"\n{fail} falharam"

    return title, msg


def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Trunca texto se for muito longo.

    Args:
        text: Texto a truncar
        max_length: Comprimento máximo

    Returns:
        Texto truncado (com "..." se foi cortado)
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
