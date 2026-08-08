"""
Testes para o módulo utils.
"""

from src.shopee_label_printer.utils import format_print_summary, sort_printers, truncate_text


class TestSortPrinters:
    """Testes para sort_printers."""

    def test_prefer_thermal(self):
        """Testa preferência por impressoras térmicas."""
        printers = ["HP LaserJet", "FY-1075 Thermal", "Canon Inkjet"]
        result = sort_printers(printers)
        assert result[0] == "FY-1075 Thermal"

    def test_multiple_thermal(self):
        """Testa com múltiplas impressoras térmicas."""
        printers = ["Normal", "Zebra Thermal", "FY-1075", "Other"]
        result = sort_printers(printers)
        # Ambas térmicas devem vir primeiro
        assert "Zebra" in result[0] or "FY" in result[0]
        assert "Zebra" in result[1] or "FY" in result[1]

    def test_no_thermal(self):
        """Testa quando não há impressora térmica."""
        printers = ["HP", "Canon", "Brother"]
        result = sort_printers(printers)
        assert len(result) == 3

    def test_dont_prefer_thermal(self):
        """Testa com preferência desativada."""
        printers = ["FY-1075", "HP"]
        result = sort_printers(printers, prefer_thermal=False)
        assert result == printers


class TestFormatPrintSummary:
    """Testes para format_print_summary."""

    def test_all_success(self):
        """Testa quando tudo imprime com sucesso."""
        title, msg = format_print_summary(5, 0)
        assert "sucesso" in title.lower()
        assert "5" in msg

    def test_with_failures(self):
        """Testa com falhas."""
        title, msg = format_print_summary(3, 2)
        assert "erro" in title.lower()
        assert "3" in msg
        assert "2" in msg

    def test_all_failures(self):
        """Testa quando tudo falha."""
        _title, msg = format_print_summary(0, 5)
        assert "5" in msg

    def test_none_selected(self):
        """Testa quando nenhuma etiqueta é selecionada."""
        title, _msg = format_print_summary(0, 0)
        assert "Nenhuma" in title


class TestTruncateText:
    """Testes para truncate_text."""

    def test_short_text(self):
        """Testa com texto curto."""
        text = "Short"
        result = truncate_text(text, 50)
        assert result == "Short"

    def test_long_text(self):
        """Testa com texto longo."""
        text = "X" * 100
        result = truncate_text(text, 50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_exact_length(self):
        """Testa com texto exatamente no limite."""
        text = "X" * 50
        result = truncate_text(text, 50)
        assert result == text

    def test_just_over_limit(self):
        """Testa com texto pouco acima do limite."""
        text = "X" * 51
        result = truncate_text(text, 50)
        assert "..." in result
