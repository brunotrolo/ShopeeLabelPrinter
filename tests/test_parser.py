"""
Testes para o módulo parser (extração e separação de etiquetas).
"""

import pytest
from pathlib import Path
from src.shopee_label_printer.parser import split_labels


def test_split_labels_single():
    """Testa separação com uma única etiqueta."""
    content = "^XA^FDTest^FS^XZ"
    result = split_labels(content)
    assert len(result) == 1
    assert result[0].strip() == "^XA^FDTest^FS^XZ"


def test_split_labels_multiple_xz():
    """Testa separação com múltiplas etiquetas ZPL."""
    content = "^XA^FDLabel1^FS^XZ^XA^FDLabel2^FS^XZ"
    result = split_labels(content)
    assert len(result) == 2
    assert "Label1" in result[0]
    assert "Label2" in result[1]


def test_split_labels_multiple_dg():
    """Testa separação com múltiplas etiquetas com imagem embutida."""
    content = "~DGImage1~DGImage2"
    result = split_labels(content)
    assert len(result) == 2


def test_split_labels_empty_blocks():
    """Testa que blocos vazios são removidos."""
    content = "^XA^FDTest^FS^XZ\n\n\n^XA^FDTest2^FS^XZ"
    result = split_labels(content)
    # Deve ter no mínimo as etiquetas válidas
    assert all(r.strip() for r in result)
