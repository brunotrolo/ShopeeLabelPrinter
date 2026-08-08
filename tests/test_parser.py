"""
Testes para o módulo parser (extração e separação de etiquetas).
"""

import pytest
import os
import tempfile
import zipfile
from pathlib import Path
from src.shopee_label_printer.parser import (
    split_labels, find_label_files, extract_zip_to_temp,
    load_labels_from_path, ParserError
)


class TestSplitLabels:
    """Testes para a função split_labels."""

    def test_split_single_label(self):
        """Testa separação com uma única etiqueta."""
        content = "^XA^FDTest^FS^XZ"
        result = split_labels(content)
        assert len(result) == 1
        assert result[0].strip() == "^XA^FDTest^FS^XZ"

    def test_split_multiple_zpl(self):
        """Testa separação com múltiplas etiquetas ZPL."""
        content = "^XA^FDLabel1^FS^XZ^XA^FDLabel2^FS^XZ"
        result = split_labels(content)
        assert len(result) == 2
        assert "Label1" in result[0]
        assert "Label2" in result[1]

    def test_split_multiple_dg(self):
        """Testa separação com múltiplas etiquetas com imagem embutida."""
        content = "~DGImage1~DGImage2"
        result = split_labels(content)
        assert len(result) == 2

    def test_split_empty_blocks(self):
        """Testa que blocos vazios são removidos."""
        content = "^XA^FDTest^FS^XZ\n\n\n^XA^FDTest2^FS^XZ"
        result = split_labels(content)
        assert all(r.strip() for r in result)

    def test_split_no_markers(self):
        """Testa com conteúdo que não tem marcadores."""
        content = "Some random text"
        result = split_labels(content)
        assert len(result) == 1

    def test_label_with_embedded_image_is_not_split(self):
        """
        Etiqueta única com imagem embutida: o ~DG fica DENTRO do ^XA...^XZ.
        Cortar no ~DG separava o cabeçalho da imagem e criava uma etiqueta
        fantasma em branco, que ia parar na impressora no 'Imprimir todas'.
        """
        content = "^XA^PW812^LL1218~DGR:IMG.GRF,4,2,FFFF0000^FO0,0^XGR:IMG.GRF,1,1^FS^XZ"
        result = split_labels(content)
        assert len(result) == 1
        assert result[0].startswith("^XA")
        assert "~DG" in result[0]

    def test_two_labels_with_embedded_images(self):
        """Duas etiquetas com imagem: divide em 2, cada uma com seu cabeçalho."""
        one = "^XA^PW812^LL1218~DGR:A.GRF,2,2,FFFF^FO0,0^XGR:A.GRF,1,1^FS^XZ"
        result = split_labels(one + one)
        assert len(result) == 2
        assert all(part.startswith("^XA") and "~DG" in part for part in result)

    def test_dg_only_file_still_splits_on_dg(self):
        """Arquivo sem ^XA nenhum: aí sim o ~DG é o delimitador."""
        result = split_labels("~DGImage1~DGImage2")
        assert len(result) == 2


class TestFindLabelFiles:
    """Testes para a função find_label_files."""

    def test_find_txt_files(self):
        """Testa busca de arquivos .txt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Criar alguns arquivos
            Path(tmpdir, "label1.txt").write_text("test")
            Path(tmpdir, "label2.zpl").write_text("test")
            Path(tmpdir, "readme.md").write_text("test")

            result = find_label_files(tmpdir)
            assert len(result) == 2
            assert any("label1.txt" in f for f in result)
            assert any("label2.zpl" in f for f in result)

    def test_find_nested_files(self):
        """Testa busca recursiva."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir, "subdir")
            subdir.mkdir()
            Path(subdir, "label.txt").write_text("test")

            result = find_label_files(tmpdir)
            assert len(result) == 1

    def test_find_no_files(self):
        """Testa quando nenhum arquivo é encontrado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "readme.md").write_text("test")
            result = find_label_files(tmpdir)
            assert len(result) == 0

    def test_find_nonexistent_dir(self):
        """Testa com diretório que não existe."""
        with pytest.raises(ParserError):
            find_label_files("/nonexistent/path")


class TestExtractZip:
    """Testes para a função extract_zip_to_temp."""

    def test_extract_valid_zip(self):
        """Testa extração de ZIP válido."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Criar ZIP
            zip_path = Path(tmpdir, "test.zip")
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr("label1.txt", "^XA^FDTest^FS^XZ")

            result = extract_zip_to_temp(str(zip_path))
            assert os.path.isdir(result)
            assert os.path.exists(os.path.join(result, "label1.txt"))

    def test_extract_nonexistent_file(self):
        """Testa com arquivo que não existe."""
        with pytest.raises(ParserError, match="não encontrado"):
            extract_zip_to_temp("/nonexistent/file.zip")

    def test_extract_invalid_zip(self):
        """Testa com arquivo que não é um ZIP válido."""
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_path = Path(tmpdir, "notazip.txt")
            invalid_path.write_text("This is not a zip")

            with pytest.raises(ParserError, match="não é um ZIP válido"):
                extract_zip_to_temp(str(invalid_path))


class TestLoadLabelsFromPath:
    """Testes para a função load_labels_from_path."""

    def test_load_from_single_file(self):
        """Testa carregamento de arquivo único."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir, "label.txt")
            file_path.write_text("^XA^FDTest^FS^XZ")

            result = load_labels_from_path(str(file_path))
            assert len(result) == 1
            assert result[0][0] == "label.txt"
            assert b"^XA^FDTest^FS^XZ" in result[0][1]

    def test_load_from_folder(self):
        """Testa carregamento de pasta."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "label1.txt").write_text("^XA^FD1^FS^XZ")
            Path(tmpdir, "label2.txt").write_text("^XA^FD2^FS^XZ")

            result = load_labels_from_path(tmpdir)
            assert len(result) == 2

    def test_load_from_zip(self):
        """Testa carregamento de ZIP."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir, "test.zip")
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr("label1.txt", "^XA^FD1^FS^XZ")
                zf.writestr("label2.txt", "^XA^FD2^FS^XZ")

            result = load_labels_from_path(str(zip_path))
            assert len(result) == 2

    def test_load_nonexistent_path(self):
        """Testa com caminho que não existe."""
        with pytest.raises(ParserError, match="não existe"):
            load_labels_from_path("/nonexistent/path")

    def test_load_empty_folder(self):
        """Testa com pasta vazia."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ParserError, match="Nenhuma etiqueta encontrada"):
                load_labels_from_path(tmpdir)

    def test_load_multiple_labels_in_file(self):
        """Testa carregamento de múltiplas etiquetas no mesmo arquivo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir, "labels.txt")
            file_path.write_text("^XA^FD1^FS^XZ^XA^FD2^FS^XZ^XA^FD3^FS^XZ")

            result = load_labels_from_path(str(file_path))
            # Deve ter 3 etiquetas da mesmo arquivo
            assert len(result) == 3
            assert "etiqueta 1/3" in result[0][0]
            assert "etiqueta 2/3" in result[1][0]
            assert "etiqueta 3/3" in result[2][0]

    def test_load_empty_file(self):
        """Testa com arquivo vazio."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "empty.txt").write_text("")
            with pytest.raises(ParserError):
                load_labels_from_path(tmpdir)
