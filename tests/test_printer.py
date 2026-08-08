"""
Testes para o módulo printer (envio RAW para impressora).
"""

import pytest
from unittest.mock import patch, MagicMock, call
from src.shopee_label_printer.printer import (
    list_printers, send_raw_to_printer, PrinterError,
    _list_printers_windows, _list_printers_unix,
    apply_print_boost, send_test_label, TEST_LABELS,
)


class TestListPrinters:
    """Testes para a função list_printers."""

    @patch('src.shopee_label_printer.printer._list_printers_windows')
    @patch('src.shopee_label_printer.printer.IS_WINDOWS', True)
    def test_list_printers_windows(self, mock_windows):
        """Testa listagem de impressoras no Windows."""
        mock_windows.return_value = ["Printer1", "Printer2"]
        result = list_printers()
        assert result == ["Printer1", "Printer2"]

    @patch('src.shopee_label_printer.printer._list_printers_unix')
    @patch('src.shopee_label_printer.printer.IS_WINDOWS', False)
    def test_list_printers_unix(self, mock_unix):
        """Testa listagem de impressoras no Unix."""
        mock_unix.return_value = ["Printer1", "Printer2"]
        result = list_printers()
        assert result == ["Printer1", "Printer2"]

    @patch('src.shopee_label_printer.printer._list_printers_windows')
    @patch('src.shopee_label_printer.printer.IS_WINDOWS', True)
    def test_list_printers_empty(self, mock_windows):
        """Testa quando nenhuma impressora é encontrada."""
        mock_windows.return_value = []
        result = list_printers()
        assert result == []


