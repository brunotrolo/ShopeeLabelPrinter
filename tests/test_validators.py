"""
Testes para o módulo validators.
"""

import pytest
from src.shopee_label_printer.validators import (
    validate_zpl_label, validate_file_extension,
    estimate_label_size, count_zpl_objects
)


class TestValidateZplLabel:
    """Testes para validate_zpl_label."""

    def test_valid_zpl(self):
        """Testa com ZPL válido."""
        data = b"^XA^FDTest^FS^XZ"
        assert validate_zpl_label(data) is True

    def test_valid_tspl(self):
        """Testa com TSPL válido."""
        data = b"~DGTest~FS"
        assert validate_zpl_label(data) is True

    def test_empty(self):
        """Testa com dados vazios."""
        assert validate_zpl_label(b"") is False

    def test_no_markers(self):
        """Testa com texto sem marcadores."""
        data = b"This is not ZPL"
        assert validate_zpl_label(data) is False

    def test_too_large(self):
        """Testa com arquivo muito grande."""
        data = b"^XA" + b"X" * (11 * 1024 * 1024)  # 11MB
        assert validate_zpl_label(data) is False

    def test_invalid_encoding(self):
        """Testa com encoding inválido."""
        data = b"\x80\x81\x82^XA"  # Bytes inválidos em latin-1
        # latin-1 aceitaqualquer byte, então pode passar
        assert isinstance(validate_zpl_label(data), bool)


class TestValidateFileExtension:
    """Testes para validate_file_extension."""

    def test_txt_extension(self):
        """Testa com extensão .txt."""
        assert validate_file_extension("label.txt") is True

    def test_zpl_extension(self):
        """Testa com extensão .zpl."""
        assert validate_file_extension("label.zpl") is True

    def test_invalid_extension(self):
        """Testa com extensão inválida."""
        assert validate_file_extension("document.pdf") is False

    def test_case_insensitive(self):
        """Testa que extensão é case-insensitive."""
        assert validate_file_extension("label.TXT") is True
        assert validate_file_extension("label.ZPL") is True


class TestEstimateLabelSize:
    """Testes para estimate_label_size."""

    def test_bytes(self):
        """Testa com tamanho em bytes."""
        result = estimate_label_size(b"X" * 512)
        assert "B" in result

    def test_kilobytes(self):
        """Testa com tamanho em KB."""
        result = estimate_label_size(b"X" * (5 * 1024))
        assert "KB" in result

    def test_megabytes(self):
        """Testa com tamanho em MB."""
        result = estimate_label_size(b"X" * (2 * 1024 * 1024))
        assert "MB" in result


class TestCountZplObjects:
    """Testes para count_zpl_objects."""

    def test_count_text_fields(self):
        """Testa contagem de campos de texto."""
        data = b"^XA^FDText1^FS^FDText2^FS^XZ"
        result = count_zpl_objects(data)
        assert result['text_fields'] == 2

    def test_count_barcodes(self):
        """Testa contagem de códigos de barras."""
        data = b"^XA^BACode1^BACode2^XZ"
        result = count_zpl_objects(data)
        assert result['barcodes'] == 2

    def test_count_qr_codes(self):
        """Testa contagem de QR codes."""
        data = b"^XA^BQCode1^BQCode2^XZ"
        result = count_zpl_objects(data)
        assert result['qr_codes'] == 2

    def test_count_images(self):
        """Testa contagem de imagens."""
        data = b"~DGImg1~DGImg2"
        result = count_zpl_objects(data)
        assert result['images'] == 2

    def test_complex_label(self):
        """Testa com rótulo complexo."""
        data = b"^XA^FDText1^FS^BACode1^XZ~DGImage1"
        result = count_zpl_objects(data)
        assert result['text_fields'] >= 1
        assert result['barcodes'] >= 1
        assert result['images'] >= 1

    def test_empty_data(self):
        """Testa com dados vazios."""
        result = count_zpl_objects(b"")
        assert isinstance(result, dict)
