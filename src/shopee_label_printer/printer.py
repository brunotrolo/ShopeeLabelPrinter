"""
Módulo de impressão: envio RAW para impressora térmica.
Com tratamento robusto de erros.
"""

import re
import platform
import subprocess
import ctypes
import logging
from ctypes import wintypes
from typing import List

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    winspool = ctypes.WinDLL("winspool.drv")

    class _DOC_INFO_1(ctypes.Structure):
        _fields_ = [
            ("pDocName", wintypes.LPWSTR),
            ("pOutputFile", wintypes.LPWSTR),
            ("pDatatype", wintypes.LPWSTR),
        ]


class PrinterError(Exception):
    """Erro na comunicação com impressora."""
    pass


def list_printers() -> List[str]:
    """
    Lista as impressoras disponíveis no sistema.

    Returns:
        Lista de nomes de impressoras
    """
    try:
        if IS_WINDOWS:
            return _list_printers_windows()
        else:
            return _list_printers_unix()
    except Exception as e:
        logger.error(f"Erro ao listar impressoras: {str(e)}")
        return []


def _list_printers_windows() -> List[str]:
    """Lista impressoras no Windows via PowerShell."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Printer | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            logger.debug(f"Encontradas {len(names)} impressora(s)")
            return names
        else:
            logger.warning(f"PowerShell retornou erro: {result.stderr}")
            return []
    except subprocess.TimeoutExpired:
        logger.error("Timeout ao listar impressoras")
        return []
    except FileNotFoundError:
        logger.error("PowerShell não encontrado")
        return []


def _list_printers_unix() -> List[str]:
    """Lista impressoras no macOS/Linux via lpstat."""
    try:
        out = subprocess.run(["lpstat", "-p"], capture_output=True, text=True)
        names = re.findall(r"printer (\S+)", out.stdout)
        logger.debug(f"Encontradas {len(names)} impressora(s)")
        return names
    except FileNotFoundError:
        logger.error("lpstat não encontrado (CUPS não instalado?)")
        return []


def send_raw_to_printer(printer_name: str, data: bytes, job_name: str = "Etiqueta Shopee"):
    """
    Envia bytes crus para a impressora, sem reprocessar/reamostrar nada.

    Args:
        printer_name: Nome da impressora
        data: Bytes da etiqueta (ZPL/TSPL)
        job_name: Nome do trabalho de impressão

    Raises:
        PrinterError: Se não conseguir imprimir
    """
    if not printer_name:
        raise PrinterError("Nenhuma impressora selecionada")

    if not data:
        raise PrinterError("Dados vazios para imprimir")

    try:
        if IS_WINDOWS:
            _send_raw_windows(printer_name, data, job_name)
        else:
            _send_raw_unix(printer_name, data)

        logger.info(f"Etiqueta enviada para {printer_name}: {job_name}")

    except PrinterError:
        raise
    except Exception as e:
        raise PrinterError(f"Erro ao enviar para impressora: {str(e)}")


def _send_raw_windows(printer_name: str, data: bytes, job_name: str):
    """Envia RAW no Windows via winspool."""
    hPrinter = wintypes.HANDLE()

    if not winspool.OpenPrinterW(printer_name, ctypes.byref(hPrinter), None):
        raise PrinterError(f"Não foi possível abrir a impressora: {printer_name}")

    try:
        doc_info = _DOC_INFO_1(
            pDocName=job_name, pOutputFile=None, pDatatype="RAW"
        )
        job_id = winspool.StartDocPrinterW(hPrinter, 1, ctypes.byref(doc_info))
        if job_id == 0:
            raise PrinterError("Falha ao iniciar o trabalho de impressão")

        try:
            if not winspool.StartPagePrinter(hPrinter):
                raise PrinterError("Falha ao iniciar a página de impressão")

            written = wintypes.DWORD(0)
            buf = ctypes.create_string_buffer(data, len(data))
            ok = winspool.WritePrinter(
                hPrinter, buf, len(data), ctypes.byref(written)
            )

            if not ok:
                raise PrinterError("Falha ao enviar os dados para a impressora")

            if written.value != len(data):
                logger.warning(
                    f"Nem todos os dados foram escritos: {written.value}/{len(data)} bytes"
                )

            winspool.EndPagePrinter(hPrinter)
        finally:
            winspool.EndDocPrinter(hPrinter)

    finally:
        winspool.ClosePrinter(hPrinter)


def _send_raw_unix(printer_name: str, data: bytes):
    """Envia RAW no Unix via lp."""
    proc = subprocess.run(
        ["lp", "-d", printer_name, "-o", "raw"],
        input=data,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise PrinterError(proc.stderr.decode(errors="ignore"))
