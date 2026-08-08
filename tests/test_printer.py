"""
Testes para o módulo printer (envio RAW para impressora).
"""

import pytest
from unittest.mock import patch, MagicMock
from src.shopee_label_printer.printer import list_printers


@patch('src.shopee_label_printer.printer.subprocess.run')
def test_list_printers_windows(mock_run):
    """Testa listagem de impressoras no Windows."""
    mock_run.return_value = MagicMock(stdout="Printer1\nPrinter2\n")

    with patch('src.shopee_label_printer.printer.IS_WINDOWS', True):
        with patch('src.shopee_label_printer.printer.platform.system', return_value='Windows'):
            result = list_printers()
            # Deve ter retornado algo
            assert isinstance(result, list)


@patch('src.shopee_label_printer.printer.subprocess.run')
def test_list_printers_empty(mock_run):
    """Testa quando nenhuma impressora é encontrada."""
    mock_run.return_value = MagicMock(stdout="")

    with patch('src.shopee_label_printer.printer.IS_WINDOWS', True):
        with patch('src.shopee_label_printer.printer.platform.system', return_value='Windows'):
            result = list_printers()
            assert isinstance(result, list)