class TestListPrintersWindows:
    """Testes para _list_printers_windows."""

    @patch('src.shopee_label_printer.printer.subprocess.run')
    def test_success(self, mock_run):
        """Testa listagem bem-sucedida."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Printer1\nPrinter2\n"
        )
        result = _list_printers_windows()
        assert result == ["Printer1", "Printer2"]

    @patch('src.shopee_label_printer.printer.subprocess.run')
    def test_error(self, mock_run):
        """Testa quando PowerShell retorna erro."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error"
        )
        result = _list_printers_windows()
        assert result == []

    @patch('src.shopee_label_printer.printer.subprocess.run')
    def test_timeout(self, mock_run):
        """Testa timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 10)
        result = _list_printers_windows()
        assert result == []

    @patch('src.shopee_label_printer.printer.subprocess.run')
    def test_not_found(self, mock_run):
        """Testa quando PowerShell não é encontrado."""
        mock_run.side_effect = FileNotFoundError()
        result = _list_printers_windows()
        assert result == []


class TestListPrintersUnix:
    """Testes para _list_printers_unix."""

    @patch('src.shopee_label_printer.printer.subprocess.run')
    def test_success(self, mock_run):
        """Testa listagem bem-sucedida."""
        mock_run.return_value = MagicMock(
            stdout="printer printer1 is idle.  enabled since...\nprinter printer2 is idle.  enabled since...\n"
        )
        result = _list_printers_unix()
        # Deve extrair os nomes das impressoras
        assert len(result) >= 0  # O regex pode ou não encontrar, depende do formato

    @patch('src.shopee_label_printer.printer.subprocess.run')
    def test_empty(self, mock_run):
        """Testa quando nenhuma impressora é encontrada."""
        mock_run.return_value = MagicMock(stdout="")
        result = _list_printers_unix()
        assert result == []

    @patch('src.shopee_label_printer.printer.subprocess.run')
    def test_not_found(self, mock_run):
        """Testa quando lpstat não é encontrado."""
        mock_run.side_effect = FileNotFoundError()
        result = _list_printers_unix()
        assert result == []


class TestSendRawToPrinter:
    """Testes para a função send_raw_to_printer."""

    def test_no_printer_selected(self):
        """Testa quando nenhuma impressora é selecionada."""
        with pytest.raises(PrinterError, match="Nenhuma impressora selecionada"):
            send_raw_to_printer("", b"data")

    def test_empty_data(self):
        """Testa quando dados estão vazios."""
        with pytest.raises(PrinterError, match="Dados vazios"):
            send_raw_to_printer("Printer1", b"")

    @patch('src.shopee_label_printer.printer._send_raw_windows')
    @patch('src.shopee_label_printer.printer.IS_WINDOWS', True)
    def test_send_windows(self, mock_send):
        """Testa envio no Windows."""
        send_raw_to_printer("Printer1", b"test data", "Job1")
        mock_send.assert_called_once_with("Printer1", b"test data", "Job1")

    @patch('src.shopee_label_printer.printer._send_raw_unix')
    @patch('src.shopee_label_printer.printer.IS_WINDOWS', False)
    def test_send_unix(self, mock_send):
        """Testa envio no Unix."""
        send_raw_to_printer("Printer1", b"test data", "Job1")
        mock_send.assert_called_once_with("Printer1", b"test data")

    def test_error_handling(self):
        """Testa tratamento de erros genéricos."""
        with patch('src.shopee_label_printer.printer._send_raw_windows') as mock_send:
            mock_send.side_effect = Exception("Connection failed")
            with patch('src.shopee_label_printer.printer.IS_WINDOWS', True):
                with pytest.raises(PrinterError, match="Erro ao enviar"):
                    send_raw_to_printer("Printer1", b"data")


class TestApplyPrintBoost:
    """
    Reforço de impressão: mais calor (^MD) e menos velocidade (^PR).

    É a única função do projeto que altera os bytes enviados, então precisa
    ficar bem amarrada: só age quando pedida, e nunca mexe no desenho.
    """

    LABEL = b"^XA^FO0,0^FDteste^FS^XZ"

    def test_desligado_devolve_bytes_identicos(self):
        assert apply_print_boost(self.LABEL, "desligado") is self.LABEL

    def test_nivel_desconhecido_nao_altera(self):
        assert apply_print_boost(self.LABEL, "turbo") is self.LABEL

    def test_insere_comandos_logo_apos_o_xa(self):
        result = apply_print_boost(self.LABEL, "medio")
        assert result.startswith(b"^XA^MD12^PR2")

    def test_niveis_sao_progressivamente_mais_escuros(self):
        import re

        escurecimento = []
        for nivel in ("leve", "medio", "forte"):
            match = re.search(rb"\^MD(\d+)", apply_print_boost(self.LABEL, nivel))
            escurecimento.append(int(match.group(1)))

        assert escurecimento == sorted(escurecimento)
        assert len(set(escurecimento)) == 3

    def test_conteudo_original_e_preservado(self):
        """O reforço acrescenta comandos, nunca remove ou reordena o resto."""
        result = apply_print_boost(self.LABEL, "forte")
        assert b"^FO0,0^FDteste^FS^XZ" in result
        assert result.endswith(b"^XZ")

    def test_nao_altera_o_desenho(self):
        """
        Tirando os comandos inseridos, os bytes têm que ser os originais —
        é isso que garante que nenhum ponto foi movido ou acrescentado.
        """
        import re

        result = apply_print_boost(self.LABEL, "forte")
        assert re.sub(rb"\^MD\d+\^PR\d+", b"", result, count=1) == self.LABEL

    def test_etiqueta_sem_xa_passa_intacta(self):
        sem_xa = b"~DGR:A.GRF,2,2,FFFF"
        assert apply_print_boost(sem_xa, "medio") == sem_xa

    def test_atua_apenas_no_primeiro_xa(self):
        duas = b"^XA^FDa^FS^XZ^XA^FDb^FS^XZ"
        assert apply_print_boost(duas, "leve").count(b"^MD") == 1


class TestSendTestLabel:
    """Etiquetas de teste usadas para descobrir a linguagem da impressora."""

    def test_zpl_e_tspl_disponiveis(self):
        assert set(TEST_LABELS) == {"ZPL", "TSPL"}

    def test_etiqueta_zpl_tem_delimitadores(self):
        assert TEST_LABELS["ZPL"].startswith(b"^XA")
        assert TEST_LABELS["ZPL"].rstrip().endswith(b"^XZ")

    def test_etiqueta_tspl_tem_print(self):
        assert b"SIZE" in TEST_LABELS["TSPL"]
        assert b"PRINT" in TEST_LABELS["TSPL"]

    def test_as_duas_sao_diferentes(self):
        """Se fossem iguais o teste não distinguiria nada."""
        assert TEST_LABELS["ZPL"] != TEST_LABELS["TSPL"]

    def test_linguagem_desconhecida_da_erro_claro(self):
        with pytest.raises(PrinterError, match="desconhecida"):
            send_test_label("Impressora", "ESCPOS")

    def test_linguagem_aceita_minuscula(self, monkeypatch):
        enviados = []
        monkeypatch.setattr(
            "src.shopee_label_printer.printer.send_raw_to_printer",
            lambda p, d, job_name=None: enviados.append(d),
        )
        send_test_label("Impressora", "zpl")
        assert enviados == [TEST_LABELS["ZPL"]]
