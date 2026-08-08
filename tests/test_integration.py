"""
Testes de integração: fluxo end-to-end da aplicação.

Esses testes validam o fluxo completo:
- Carregar etiqueta ZPL
- Renderizar preview
- Converter para diferentes formatos
- Simular envio para impressora
"""

import io
import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shopee_label_printer.converters import zpl_to_pdf, zpl_to_tspl
from shopee_label_printer.parser import load_labels_from_path
from shopee_label_printer.renderer import render_zpl


class TestE2ELoadAndRender:
    """Testes de carga e renderização end-to-end."""

    def test_load_single_zpl_file(self, tmp_path: Path) -> None:
        """Testa carregamento de arquivo ZPL único."""
        # Arrange
        zpl_file = tmp_path / "label.zpl"
        test_zpl = b"^XA^MMT^PQ1,0,1,Y^XZ"
        zpl_file.write_bytes(test_zpl)

        # Act
        labels = load_labels_from_path(str(zpl_file))

        # Assert
        assert len(labels) == 1
        assert labels[0][1] == test_zpl

    def test_load_multiple_zpl_files_from_folder(self, tmp_path: Path) -> None:
        """Testa carregamento de múltiplos arquivos ZPL de uma pasta."""
        # Arrange
        labels_dir = tmp_path / "labels"
        labels_dir.mkdir()
        test_zpl_1 = b"^XA^MMT^FT50,50^A0N,25^FDLabel1^FS^PQ1,0,1,Y^XZ"
        test_zpl_2 = b"^XA^MMT^FT50,50^A0N,25^FDLabel2^FS^PQ1,0,1,Y^XZ"

        (labels_dir / "label1.zpl").write_bytes(test_zpl_1)
        (labels_dir / "label2.txt").write_bytes(test_zpl_2)

        # Act
        labels = load_labels_from_path(str(labels_dir))

        # Assert
        assert len(labels) == 2

    def test_render_zpl_to_preview(self, sample_zpl_with_bitmap: bytes) -> None:
        """Testa renderização de ZPL para preview."""
        # Act
        render = render_zpl(sample_zpl_with_bitmap)

        # Assert
        assert render is not None
        assert render.width > 0
        assert render.height > 0
        assert len(render.pixels) > 0

    def test_render_zpl_produces_correct_dimensions(
        self, sample_zpl_with_bitmap: bytes
    ) -> None:
        """Testa que render produz dimensões corretas (203 DPI)."""
        # Act
        render = render_zpl(sample_zpl_with_bitmap)

        # Assert: Etiqueta padrão 100x150mm em 203 DPI
        expected_width = 812  # 4" * 203
        expected_height = 1218  # 6" * 203
        assert render.width == expected_width
        assert render.height == expected_height


class TestE2EPrintFlow:
    """Testes de fluxo de impressão completo."""

    def test_convert_zpl_to_tspl(self, sample_zpl_with_bitmap: bytes) -> None:
        """Testa conversão ZPL → TSPL."""
        # Act
        tspl_data = zpl_to_tspl(
            sample_zpl_with_bitmap, render_zpl, boost_level="desligado"
        )

        # Assert
        assert isinstance(tspl_data, bytes)
        assert b"SIZE" in tspl_data  # Header TSPL
        assert b"BITMAP" in tspl_data
        assert b"PRINT" in tspl_data

    def test_convert_zpl_to_tspl_with_boost(self, sample_zpl_with_bitmap: bytes) -> None:
        """Testa conversão com reforço de impressão."""
        # Act
        tspl_data = zpl_to_tspl(
            sample_zpl_with_bitmap, render_zpl, boost_level="leve"
        )

        # Assert
        assert b"DENSITY 12" in tspl_data or b"SPEED 2" in tspl_data

    def test_convert_zpl_to_tspl_custom_boost_valid(
        self, sample_zpl_with_bitmap: bytes
    ) -> None:
        """Testa conversão com reforço customizado válido."""
        # Act
        tspl_data = zpl_to_tspl(
            sample_zpl_with_bitmap,
            render_zpl,
            boost_level="customizado",
            custom_density=10,
            custom_speed=2,
        )

        # Assert
        assert b"DENSITY 10" in tspl_data
        assert b"SPEED 2" in tspl_data

    def test_convert_zpl_to_tspl_custom_boost_invalid_density(
        self, sample_zpl_with_bitmap: bytes
    ) -> None:
        """Testa conversão com density fora do range válido."""
        from shopee_label_printer.converters import ConversionError

        # Act & Assert
        with pytest.raises(ConversionError) as exc_info:
            zpl_to_tspl(
                sample_zpl_with_bitmap,
                render_zpl,
                boost_level="customizado",
                custom_density=20,  # Inválido: deve ser 0-15
                custom_speed=2,
            )
        assert "density deve estar entre 0-15" in str(exc_info.value)

    def test_convert_zpl_to_pdf(self, sample_zpl_with_bitmap: bytes) -> None:
        """Testa conversão ZPL → PDF."""
        # Act
        pdf_data = zpl_to_pdf(sample_zpl_with_bitmap, render_zpl)

        # Assert
        assert isinstance(pdf_data, bytes)
        assert pdf_data.startswith(b"%PDF")  # PDF header

    def test_convert_zpl_to_pdf_with_save(
        self, sample_zpl_with_bitmap: bytes, tmp_path: Path
    ) -> None:
        """Testa conversão ZPL → PDF com salvamento em disco."""
        # Arrange
        output_file = tmp_path / "label.pdf"

        # Act
        pdf_data = zpl_to_pdf(sample_zpl_with_bitmap, render_zpl, str(output_file))

        # Assert
        assert output_file.exists()
        assert output_file.read_bytes() == pdf_data
        assert len(pdf_data) > 100


class TestE2EErrorHandling:
    """Testes de tratamento de erros em fluxos completos."""

    def test_load_nonexistent_file_raises_error(self, tmp_path: Path) -> None:
        """Testa que arquivo inexistente lança erro."""
        from shopee_label_printer.parser import ParserError

        nonexistent = tmp_path / "does_not_exist.zpl"

        with pytest.raises(ParserError):
            load_labels_from_path(str(nonexistent))


class TestE2ELogging:
    """Testes que verificam que logging está funcionando."""

    def test_converstion_logs_progress(
        self, sample_zpl_with_bitmap: bytes, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Testa que conversão registra milestones de progresso."""
        # Arrange
        caplog.set_level(logging.INFO)

        # Act
        zpl_to_tspl(sample_zpl_with_bitmap, render_zpl, boost_level="desligado")

        # Assert
        log_messages = [record.message for record in caplog.records]
        assert any("Iniciando conversão ZPL → TSPL" in msg for msg in log_messages)
        assert any("renderizada" in msg for msg in log_messages)
        assert any("Conversão concluída" in msg for msg in log_messages)

    def test_pdf_conversion_logs_progress(
        self, sample_zpl_with_bitmap: bytes, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Testa que conversão PDF registra milestones."""
        # Arrange
        caplog.set_level(logging.INFO)

        # Act
        zpl_to_pdf(sample_zpl_with_bitmap, render_zpl)

        # Assert
        log_messages = [record.message for record in caplog.records]
        assert any("Iniciando conversão ZPL → PDF" in msg for msg in log_messages)
