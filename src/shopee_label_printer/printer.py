"""
Módulo de impressão: envio RAW para impressora térmica.
Com tratamento robusto de erros.
"""

import ctypes
import logging
import platform
import re
import subprocess
from ctypes import wintypes

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    # use_last_error=True guarda o GetLastError() da chamada, que é o que
    # explica por que a impressão falhou. Sem isso, todo erro vira só
    # "não foi possível" e não dá para diagnosticar nada.
    winspool = ctypes.WinDLL("winspool.drv", use_last_error=True)

    class _DOC_INFO_1(ctypes.Structure):
        _fields_ = [
            ("pDocName", wintypes.LPWSTR),
            ("pOutputFile", wintypes.LPWSTR),
            ("pDatatype", wintypes.LPWSTR),
        ]

    # Sem argtypes o ctypes assume int de 32 bits para ponteiros e handles.
    # No Windows 64 bits isso trunca o handle da impressora, e as chamadas
    # seguintes falham (ou pior, escrevem em endereço errado).
    winspool.OpenPrinterW.argtypes = [
        wintypes.LPWSTR, ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p
    ]
    winspool.OpenPrinterW.restype = wintypes.BOOL

    winspool.StartDocPrinterW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(_DOC_INFO_1)
    ]
    winspool.StartDocPrinterW.restype = wintypes.DWORD

    winspool.StartPagePrinter.argtypes = [wintypes.HANDLE]
    winspool.StartPagePrinter.restype = wintypes.BOOL

    winspool.WritePrinter.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)
    ]
    winspool.WritePrinter.restype = wintypes.BOOL

    winspool.EndPagePrinter.argtypes = [wintypes.HANDLE]
    winspool.EndPagePrinter.restype = wintypes.BOOL

    winspool.EndDocPrinter.argtypes = [wintypes.HANDLE]
    winspool.EndDocPrinter.restype = wintypes.BOOL

    winspool.ClosePrinter.argtypes = [wintypes.HANDLE]
    winspool.ClosePrinter.restype = wintypes.BOOL


def _windows_error(action: str) -> str:
    """Monta a mensagem com o código e o texto de erro que o Windows devolveu."""
    code = ctypes.get_last_error()
    if not code:
        return action
    try:
        detail = ctypes.WinError(code).strerror
    except Exception:  # noqa: BLE001
        detail = "erro desconhecido"
    return f"{action} (erro {code} do Windows: {detail})"


class PrinterError(Exception):
    """Erro na comunicação com impressora."""
    pass


def list_printers() -> list[str]:
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


def _list_printers_windows() -> list[str]:
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


def _list_printers_unix() -> list[str]:
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

    ctypes.set_last_error(0)
    if not winspool.OpenPrinterW(printer_name, ctypes.byref(hPrinter), None):
        raise PrinterError(
            _windows_error(f"Não foi possível abrir a impressora '{printer_name}'")
        )

    logger.debug("Impressora aberta: %s", printer_name)

    try:
        doc_info = _DOC_INFO_1(pDocName=job_name, pOutputFile=None, pDatatype="RAW")

        ctypes.set_last_error(0)
        job_id = winspool.StartDocPrinterW(hPrinter, 1, ctypes.byref(doc_info))
        if job_id == 0:
            raise PrinterError(
                _windows_error(
                    "Falha ao iniciar o trabalho de impressão. A impressora pode não "
                    "aceitar dados RAW com o driver instalado"
                )
            )

        logger.info("Trabalho %s iniciado (%d bytes, modo RAW)", job_id, len(data))

        try:
            ctypes.set_last_error(0)
            if not winspool.StartPagePrinter(hPrinter):
                raise PrinterError(_windows_error("Falha ao iniciar a página"))

            written = wintypes.DWORD(0)
            buf = ctypes.create_string_buffer(data, len(data))

            ctypes.set_last_error(0)
            ok = winspool.WritePrinter(hPrinter, buf, len(data), ctypes.byref(written))

            if not ok:
                raise PrinterError(_windows_error("Falha ao enviar os dados"))

            # Envio parcial é falha, não aviso: a etiqueta chega cortada na
            # impressora e o usuário só descobriria olhando o papel.
            if written.value != len(data):
                raise PrinterError(
                    f"A impressora aceitou apenas {written.value} de {len(data)} bytes. "
                    "A etiqueta chegaria incompleta."
                )

            logger.info("%d bytes entregues ao spooler", written.value)
            winspool.EndPagePrinter(hPrinter)
        finally:
            winspool.EndDocPrinter(hPrinter)

    finally:
        winspool.ClosePrinter(hPrinter)


