"""
Shopee Label Printer
=====================
Importa o ZIP (ou pasta/arquivo TXT) que a Shopee fornece com etiquetas de envio
em ZPL/TSPL e envia cada etiqueta DIRETO (em modo bruto/RAW) para a impressora
térmica, sem passar por PDF -- evitando qualquer perda de resolução.

Requisitos:
    Nenhuma biblioteca externa. Usa só a Python padrão (ctypes + PowerShell
    no Windows; comando "lp" do CUPS no macOS/Linux).

Como rodar:
    python shopee_print_app.py

Como transformar num .exe que roda sem precisar de Python instalado:
    Veja o arquivo LEIA-ME.md (é um comando único, rodado uma vez).
"""

import os
import re
import sys
import zipfile
import shutil
import tempfile
import platform
import subprocess
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    winspool = ctypes.WinDLL("winspool.drv")

    class _DOC_INFO_1(ctypes.Structure):
        _fields_ = [
            ("pDocName", wintypes.LPWSTR),
            ("pOutputFile", wintypes.LPWSTR),
            ("pDatatype", wintypes.LPWSTR),
        ]

LABEL_EXTENSIONS = {".txt", ".zpl", ".prn", ".tspl"}


# ---------------------------------------------------------------------------
# Lógica de arquivos (sem dependência de GUI, pra poder ser testada isolada)
# ---------------------------------------------------------------------------

def extract_zip_to_temp(zip_path: str) -> str:
    """Extrai o ZIP para uma pasta temporária e retorna o caminho dela."""
    tmp_dir = tempfile.mkdtemp(prefix="shopee_labels_")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmp_dir)
    return tmp_dir


def find_label_files(folder: str):
    """Varre a pasta (recursivo) procurando arquivos de etiqueta."""
    files = []
    for root, _dirs, names in os.walk(folder):
        for name in names:
            if Path(name).suffix.lower() in LABEL_EXTENSIONS:
                files.append(os.path.join(root, name))
    return sorted(files)


def split_labels(content: str):
    """
    Alguns arquivos trazem mais de uma etiqueta concatenada no mesmo TXT.
    Divide o conteúdo em blocos individuais, um por etiqueta.
    """
    if "~DG" in content:
        # Cada etiqueta com imagem embutida começa com ~DG
        parts = re.split(r"(?=~DG)", content)
    elif "^XA" in content:
        # ZPL sem imagem embutida: cada etiqueta começa com ^XA
        parts = re.split(r"(?=\^XA)", content)
    else:
        parts = [content]
    return [p for p in parts if p.strip()]


def load_labels_from_path(path: str):
    """
    Aceita um .zip, uma pasta já extraída, ou um único arquivo .txt/.zpl.
    Retorna lista de tuplas (nome_origem, bytes_da_etiqueta).
    """
    labels = []

    if os.path.isdir(path):
        source_files = find_label_files(path)
    elif path.lower().endswith(".zip"):
        tmp_dir = extract_zip_to_temp(path)
        source_files = find_label_files(tmp_dir)
    else:
        source_files = [path]

    for file_path in source_files:
        with open(file_path, "rb") as f:
            raw = f.read()
        # decodifica em latin-1 (1 byte = 1 char, não perde nenhum byte)
        text = raw.decode("latin-1")
        blocks = split_labels(text)
        for i, block in enumerate(blocks):
            name = Path(file_path).name
            if len(blocks) > 1:
                name = f"{name} (etiqueta {i + 1}/{len(blocks)})"
            labels.append((name, block.encode("latin-1")))

    return labels


# ---------------------------------------------------------------------------
# Impressão bruta (RAW)
# ---------------------------------------------------------------------------

def list_printers():
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


# ---------------------------------------------------------------------------
# Interface gráfica
# ---------------------------------------------------------------------------

class ShopeePrintApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Shopee Label Printer")
        self.geometry("640x520")
        self.resizable(True, True)

        self.labels_loaded = []  # lista de (nome, bytes)

        self._build_ui()
        self._refresh_printers()

    # -- construção da UI ---------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", **pad)

        ttk.Button(
            top_frame, text="Importar ZIP / Pasta / TXT", command=self._on_import
        ).pack(side="left")

        self.status_label = ttk.Label(top_frame, text="Nenhum arquivo carregado")
        self.status_label.pack(side="left", padx=12)

        # Seletor de impressora
        printer_frame = ttk.Frame(self)
        printer_frame.pack(fill="x", **pad)

        ttk.Label(printer_frame, text="Impressora:").pack(side="left")
        self.printer_var = tk.StringVar()
        self.printer_combo = ttk.Combobox(
            printer_frame, textvariable=self.printer_var, state="readonly", width=40
        )
        self.printer_combo.pack(side="left", padx=8)

        ttk.Button(
            printer_frame, text="Atualizar lista", command=self._refresh_printers
        ).pack(side="left")

        # Lista de etiquetas encontradas
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, **pad)

        ttk.Label(list_frame, text="Etiquetas encontradas:").pack(anchor="w")

        self.listbox = tk.Listbox(list_frame, selectmode="extended")
        self.listbox.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(list_frame, command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        # Botões de ação
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", **pad)

        ttk.Button(
            action_frame, text="Imprimir selecionadas", command=self._print_selected
        ).pack(side="left")

        ttk.Button(
            action_frame, text="Imprimir todas", command=self._print_all
        ).pack(side="left", padx=8)

        # Log
        ttk.Label(self, text="Log:").pack(anchor="w", padx=10)
        self.log_text = tk.Text(self, height=10, state="disabled")
        self.log_text.pack(fill="both", expand=False, padx=10, pady=(0, 10))

    # -- ações ---------------------------------------------------------------
    def _log(self, msg: str):
        self.log_text.config(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {msg}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _refresh_printers(self):
        printers = list_printers()
        self.printer_combo["values"] = printers
        if printers and not self.printer_var.get():
            self.printer_var.set(printers[0])
        if not printers:
            self._log(
                "Nenhuma impressora encontrada. Verifique se ela está instalada "
                "no Windows (Painel de Controle > Dispositivos e Impressoras)."
            )

    def _on_import(self):
        path = filedialog.askopenfilename(
            title="Selecione o ZIP, TXT ou etiqueta",
            filetypes=[
                ("Etiquetas / ZIP", "*.zip *.txt *.zpl *.prn *.tspl"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not path:
            # tenta como pasta, caso o usuário tenha cancelado o seletor de arquivo
            path = filedialog.askdirectory(title="Ou selecione uma pasta com etiquetas")
            if not path:
                return

        try:
            self.labels_loaded = load_labels_from_path(path)
        except Exception as e:
            messagebox.showerror("Erro ao importar", str(e))
            return

        self.listbox.delete(0, "end")
        for name, _data in self.labels_loaded:
            self.listbox.insert("end", name)

        self.status_label.config(
            text=f"{len(self.labels_loaded)} etiqueta(s) carregada(s) de: {os.path.basename(path)}"
        )
        self._log(f"Carregado: {path} -> {len(self.labels_loaded)} etiqueta(s)")

    def _print_indices(self, indices):
        printer = self.printer_var.get()
        if not printer:
            messagebox.showwarning("Atenção", "Selecione uma impressora antes de imprimir.")
            return
        if not indices:
            messagebox.showwarning("Atenção", "Nenhuma etiqueta selecionada.")
            return

        ok, fail = 0, 0
        for i in indices:
            name, data = self.labels_loaded[i]
            try:
                send_raw_to_printer(printer, data, job_name=name)
                self._log(f"Impresso: {name}")
                ok += 1
            except Exception as e:
                self._log(f"ERRO ao imprimir {name}: {e}")
                fail += 1

        messagebox.showinfo(
            "Concluído", f"{ok} etiqueta(s) enviada(s) com sucesso.\n{fail} falharam."
        )

    def _print_selected(self):
        self._print_indices(list(self.listbox.curselection()))

    def _print_all(self):
        self._print_indices(list(range(len(self.labels_loaded))))


if __name__ == "__main__":
    app = ShopeePrintApp()
    app.mainloop()
