"""
Fixtures compartilhadas para testes.

Este arquivo é carregado automaticamente pelo pytest e disponibiliza
fixtures que podem ser usadas por qualquer teste.
"""

import pytest


@pytest.fixture
def sample_zpl_label() -> bytes:
    """
    Retorna um ZPL mínimo válido para testes renderização.

    Este ZPL é apenas para renderização (teste de parse/render).
    Para testes de conversão (TSPL/PDF), use sample_zpl_with_bitmap.
    """
    return (
        b"^XA"
        b"^MMT"
        b"^PON"
        b"^LH0,0"
        b"^LS0"
        b"^PQ1,0,1,Y^XZ"
    )


@pytest.fixture
def sample_zpl_with_bitmap() -> bytes:
    """
    Retorna um ZPL com bitmap embutido (seguro para converter para TSPL/PDF).

    Bitmap 100x50 pixels com padrão simples para testes de conversão.
    """
    # Bitmap mínimo: 100x50 pixels = ~625 bytes quando empacotado
    # Usando ~DG para armazenar na memória da impressora
    return (
        b"^XA"
        b"^MMT"
        b"^PON"
        b"^LH0,0"
        b"^LS0"
        # Bitmap simples em formato ^GFA (ASCII hex)
        # 100 pixels de largura, 50 pixels de altura
        b"^GFA,625,625,13,"
        # Usar padrão repetitivo simples (linha branca, linha preta, etc)
        + b"00" * 650  # Muitos zeros para criar bitmap simplificado
        + b"^XZ"
    )


@pytest.fixture
def sample_zpl_with_text() -> bytes:
    """Retorna um ZPL com texto adicional para testes."""
    return (
        b"^XA"
        b"^MMT"
        b"^PON"
        b"^LH0,0"
        b"^LS0"
        b"^FT50,50^A0N,25^FDTest Label^FS"
        b"^BY2,3,50^FT50,100^BCN,,Y,N"
        b"^FD123456789012^FS"
        b"^PQ1,0,1,Y^XZ"
    )


@pytest.fixture
def tspl_boost_levels() -> dict:
    """Retorna os níveis de reforço TSPL para testes."""
    return {
        "desligado": (None, None),
        "leve": (12, 2),
        "medio": (15, 2),
        "forte": (15, 1),
    }
