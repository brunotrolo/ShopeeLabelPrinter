"""
Shopee Label Printer
====================

Imprime etiquetas de envio da Shopee direto em impressora térmica (modo RAW).
Sem conversão para PDF, sem reamostragem — preserva 100% da resolução original.

**Uso Básico:**

    from shopee_label_printer.parser import load_labels_from_path
    from shopee_label_printer.renderer import render_zpl
    from shopee_label_printer.printer import send_raw_to_printer

    # Carregar etiquetas de um ZIP do Shopee
    labels = load_labels_from_path("labels.zip")

    # Renderizar preview da primeira etiqueta
    render = render_zpl(labels[0][1])
    print(f"Dimensões: {render.width_mm}x{render.height_mm}mm")

    # Enviar para impressora térmica
    send_raw_to_printer(labels[0][1], printer_name="FY-1075")

**Recursos:**

- 📦 Importa: ZIP Shopee, TXT, ZPL, TSPL, PRN
- 🎨 Renderiza: Preview 203 DPI (pixel-perfeito)
- 🖨️ Imprime: ZPL nativo (RAW), TSPL (FY-1075), PDF
- 🔒 Segurança: 100% local, zero dependências externas
- 🌐 Multi-plataforma: Windows (.exe), Web (browser), Python CLI

**Versão:** 0.5.0 (Alpha)
**Status:** Production-ready para v1.0 (em testes finais)
**Autor:** Bruno Trolo <bruno@trolo.dev>
**Licença:** MIT
**GitHub:** https://github.com/brunotrolo/ShopeeLabelPrinter
"""

__version__ = "0.5.0"
__author__ = "Bruno Trolo"
__email__ = "bruno@trolo.dev"
__license__ = "MIT"
__url__ = "https://github.com/brunotrolo/ShopeeLabelPrinter"
