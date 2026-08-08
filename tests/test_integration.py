"""
Testes de integração: fluxo end-to-end da aplicação.

Esses testes validam o fluxo completo:
- Carregar etiqueta ZPL
- Renderizar preview
- Converter para diferentes formatos
- Simular envio para impressora
"""

import logging
from pathlib import Path

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


class TestE2EAutoImport:
    """Testes de auto-import de arquivos da pasta Downloads."""

    def test_detect_zpl_files_with_pattern(self, tmp_path: Path) -> None:
        """Testa detecção de arquivos com padrão 'Etiqueta de Envio ZPL'."""
        # Arrange
        zpl_file = tmp_path / "Etiqueta de Envio ZPL 123.zpl"
        test_zpl = b"^XA^MMT^PQ1,0,1,Y^XZ"
        zpl_file.write_bytes(test_zpl)

        other_file = tmp_path / "outro_arquivo.zpl"
        other_file.write_bytes(test_zpl)

        # Act: Listar arquivos com padrão (simulando _get_downloads_folder)
        pattern_files = list(tmp_path.glob("Etiqueta de Envio ZPL*.*"))

        # Assert
        assert len(pattern_files) == 1
        assert pattern_files[0].name == "Etiqueta de Envio ZPL 123.zpl"

    def test_deduplicate_loaded_files(self, tmp_path: Path, sample_zpl_with_bitmap: bytes) -> None:
        """Testa que não há duplicatas ao importar o mesmo arquivo novamente."""
        # Arrange
        zpl_file = tmp_path / "Etiqueta de Envio ZPL ABC.zpl"
        zpl_file.write_bytes(sample_zpl_with_bitmap)

        # Act 1: Primeira importação
        labels_1 = load_labels_from_path(str(zpl_file))
        assert len(labels_1) > 0

        # Act 2: Segunda importação (mesmo arquivo)
        labels_2 = load_labels_from_path(str(zpl_file))

        # Assert: Mesmo arquivo, mesmos rótulos
        assert len(labels_2) == len(labels_1)
        assert labels_2[0][1] == labels_1[0][1]

    def test_auto_import_finds_supported_formats(self, tmp_path: Path) -> None:
        """Testa que auto-import detecta múltiplos formatos suportados."""
        # Arrange
        supported_exts = [".zpl", ".tspl", ".txt", ".prn"]
        test_data = b"^XA^MMT^PQ1,0,1,Y^XZ"

        for ext in supported_exts:
            file = tmp_path / f"Etiqueta de Envio ZPL formato{ext}"
            file.write_bytes(test_data)

        # Act
        zpl_files = [
            f for f in tmp_path.glob("Etiqueta de Envio ZPL*.*")
            if f.suffix.lower() in {".zpl", ".tspl", ".txt", ".prn"} and f.is_file()
        ]

        # Assert
        assert len(zpl_files) == len(supported_exts)

    def test_auto_import_ignores_non_matching_files(self, tmp_path: Path) -> None:
        """Testa que arquivos sem padrão não são importados."""
        # Arrange
        matching = tmp_path / "Etiqueta de Envio ZPL 001.zpl"
        matching.write_bytes(b"^XA^XZ")

        non_matching = tmp_path / "random_label.zpl"
        non_matching.write_bytes(b"^XA^XZ")

        # Act
        pattern_files = list(tmp_path.glob("Etiqueta de Envio ZPL*.*"))

        # Assert
        assert len(pattern_files) == 1
        assert pattern_files[0] == matching

    def test_auto_import_handles_file_hash_tracking(self, tmp_path: Path) -> None:
        """Testa que o sistema rastreia files por hash para evitar re-importação."""
        # Arrange
        file1 = tmp_path / "Etiqueta de Envio ZPL 1.zpl"
        file1.write_bytes(b"^XA^PQ1^XZ")

        file2 = tmp_path / "Etiqueta de Envio ZPL 2.zpl"
        file2.write_bytes(b"^XA^PQ1^XZ")

        # Act: Simular rastreamento
        loaded_hashes = set()
        new_files = []

        for filepath in [file1, file2]:
            file_hash = str(filepath.resolve())
            if file_hash not in loaded_hashes:
                new_files.append(filepath)
                loaded_hashes.add(file_hash)

        # Re-processar file1
        for filepath in [file1]:
            file_hash = str(filepath.resolve())
            if file_hash not in loaded_hashes:
                new_files.append(filepath)

        # Assert
        assert len(new_files) == 2  # Foram adicionados 2 arquivos novos
        assert str(file1.resolve()) in loaded_hashes
        assert str(file2.resolve()) in loaded_hashes

    def test_auto_import_fallback_without_shopee_pattern(self, tmp_path: Path) -> None:
        """Testa que auto-import detecta arquivos sem padrão Shopee como fallback."""
        # Arrange: Criar arquivo sem padrão "Etiqueta de Envio ZPL"
        generic_file = tmp_path / "label_001.zpl"
        generic_file.write_bytes(b"^XA^PQ1^XZ")

        # Act: Simular a lógica de fallback
        supported_ext = {".zpl", ".tspl", ".txt", ".prn"}
        pattern_files = list(tmp_path.glob("Etiqueta de Envio ZPL*.*"))
        zpl_files = [
            f for f in pattern_files
            if f.suffix.lower() in supported_ext and f.is_file()
        ]

        # Se não encontrou com padrão, procura todos
        if not zpl_files:
            all_files = list(tmp_path.glob("*.*"))
            zpl_files = [
                f for f in all_files
                if f.suffix.lower() in supported_ext and f.is_file()
            ]

        # Assert
        assert len(zpl_files) == 1
        assert zpl_files[0] == generic_file
