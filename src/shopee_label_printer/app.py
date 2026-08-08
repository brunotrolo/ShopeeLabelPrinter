"""
Módulo de interface gráfica: aplicação tkinter.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

from .parser import load_labels_from_path
from .printer import list_printers, send_raw_to_printer


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


def main():
    app = ShopeePrintApp()
    app.mainloop()


if __name__ == "__main__":
    main()
