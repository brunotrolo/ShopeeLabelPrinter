"""
Módulo de interface gráfica: aplicação tkinter.
Com tratamento de erros e logging integrados.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

from .parser import load_labels_from_path, ParserError
from .printer import list_printers, send_raw_to_printer, PrinterError
from .logger import setup_logging, get_logger


class ShopeePrintApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Shopee Label Printer v0.1.0")
        self.geometry("700x600")
        self.resizable(True, True)

        # Inicializar logging
        self.logger = setup_logging(console_callback=self._log)

        self.labels_loaded = []  # lista de (nome, bytes)

        self._build_ui()
        self._refresh_printers()

    # -- construção da UI ---------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", **pad)
        ttk.Label(header, text="Shopee Label Printer", font=("Arial", 14, "bold")).pack(side="left")
        ttk.Label(header, text="Imprima etiquetas em modo RAW", font=("Arial", 9), foreground="gray").pack(side="left", padx=8)

        # Botão de importação
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", **pad)

        ttk.Button(
            top_frame, text="📂 Importar ZIP / Pasta / TXT", command=self._on_import
        ).pack(side="left")

        self.status_label = ttk.Label(top_frame, text="Nenhum arquivo carregado", foreground="orange")
        self.status_label.pack(side="left", padx=12)

        # Seletor de impressora
        printer_frame = ttk.LabelFrame(self, text="Impressora", padding=10)
        printer_frame.pack(fill="x", **pad)

        ttk.Label(printer_frame, text="Selecione:").pack(side="left")
        self.printer_var = tk.StringVar()
        self.printer_combo = ttk.Combobox(
            printer_frame, textvariable=self.printer_var, state="readonly", width=40
        )
        self.printer_combo.pack(side="left", padx=8)

        ttk.Button(
            printer_frame, text="🔄 Atualizar", command=self._refresh_printers
        ).pack(side="left")

        # Lista de etiquetas encontradas
        list_frame = ttk.LabelFrame(self, text="Etiquetas encontradas", padding=10)
        list_frame.pack(fill="both", expand=True, **pad)

        self.listbox = tk.Listbox(list_frame, selectmode="extended", height=8)
        self.listbox.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(list_frame, command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        # Botões de ação
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", **pad)

        ttk.Button(
            action_frame, text="🖨️  Imprimir selecionadas", command=self._print_selected
        ).pack(side="left", padx=4)

        ttk.Button(
            action_frame, text="🖨️  Imprimir todas", command=self._print_all
        ).pack(side="left", padx=4)

        ttk.Button(
            action_frame, text="ℹ️  Logs", command=self._show_log_dir
        ).pack(side="left", padx=4)

        # Log
        ttk.Label(self, text="Log:", font=("Arial", 9, "bold")).pack(anchor="w", padx=10)
        self.log_text = tk.Text(self, height=8, state="disabled", font=("Courier", 8))
        self.log_text.pack(fill="both", expand=False, padx=10, pady=(0, 10))

    # -- ações ---------------------------------------------------------------
    def _log(self, msg: str):
        """Adiciona mensagem ao log da GUI."""
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"{msg}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _refresh_printers(self):
        """Atualiza a lista de impressoras."""
        self._log("Buscando impressoras...")
        printers = list_printers()
        self.printer_combo["values"] = printers

        if printers:
            # Tentar pré-selecionar impressora térmica
            thermal_printers = [p for p in printers if any(x in p.lower() for x in ['fy', 'térm', 'label', 'thermal'])]
            if thermal_printers:
                self.printer_var.set(thermal_printers[0])
            else:
                self.printer_var.set(printers[0])
            self._log(f"✓ {len(printers)} impressora(s) encontrada(s)")
        else:
            self._log("⚠️  Nenhuma impressora encontrada. Instale a impressora antes de abrir este programa.")

    def _on_import(self):
        """Importa arquivo ZIP, pasta ou TXT."""
        path = filedialog.askopenfilename(
            title="Selecione o ZIP, TXT ou etiqueta",
            filetypes=[
                ("Etiquetas / ZIP", "*.zip *.txt *.zpl *.prn *.tspl"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not path:
            # tenta como pasta
            path = filedialog.askdirectory(title="Ou selecione uma pasta com etiquetas")
            if not path:
                return

        try:
            self._log(f"Carregando: {os.path.basename(path)}...")
            self.labels_loaded = load_labels_from_path(path)

            self.listbox.delete(0, "end")
            for name, _data in self.labels_loaded:
                self.listbox.insert("end", name)

            self.status_label.config(
                text=f"✓ {len(self.labels_loaded)} etiqueta(s)",
                foreground="green"
            )
            self._log(f"✓ Carregadas {len(self.labels_loaded)} etiqueta(s)")

        except ParserError as e:
            self.status_label.config(text="❌ Erro ao carregar", foreground="red")
            self._log(f"❌ ERRO: {str(e)}")
            messagebox.showerror("Erro ao importar", str(e))

        except Exception as e:
            self.status_label.config(text="❌ Erro desconhecido", foreground="red")
            self._log(f"❌ ERRO DESCONHECIDO: {str(e)}")
            messagebox.showerror("Erro", f"Erro desconhecido: {str(e)}")

    def _print_indices(self, indices):
        """Imprime as etiquetas nos índices fornecidos."""
        printer = self.printer_var.get()
        if not printer:
            messagebox.showwarning("Atenção", "Selecione uma impressora antes de imprimir.")
            self._log("⚠️  Impressora não selecionada")
            return
        if not indices:
            messagebox.showwarning("Atenção", "Nenhuma etiqueta selecionada.")
            self._log("⚠️  Nenhuma etiqueta selecionada")
            return

        ok, fail = 0, 0
        for i in indices:
            name, data = self.labels_loaded[i]
            try:
                send_raw_to_printer(printer, data, job_name=name)
                self._log(f"✓ {name}")
                ok += 1
            except PrinterError as e:
                self._log(f"❌ {name}: {str(e)}")
                fail += 1
            except Exception as e:
                self._log(f"❌ {name}: Erro desconhecido: {str(e)}")
                fail += 1

        msg = f"{ok} etiqueta(s) enviada(s) com sucesso"
        if fail:
            msg += f"\n{fail} falharam"
        messagebox.showinfo("Concluído", msg)

    def _print_selected(self):
        """Imprime as etiquetas selecionadas na listbox."""
        self._print_indices(list(self.listbox.curselection()))

    def _print_all(self):
        """Imprime todas as etiquetas."""
        self._print_indices(list(range(len(self.labels_loaded))))

    def _show_log_dir(self):
        """Abre o diretório de logs."""
        from .logger import _get_log_dir
        log_dir = _get_log_dir()
        if os.name == 'nt':
            os.startfile(str(log_dir))
        else:
            os.system(f"open '{log_dir}'")
        self._log(f"Abrindo: {log_dir}")


def main():
    app = ShopeePrintApp()
    app.mainloop()


if __name__ == "__main__":
    main()
