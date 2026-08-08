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
from .printer import (
    PrinterError,
    apply_print_boost,
    list_printers,
    send_raw_to_printer,
    send_test_label,
)
from .renderer import RenderError, render_zpl, to_ppm, downsample
from .converters import zpl_to_tspl, zpl_to_pdf, ConversionError

# Níveis de zoom: rótulo -> fator de redução (1 = resolução nativa 203 DPI)
ZOOM_LEVELS = [
    ("Ajustar à janela", None),
    ("100% (203 DPI)", 1),
    ("50%", 2),
    ("33%", 3),
    ("25%", 4),
]

# Reforço de impressão: mais calor e menos velocidade, para traço fino sair
# cheio. Só age quando o usuário escolhe — o padrão envia os bytes intactos.
BOOST_CHOICES = [
    ("Leve — traço mais firme", "leve"),
    ("Médio — traço bem escuro", "medio"),
    ("Forte — pode borrar o código", "forte"),
    ("Customizado", "customizado"),
    ("Desligado (bytes originais)", "desligado"),
]

# Modos de saída: permite escolher entre ZPL nativo, TSPL (para FY-1075) ou PDF
MODE_CHOICES = [
    ("ZPL (Zebra nativo)", "zpl"),
    ("TSPL (FY-1075, compatível)", "tspl"),
    ("PDF (arquivo)", "pdf"),
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

        # Duas linhas empilhadas: cada uma num frame próprio, senão o pack
        # horizontal da primeira briga com o vertical da segunda.
        printer_row = ttk.Frame(printer_frame)
        printer_row.pack(fill="x")

        self.printer_var = tk.StringVar()
        self.printer_combo = ttk.Combobox(
            printer_row, textvariable=self.printer_var, state="readonly", width=32
        )
        self.printer_combo.pack(side="left")
        ttk.Button(printer_row, text="🔄", width=3, command=self._refresh_printers).pack(
            side="left", padx=4
        )

        boost_row = ttk.Frame(printer_frame)
        boost_row.pack(fill="x", pady=(8, 0))
        ttk.Label(boost_row, text="Reforço:").pack(side="left")
        self.boost_var = tk.StringVar(value="Leve — traço mais firme")
        self.boost_combo = ttk.Combobox(
            boost_row,
            textvariable=self.boost_var,
            state="readonly",
            width=26,
            values=[label for label, _ in BOOST_CHOICES],
        )
        self.boost_combo.pack(side="left", padx=6)
        self.boost_combo.bind("<<ComboboxSelected>>", self._on_boost_changed)

        self.custom_frame = ttk.Frame(printer_frame)
        self.custom_frame.pack(fill="x", pady=(8, 0))
        self._update_custom_ui()

        mode_row = ttk.Frame(printer_frame)
        mode_row.pack(fill="x", pady=(8, 0))
        ttk.Label(mode_row, text="Modo:").pack(side="left")
        self.mode_var = tk.StringVar(value="TSPL (FY-1075, compatível)")
        ttk.Combobox(
            mode_row,
            textvariable=self.mode_var,
            state="readonly",
            width=26,
            values=[label for label, _ in MODE_CHOICES],
        ).pack(side="left", padx=6)

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
        ttk.Button(action_frame, text="🔧 Testar", command=self._run_diagnostic).pack(side="left")
        ttk.Button(action_frame, text="ℹ️ Logs", command=self._show_log_dir).pack(side="left", padx=4)

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

    def _on_boost_changed(self, _event=None):
        """Atualiza a UI de customizado quando o boost é alterado."""
        self._update_custom_ui()

    def _update_custom_ui(self):
        """Mostra/esconde UI de customizado conforme a seleção."""
        for widget in self.custom_frame.winfo_children():
            widget.destroy()

        boost_label = self.boost_var.get()
        if "Customizado" in boost_label:
            # Mostra controles de DENSITY e SPEED
            ttk.Label(self.custom_frame, text="DENSITY (0-15):").pack(side="left", padx=(6, 4))
            self.custom_density_var = tk.IntVar(value=12)
            ttk.Scale(
                self.custom_frame,
                from_=0,
                to=15,
                orient="horizontal",
                variable=self.custom_density_var,
                length=100,
            ).pack(side="left", padx=(0, 4))
            ttk.Label(self.custom_frame, text=self.custom_density_var.get()).pack(side="left", padx=(0, 12))

            ttk.Label(self.custom_frame, text="SPEED (pol/s):").pack(side="left", padx=(0, 4))
            self.custom_speed_var = tk.IntVar(value=2)
            ttk.Scale(
                self.custom_frame,
                from_=1,
                to=4,
                orient="horizontal",
                variable=self.custom_speed_var,
                length=100,
            ).pack(side="left", padx=(0, 4))
            ttk.Label(self.custom_frame, text=self.custom_speed_var.get()).pack(side="left", padx=(0, 12))

            # Info sobre o que significa
            info_text = (
                "Aumentar DENSITY = mais escuro | Aumentar SPEED = mais rápido (menos escuro)"
            )
            ttk.Label(self.custom_frame, text=info_text, foreground="gray").pack(
                side="left", padx=6
            )
        else:
            # Mostra explicação sobre DENSITY e SPEED quando não é customizado
            self.custom_density_var = None
            self.custom_speed_var = None

    def _get_boost_level(self) -> str:
        """Retorna o nível de boost selecionado ou 'customizado' com valores."""
        boost_label = self.boost_var.get()
        boost_value = dict((label, value) for label, value in BOOST_CHOICES)[boost_label]

        if boost_value == "customizado":
            if hasattr(self, "custom_density_var") and self.custom_density_var:
                # Retorna uma tupla que será tratada diferente
                return (self.custom_density_var.get(), self.custom_speed_var.get())
        return boost_value

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
        if not indices:
            messagebox.showwarning("Atenção", "Nenhuma etiqueta selecionada.")
            self._log("⚠️  Nenhuma etiqueta selecionada")
            return

        mode = dict(MODE_CHOICES)[self.mode_var.get()]
        boost = self._get_boost_level()

        # Modo PDF salva em arquivo, não imprime — reforço não se aplica a
        # um arquivo estático.
        if mode == "pdf":
            return self._save_pdf_indices(indices)

        # Modos ZPL e TSPL precisam de impressora
        printer = self.printer_var.get()
        if not printer:
            messagebox.showwarning("Atenção", "Selecione uma impressora antes de imprimir.")
            self._log("⚠️  Impressora não selecionada")
            return

        boost_label = "customizado" if isinstance(boost, tuple) else boost
        if boost_label != "desligado":
            self._log(f"⚙️  Reforço de impressão: {boost_label} (altera os bytes enviados)")

        if mode != "zpl":
            self._log(f"⚙️  Modo de impressão: {mode.upper()}")

        ok, fail = 0, 0
        for i in indices:
            name, data = self.labels_loaded[i]
            try:
                # Converte para o modo selecionado. ^MD/^PR (apply_print_boost)
                # só existem em ZPL, por isso o reforço do TSPL entra dentro da
                # própria conversão, como DENSITY/SPEED.
                if mode == "tspl":
                    if isinstance(boost, tuple):
                        # Customizado: boost é (density, speed)
                        # Precisa converter para o formato esperado por zpl_to_tspl
                        # que usa strings de chaves em TSPL_BOOST_LEVELS
                        # Vamos adicionar suporte customizado direto em converters.py
                        data = zpl_to_tspl(data, render_zpl, boost_level="customizado", custom_density=boost[0], custom_speed=boost[1])
                    else:
                        data = zpl_to_tspl(data, render_zpl, boost_level=boost)
                    name = name.replace(".txt", ".tspl").replace(".zpl", ".tspl")
                elif boost != "desligado" and not isinstance(boost, tuple):
                    data = apply_print_boost(data, boost)

                send_raw_to_printer(printer, data, job_name=name)
                self._log(f"✓ {name}")
                ok += 1
            except ConversionError as e:
                self._log(f"❌ {name}: {e}")
                fail += 1
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

    def _save_pdf_indices(self, indices):
        """Salva etiquetas selecionadas como PDF."""
        folder = filedialog.askdirectory(title="Selecione a pasta para salvar os PDFs")
        if not folder:
            return

        ok, fail = 0, 0
        for i in indices:
            name, data = self.labels_loaded[i]
            try:
                pdf_path = os.path.join(folder, name.replace(".txt", ".pdf").replace(".zpl", ".pdf"))

                pdf_bytes = zpl_to_pdf(data, render_zpl)

                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)

                self._log(f"✓ {name} → {os.path.basename(pdf_path)}")
                ok += 1
            except ConversionError as e:
                self._log(f"❌ {name}: {e}")
                fail += 1
            except Exception as e:  # noqa: BLE001
                self._log(f"❌ {name}: {e}")
                fail += 1

        msg = f"{ok} PDF(s) salvo(s) com sucesso em:\n{folder}"
        if fail:
            msg += f"\n{fail} falharam"
        messagebox.showinfo("Concluído", msg)

    def _print_selected(self):
        self._print_indices(list(self.listbox.curselection()))

    def _print_all(self):
        self._print_indices(list(range(len(self.labels_loaded))))

    def _run_diagnostic(self):
        """
        Manda uma etiqueta mínima em ZPL e outra em TSPL.

        Serve para o caso "não sai nada e nenhum erro aparece": a etiqueta da
        Shopee é ZPL, e uma impressora em modo TSPL ignora ZPL caladamente.
        Ver qual das duas sai no papel identifica a linguagem.
        """
        printer = self.printer_var.get()
        if not printer:
            messagebox.showwarning("Atenção", "Selecione uma impressora antes de testar.")
            return

        if not messagebox.askokcancel(
            "Teste de impressão",
            "Vão sair DUAS etiquetas de teste:\n\n"
            "   1ª — TESTE ZPL\n"
            "   2ª — TESTE TSPL\n\n"
            "Veja qual delas imprimiu:\n\n"
            "• Só a ZPL saiu → a impressora fala ZPL, que é a linguagem da\n"
            "   etiqueta da Shopee. Deveria funcionar.\n"
            "• Só a TSPL saiu → é por isso que a etiqueta da Shopee não sai.\n"
            "• Nenhuma saiu → o problema é o driver não repassar dados RAW.\n\n"
            "Deixe papel na impressora e clique em OK.",
        ):
            return

        results = []
        for language in ("ZPL", "TSPL"):
            try:
                send_test_label(printer, language)
                self._log(f"✓ Teste {language} enviado")
                results.append(f"✓ {language}: enviado sem erro")
            except PrinterError as exc:
                self._log(f"❌ Teste {language}: {exc}")
                results.append(f"❌ {language}: {exc}")
            except Exception as exc:  # noqa: BLE001
                self._log(f"❌ Teste {language}: {exc}")
                results.append(f"❌ {language}: {exc}")

        messagebox.showinfo(
            "Resultado do teste",
            "\n\n".join(results)
            + "\n\nAgora veja o que saiu no papel.\n\n"
            "'Enviado sem erro' quer dizer que o Windows aceitou os bytes — "
            "não que a impressora entendeu. Quem responde isso é o papel.",
        )

    def _show_log_dir(self):
        import subprocess
        import platform
        from .logger import _get_log_dir

        log_dir = _get_log_dir()
        try:
            if os.name == "nt":
                os.startfile(str(log_dir))  # noqa: S606
            elif platform.system() == "Darwin":
                subprocess.run(["open", str(log_dir)], check=True)
            else:
                subprocess.run(["xdg-open", str(log_dir)], check=True)
            self._log(f"Abrindo: {log_dir}")
        except Exception as e:
            self._log(f"Erro ao abrir pasta: {e}")
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta: {e}")


def main():
    app = ShopeePrintApp()
    app.mainloop()


if __name__ == "__main__":
    main()
