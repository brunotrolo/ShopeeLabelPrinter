"""
Módulo de interface gráfica: aplicação tkinter.

Layout em duas colunas: controles à esquerda, preview da etiqueta à direita.
O preview é reconstruído a partir dos mesmos bytes que vão para a impressora,
mas nunca os altera — o envio continua sendo RAW, byte a byte.
"""

import math
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .logger import setup_logging
from .parser import ParserError, load_labels_from_path
from .printer import PrinterError, list_printers, send_raw_to_printer
from .renderer import RenderError, render_zpl, to_ppm, downsample

# Níveis de zoom: rótulo -> fator de redução (1 = resolução nativa 203 DPI)
ZOOM_LEVELS = [
    ("Ajustar à janela", None),
    ("100% (203 DPI)", 1),
    ("50%", 2),
    ("33%", 3),
    ("25%", 4),
]


class ShopeePrintApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Shopee Label Printer v{__version__}")
        self.geometry("1150x780")
        self.minsize(900, 600)

        self.labels_loaded = []      # lista de (nome, bytes)
        self._preview_image = None   # referência viva do PhotoImage
        self._current_render = None
        self._current_index = None
        self._placeholder = ""
        self.log_text = None

        # A UI precisa existir antes do logging: setup_logging() já emite a
        # primeira mensagem, e ela é entregue ao callback na hora.
        self._build_ui()
        self.logger = setup_logging(console_callback=self._log)
        self._refresh_printers()

    # -- construção da UI ---------------------------------------------------
    def _build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=(10, 4))
        ttk.Label(header, text="Shopee Label Printer", font=("Arial", 14, "bold")).pack(side="left")
        ttk.Label(
            header,
            text="Envio RAW · sem perda de resolução",
            font=("Arial", 9),
            foreground="gray",
        ).pack(side="left", padx=8)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=6)

        left = ttk.Frame(body, width=430)
        left.pack(side="left", fill="both")
        left.pack_propagate(False)

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        self._build_controls(left)
        self._build_preview(right)

    def _build_controls(self, parent):
        pad = {"padx": 0, "pady": 5}

        import_frame = ttk.Frame(parent)
        import_frame.pack(fill="x", **pad)
        ttk.Button(
            import_frame, text="📂 Importar ZIP / Pasta / TXT", command=self._on_import
        ).pack(side="left")

        self.status_label = ttk.Label(parent, text="Nenhum arquivo carregado", foreground="orange")
        self.status_label.pack(anchor="w")

        printer_frame = ttk.LabelFrame(parent, text="Impressora", padding=8)
        printer_frame.pack(fill="x", **pad)

        self.printer_var = tk.StringVar()
        self.printer_combo = ttk.Combobox(
            printer_frame, textvariable=self.printer_var, state="readonly", width=34
        )
        self.printer_combo.pack(side="left")
        ttk.Button(printer_frame, text="🔄", width=3, command=self._refresh_printers).pack(
            side="left", padx=4
        )

        list_frame = ttk.LabelFrame(parent, text="Etiquetas encontradas", padding=8)
        list_frame.pack(fill="both", expand=True, **pad)

        self.listbox = tk.Listbox(list_frame, selectmode="extended", exportselection=False)
        self.listbox.pack(fill="both", expand=True, side="left")
        self.listbox.bind("<<ListboxSelect>>", self._on_select_label)

        scrollbar = ttk.Scrollbar(list_frame, command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        action_frame = ttk.Frame(parent)
        action_frame.pack(fill="x", **pad)
        ttk.Button(action_frame, text="🖨️ Selecionadas", command=self._print_selected).pack(
            side="left"
        )
        ttk.Button(action_frame, text="🖨️ Todas", command=self._print_all).pack(side="left", padx=4)
        ttk.Button(action_frame, text="ℹ️ Logs", command=self._show_log_dir).pack(side="left")

        ttk.Label(parent, text="Log:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(6, 0))
        self.log_text = tk.Text(parent, height=8, state="disabled", font=("Courier", 8))
        self.log_text.pack(fill="x")

    def _build_preview(self, parent):
        frame = ttk.LabelFrame(parent, text="Preview da etiqueta", padding=8)
        frame.pack(fill="both", expand=True)

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", pady=(0, 6))

        ttk.Label(toolbar, text="Zoom:").pack(side="left")
        self.zoom_var = tk.StringVar(value=ZOOM_LEVELS[0][0])
        zoom_combo = ttk.Combobox(
            toolbar,
            textvariable=self.zoom_var,
            state="readonly",
            width=18,
            values=[label for label, _ in ZOOM_LEVELS],
        )
        zoom_combo.pack(side="left", padx=6)
        zoom_combo.bind("<<ComboboxSelected>>", lambda _e: self._draw_preview())

        self.preview_info = ttk.Label(toolbar, text="", foreground="gray", font=("Arial", 9))
        self.preview_info.pack(side="left", padx=10)

        canvas_frame = ttk.Frame(frame)
        canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(canvas_frame, background="#e9ecef", highlightthickness=0)
        v_scroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        h_scroll = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self._show_placeholder("Importe um arquivo e selecione uma etiqueta")

    # -- preview -------------------------------------------------------------
    def _show_placeholder(self, message: str):
        self.canvas.delete("all")
        self._preview_image = None
        self._placeholder = message

        # winfo_width() ainda devolve 1 antes do primeiro layout, o que jogava
        # o texto para fora da área visível. Nesse caso espera o <Configure>,
        # que redesenha com o tamanho real.
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1 or height <= 1:
            return

        self.canvas.create_text(
            width // 2,
            height // 2,
            text=message,
            fill="#868e96",
            font=("Arial", 11),
            width=width - 40,
            justify="center",
        )
        self.canvas.configure(scrollregion=(0, 0, width, height))

    def _on_canvas_resize(self, _event):
        if self._current_render is None:
            if self._placeholder:
                self._show_placeholder(self._placeholder)
        elif self.zoom_var.get() == ZOOM_LEVELS[0][0]:
            self._draw_preview()

    def _on_select_label(self, _event=None):
        selection = self.listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if index == self._current_index:
            return

        self._current_index = index
        name, data = self.labels_loaded[index]

        try:
            self._current_render = render_zpl(data)
        except RenderError as exc:
            self._current_render = None
            self.preview_info.config(text="")
            self._show_placeholder(f"Não foi possível gerar o preview:\n{exc}")
            self._log(f"⚠️  Preview indisponível para {name}: {exc}")
            return
        except Exception as exc:  # noqa: BLE001 - preview nunca pode derrubar o app
            self._current_render = None
            self.preview_info.config(text="")
            self._show_placeholder("Não foi possível gerar o preview desta etiqueta")
            self._log(f"⚠️  Preview falhou para {name}: {exc}")
            return

        self._draw_preview()

    def _fit_factor(self, render) -> int:
        """Menor fator inteiro que faz a etiqueta caber na área visível."""
        available_w = max(self.canvas.winfo_width() - 20, 100)
        available_h = max(self.canvas.winfo_height() - 20, 100)
        needed = max(render.width / available_w, render.height / available_h)
        return max(1, math.ceil(needed))

    def _draw_preview(self):
        render = self._current_render
        if render is None:
            return

        factor = dict(ZOOM_LEVELS)[self.zoom_var.get()] or self._fit_factor(render)
        width, height, gray = downsample(render, factor)

        self._preview_image = tk.PhotoImage(data=to_ppm(width, height, gray))

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self._preview_image, anchor="nw")
        self.canvas.create_rectangle(0, 0, width, height, outline="#adb5bd")

        scale = 1 / factor
        for overlay in render.overlays:
            self._draw_overlay(overlay, scale)

        self.canvas.configure(scrollregion=(0, 0, width, height))
        self.preview_info.config(
            text=(
                f"{render.width} × {render.height} pontos · "
                f"{render.width_mm:.0f} × {render.height_mm:.0f} mm · {render.dpi} DPI"
            )
        )

    def _draw_overlay(self, overlay, scale: float):
        """Desenha os elementos vetoriais (texto, caixa, código) sobre o bitmap."""
        x = overlay.x * scale
        y = overlay.y * scale

        if overlay.kind == "text":
            size = max(6, int(overlay.font_height * scale))
            self.canvas.create_text(
                x,
                y,
                text=overlay.data,
                anchor="nw",
                fill="#000000",
                font=("Arial", -size),
            )

        elif overlay.kind == "box":
            self.canvas.create_rectangle(
                x,
                y,
                x + overlay.width * scale,
                y + overlay.height * scale,
                outline="#000000",
                width=max(1, overlay.thickness * scale),
            )

        elif overlay.kind == "barcode":
            cursor = x
            height = overlay.height * scale
            for i, module in enumerate(overlay.modules):
                span = module * overlay.thickness * scale
                if i % 2 == 0 and span > 0:  # índices pares são barras
                    self.canvas.create_rectangle(
                        cursor, y, cursor + span, y + height, fill="#000000", width=0
                    )
                cursor += span

        elif overlay.kind == "qr":
            side = max(20, 25 * overlay.thickness * scale)
            self.canvas.create_rectangle(x, y, x + side, y + side, outline="#000000", dash=(3, 3))
            self.canvas.create_text(
                x + side / 2, y + side / 2, text="QR", fill="#495057", font=("Arial", 8)
            )

    # -- ações ---------------------------------------------------------------
    def _log(self, msg: str):
        if self.log_text is None:  # log emitido antes da UI existir
            return
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"{msg}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _refresh_printers(self):
        self._log("Buscando impressoras...")
        printers = list_printers()
        self.printer_combo["values"] = printers

        if printers:
            thermal = [
                p for p in printers if any(x in p.lower() for x in ("fy", "térm", "label", "thermal"))
            ]
            self.printer_var.set(thermal[0] if thermal else printers[0])
            self._log(f"✓ {len(printers)} impressora(s) encontrada(s)")
        else:
            self._log("⚠️  Nenhuma impressora encontrada. Instale a impressora antes de imprimir.")

    def _on_import(self):
        path = filedialog.askopenfilename(
            title="Selecione o ZIP, TXT ou etiqueta",
            filetypes=[
                ("Etiquetas / ZIP", "*.zip *.txt *.zpl *.prn *.tspl"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not path:
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
                text=f"✓ {len(self.labels_loaded)} etiqueta(s)", foreground="green"
            )
            self._log(f"✓ Carregadas {len(self.labels_loaded)} etiqueta(s)")

            # Já mostra a primeira etiqueta — o usuário confere antes de imprimir.
            self._current_index = None
            self._current_render = None
            if self.labels_loaded:
                self.listbox.selection_set(0)
                self._on_select_label()

        except ParserError as e:
            self.status_label.config(text="❌ Erro ao carregar", foreground="red")
            self._log(f"❌ ERRO: {e}")
            messagebox.showerror("Erro ao importar", str(e))

        except Exception as e:  # noqa: BLE001
            self.status_label.config(text="❌ Erro desconhecido", foreground="red")
            self._log(f"❌ ERRO DESCONHECIDO: {e}")
            messagebox.showerror("Erro", f"Erro desconhecido: {e}")

    def _print_indices(self, indices):
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
                self._log(f"❌ {name}: {e}")
                fail += 1
            except Exception as e:  # noqa: BLE001
                self._log(f"❌ {name}: Erro desconhecido: {e}")
                fail += 1

        msg = f"{ok} etiqueta(s) enviada(s) com sucesso"
        if fail:
            msg += f"\n{fail} falharam"
        messagebox.showinfo("Concluído", msg)

    def _print_selected(self):
        self._print_indices(list(self.listbox.curselection()))

    def _print_all(self):
        self._print_indices(list(range(len(self.labels_loaded))))

    def _show_log_dir(self):
        from .logger import _get_log_dir

        log_dir = _get_log_dir()
        if os.name == "nt":
            os.startfile(str(log_dir))  # noqa: S606
        else:
            os.system(f"open '{log_dir}'")  # noqa: S605
        self._log(f"Abrindo: {log_dir}")


def main():
    app = ShopeePrintApp()
    app.mainloop()


if __name__ == "__main__":
    main()
