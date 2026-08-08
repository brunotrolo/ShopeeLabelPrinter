"""
Módulo de impressão: envio RAW para impressora térmica.
"""

import re
import platform
import subprocess
import ctypes
from ctypes import wintypes

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    winspool = ctypes.WinDLL("winspool.drv")

    class _DOC_INFO_1(ctypes.Structure):
        _fields_ = [
            ("pDocName", wintypes.LPWSTR),
            ("pOutputFile", wintypes.LPWSTR),
            ("pDatatype", wintypes.LPWSTR),
        ]


def list_printers():
    """Lista as impressoras disponíveis no sistema."""
    if IS_WINDOWS:
        # Usa o PowerShell (já vem em qualquer Windows 10/11), sem libs extras
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Printer | Select-Object -ExpandProperty Name"],
                capture_output=True, text=True, timeout=10,
            )
            names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            return names
        except Exception:
            return []
    else:
        try:
            out = subprocess.run(["lpstat", "-p"], capture_output=True, text=True)
            names = re.findall(r"printer (\S+)", out.stdout)
            return names
        except FileNotFoundError:
            return []


def send_raw_to_printer(printer_name: str, data: bytes, job_name: str = "Etiqueta Shopee"):
    """Envia bytes crus para a impressora, sem reprocessar/reamostrar nada."""
    if IS_WINDOWS:
        hPrinter = wintypes.HANDLE()
        if not winspool.OpenPrinterW(printer_name, ctypes.byref(hPrinter), None):
            raise RuntimeError(f"Não foi possível abrir a impressora: {printer_name}")
        try:
            doc_info = _DOC_INFO_1(
                pDocName=job_name, pOutputFile=None, pDatatype="RAW"
            )
            job_id = winspool.StartDocPrinterW(hPrinter, 1, ctypes.byref(doc_info))
            if job_id == 0:
                raise RuntimeError("Falha ao iniciar o trabalho de impressão")
            try:
                if not winspool.StartPagePrinter(hPrinter):
                    raise RuntimeError("Falha ao iniciar a página de impressão")
                written = wintypes.DWORD(0)
                buf = ctypes.create_string_buffer(data, len(data))
                ok = winspool.WritePrinter(
                    hPrinter, buf, len(data), ctypes.byref(written)
                )
                if not ok:
                    raise RuntimeError("Falha ao enviar os dados para a impressora")
                winspool.EndPagePrinter(hPrinter)
            finally:
                winspool.EndDocPrinter(hPrinter)
        finally:
            winspool.ClosePrinter(hPrinter)
    else:
        proc = subprocess.run(
            ["lp", "-d", printer_name, "-o", "raw"],
            input=data,
            capture_output=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode(errors="ignore"))