# Níveis de reforço: (escurecimento ^MD, velocidade ^PR em polegadas/s).
#
# Numa impressora térmica, traço fino e falhado quase nunca se resolve
# engrossando o desenho — resolve-se com mais calor (^MD) e menos velocidade
# (^PR), que é o que faz o ponto sair cheio. Engrossar o bitmap alargaria
# também as barras do código de barras e mudaria a proporção barra/espaço,
# que é justamente o que o leitor mede: o código ficaria mais grosso e
# ilegível. Por isso aqui se mexe no calor, nunca na geometria.
PRINT_BOOST_LEVELS = {
    "desligado": (None, None),
    "leve": (6, 3),
    "medio": (12, 2),
    "forte": (18, 2),
}

_XA_RE = re.compile(rb"\^XA")


def apply_print_boost(data: bytes, level: str) -> bytes:
    """
    Insere ajuste de escurecimento (^MD) e velocidade (^PR) na etiqueta.

    ATENÇÃO: isto ALTERA os bytes enviados à impressora — é a única função do
    projeto que faz isso, e só age quando o usuário pede. O desenho não muda:
    ^MD e ^PR mexem em quanto a cabeça térmica esquenta e em quanto o papel
    corre, não no conteúdo. Nenhum ponto é acrescentado ou movido.

    Escurecer demais faz a tinta espalhar e as barras engordarem a ponto do
    leitor não conseguir mais ler o código. Se o código de barras parar de
    ser lido, baixe um nível.

    Args:
        data: bytes originais da etiqueta
        level: uma das chaves de PRINT_BOOST_LEVELS

    Returns:
        Os bytes ajustados — ou os originais, intactos, se o nível for
        "desligado" ou a etiqueta não tiver ^XA.
    """
    darkness, speed = PRINT_BOOST_LEVELS.get(level, (None, None))
    if darkness is None and speed is None:
        return data

    match = _XA_RE.search(data)
    if not match:
        logger.warning("Etiqueta sem ^XA: reforço de impressão não aplicado")
        return data

    commands = b""
    if darkness is not None:
        commands += b"^MD%d" % darkness
    if speed is not None:
        commands += b"^PR%d" % speed

    logger.info("Reforço '%s' aplicado: %s", level, commands.decode("ascii"))
    return data[: match.end()] + commands + data[match.end() :]


# Etiquetas mínimas de teste, uma em cada linguagem.
#
# Servem para descobrir o que a impressora entende. A etiqueta da Shopee é
# ZPL; se a impressora estiver em modo TSPL, ela simplesmente ignora os
# comandos ZPL e não sai nada — sem erro nenhum, porque do ponto de vista do
# Windows os bytes foram entregues.
TEST_LABELS = {
    "ZPL": (
        b"^XA\r\n"
        b"^FO40,40^A0N,45,45^FDTESTE ZPL^FS\r\n"
        b"^FO40,110^GB520,8,8^FS\r\n"
        b"^FO40,150^A0N,28,28^FDSe voce esta lendo isto,^FS\r\n"
        b"^FO40,190^A0N,28,28^FDa impressora entende ZPL.^FS\r\n"
        b"^XZ\r\n"
    ),
    "TSPL": (
        b"SIZE 100 mm,150 mm\r\n"
        b"GAP 3 mm,0 mm\r\n"
        b"DIRECTION 1\r\n"
        b"CLS\r\n"
        b'TEXT 40,40,"4",0,1,1,"TESTE TSPL"\r\n'
        b"BAR 40,110,520,8\r\n"
        b'TEXT 40,150,"3",0,1,1,"Se voce esta lendo isto,"\r\n'
        b'TEXT 40,190,"3",0,1,1,"a impressora entende TSPL."\r\n'
        b"PRINT 1,1\r\n"
    ),
}


def send_test_label(printer_name: str, language: str):
    """
    Envia uma etiqueta mínima de teste na linguagem escolhida.

    Se o teste ZPL sai e o TSPL não (ou vice-versa), está identificada a
    linguagem que a impressora fala — e, portanto, se a etiqueta da Shopee
    (que é ZPL) tem chance de funcionar nela.

    Raises:
        PrinterError: se a linguagem for desconhecida ou o envio falhar
    """
    language = language.upper()
    if language not in TEST_LABELS:
        raise PrinterError(
            f"Linguagem de teste desconhecida: {language}. "
            f"Use uma destas: {', '.join(TEST_LABELS)}"
        )

    send_raw_to_printer(
        printer_name, TEST_LABELS[language], job_name=f"Teste {language}"
    )


def _send_raw_unix(printer_name: str, data: bytes):
    """Envia RAW no Unix via lp."""
    proc = subprocess.run(
        ["lp", "-d", printer_name, "-o", "raw"],
        input=data,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise PrinterError(proc.stderr.decode(errors="ignore"))
