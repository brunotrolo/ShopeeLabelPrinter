"""
Conversores de formato: ZPL → TSPL e ZPL → PDF.

O ZPL (Zebra Programming Language) é o formato das etiquetas da Shopee.
TSPL é a linguagem nativa de impressoras térmicas como a FY-1075.
PDF é para guardar ou imprimir por outro caminho (driver do sistema).

Os dois caminhos partem do mesmo bitmap que o preview usa (renderer.py):
a etiqueta real da Shopee traz o desenho inteiro embutido como imagem
(~DG/^GFA), então o bitmap decodificado já é a etiqueta completa — não
precisa reinterpretar texto, caixa ou código de barra.

Sem dependência externa nenhuma (mesmo princípio do resto do projeto):
o PDF é montado a mão, objeto por objeto, comprimindo o bitmap com zlib
(stdlib) — não precisa de Pillow nem reportlab, e o .exe não muda de tamanho.
"""

import logging
import zlib

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Erro na conversão entre formatos."""
    pass


def _render_or_raise(zpl_data: bytes, renderer_func):
    """
    Renderiza o ZPL e recusa etiquetas que dependem de elementos vetoriais
    (texto/caixa/código desenhados por cima, não embutidos no bitmap).

    O preview consegue aproximar esses elementos na tela, mas TSPL/PDF
    precisam de um raster só — desenhar por cima exigiria reimplementar
    fonte e código de barras nesse raster, e uma aproximação errada sairia
    impressa sem ninguém perceber. Melhor recusar do que entregar etiqueta
    incompleta.
    """
    from .renderer import RenderError

    try:
        render = renderer_func(zpl_data)
    except RenderError as e:
        raise ConversionError(f"Não foi possível interpretar a etiqueta: {e}")

    if render.overlays:
        raise ConversionError(
            "Esta etiqueta tem elementos desenhados por fora da imagem embutida "
            "(texto, caixa ou código de barras) — a conversão só é confiável para "
            "etiquetas onde tudo já vem como imagem, como as da Shopee. "
            "Envie em ZPL direto para não arriscar perder esses elementos."
        )

    return render


def _pack_bitmap(render) -> tuple[bytes, int, int]:
    """
    Empacota render.pixels (1 byte por pixel, 1 = preto) em bits MSB-first,
    uma linha começando sempre num byte novo — formato binário que tanto o
    comando TSPL BITMAP quanto uma imagem PDF de 1 bit esperam.

    Returns:
        (bytes empacotados, largura em bytes, altura em pontos)
    """
    width, height = render.width, render.height
    pixels = render.pixels
    bytes_per_row = (width + 7) // 8

    packed = bytearray(bytes_per_row * height)
    for y in range(height):
        row_pixel_base = y * width
        row_byte_base = y * bytes_per_row
        for x in range(width):
            if pixels[row_pixel_base + x]:
                packed[row_byte_base + (x >> 3)] |= 0x80 >> (x & 7)

    return bytes(packed), bytes_per_row, height


def _invert_bitmap(bitmap_bytes: bytes) -> bytes:
    """
    Inverte a polaridade do bitmap: XOR com 0xFF para flipping de todos os bits.
    Necessário para TSPL (FY-1075), cuja convenção é oposta à do render.pixels.

    No render: 1 = preto (black)
    Em TSPL: 0 = preto, 1 = branco (white) — polaridade invertida
    """
    return bytes(b ^ 0xFF for b in bitmap_bytes)


# Reforço de impressão em TSPL: DENSITY (0-15, padrão 8) e SPEED (pol/s).
# Equivalente ao PRINT_BOOST_LEVELS do ZPL (^MD/^PR, em printer.py), mas na
# escala e nos comandos que o TSPL usa — ^MD/^PR não existem em TSPL, então
# não dá pra reaproveitar apply_print_boost() depois de converter.
TSPL_BOOST_LEVELS = {
    "desligado": (None, None),
    "leve": (12, 2),
    "medio": (15, 2),
    "forte": (15, 1),
}


def zpl_to_tspl(
    zpl_data: bytes,
    renderer_func,
    boost_level: str = "desligado",
    custom_density: int = None,
    custom_speed: int = None,
) -> bytes:
    """
    Converte ZPL para TSPL, desenhando o bitmap decodificado com o comando
    BITMAP (TSPL/TSPL2 Programming Manual, TSC): sintaxe
    ``BITMAP x,y,largura_em_bytes,altura_em_pontos,modo,<dados binários>``,
    com 1 bit = 1 ponto preto e dados enviados crus (não em hex/texto) logo
    depois da vírgula final.

    Nota: TSPL usa polaridade oposta à do render (render: 1=preto, TSPL: 0=preto),
    então o bitmap é invertido automaticamente antes do envio.

    Args:
        zpl_data: Bytes da etiqueta em ZPL
        renderer_func: render_zpl(data) -> LabelRender
        boost_level: uma das chaves de TSPL_BOOST_LEVELS ou "customizado"
        custom_density: DENSITY (0-15) quando boost_level="customizado"
        custom_speed: SPEED (pol/s) quando boost_level="customizado"

    Returns:
        Bytes da etiqueta em TSPL, prontos para envio RAW

    Raises:
        ConversionError: Se não conseguir converter com segurança
    """
    try:
        logger.info("Iniciando conversão ZPL → TSPL")
        render = _render_or_raise(zpl_data, renderer_func)
        logger.info("Etiqueta renderizada: %.1f × %.1f mm", render.width_mm, render.height_mm)

        bitmap_bytes, width_bytes, height_dots = _pack_bitmap(render)
        logger.info("Bitmap empacotado: %d bytes/linha, %d pontos altura", width_bytes, height_dots)

        bitmap_bytes = _invert_bitmap(bitmap_bytes)
        logger.debug("Polaridade do bitmap invertida para TSPL")

        if boost_level == "customizado":
            # Validar parâmetros customizados
            if custom_density is not None and not (0 <= custom_density <= 15):
                raise ConversionError(
                    f"custom_density deve estar entre 0-15, recebido: {custom_density}"
                )
            if custom_speed is not None and custom_speed <= 0:
                raise ConversionError(
                    f"custom_speed deve ser positivo, recebido: {custom_speed}"
                )
            density, speed = custom_density, custom_speed
            logger.info("Usando parâmetros customizados: density=%s, speed=%s", density, speed)
        else:
            density, speed = TSPL_BOOST_LEVELS.get(boost_level, (None, None))
            logger.info("Usando preset de reforço: %s", boost_level)

        boost_commands = ""
        if speed is not None:
            boost_commands += f"SPEED {speed}\r\n"
        if density is not None:
            boost_commands += f"DENSITY {density}\r\n"

        header = (
            f"SIZE {render.width_mm:.1f} mm,{render.height_mm:.1f} mm\r\n"
            "GAP 3 mm,0 mm\r\n"
            "DIRECTION 1\r\n"
            f"{boost_commands}"
            "CLS\r\n"
            f"BITMAP 0,0,{width_bytes},{height_dots},0,"
        ).encode("ascii")

        tspl_output = header + bitmap_bytes + b"\r\nPRINT 1,1\r\n"
        logger.info("Conversão concluída: %d bytes TSPL", len(tspl_output))
        return tspl_output

    except ConversionError:
        raise
    except Exception as e:
        logger.error("Erro ao converter ZPL para TSPL: %s", str(e))
        raise ConversionError(f"Erro ao converter ZPL para TSPL: {str(e)}")


def _build_pdf(width_mm: float, height_mm: float, width_px: int, height_px: int,
                packed_bits: bytes) -> bytes:
    """
    Monta um PDF de uma página só, com uma imagem 1-bit (DeviceGray) ocupando
    a página inteira — sem biblioteca nenhuma, só a estrutura do formato PDF
    e zlib para comprimir o bitmap.

    1 bit por ponto, mesma amostra que já vem de _pack_bitmap. `/Decode [1 0]`
    inverte a tabela padrão do DeviceGray: bit 1 (preto no nosso render) vira
    componente 0 (preto no PDF); sem isso a etiqueta sairia em negativo.
    """
    compressed = zlib.compress(packed_bits, level=6)

    # 1 mm = 72/25.4 pontos PDF
    width_pt = width_mm * 72.0 / 25.4
    height_pt = height_mm * 72.0 / 25.4

    content_stream = (
        f"q\n{width_pt:.2f} 0 0 {height_pt:.2f} 0 0 cm\n/Im0 Do\nQ\n"
    ).encode("ascii")

    obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
    obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    obj3 = (
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width_pt:.2f} {height_pt:.2f}] "
        f"/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>"
    ).encode("ascii")
    obj4 = (
        f"<< /Length {len(content_stream)} >>\nstream\n".encode("ascii")
        + content_stream
        + b"\nendstream"
    )
    obj5 = (
        (
            f"<< /Type /XObject /Subtype /Image /Width {width_px} /Height {height_px} "
            f"/ColorSpace /DeviceGray /BitsPerComponent 1 /Decode [1 0] "
            f"/Filter /FlateDecode /Length {len(compressed)} >>\nstream\n"
        ).encode("ascii")
        + compressed
        + b"\nendstream"
    )

    objects = [obj1, obj2, obj3, obj4, obj5]

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (len(objects) + 1)
    for i, body in enumerate(objects, start=1):
        offsets[i] = len(out)
        out += f"{i} 0 obj\n".encode("ascii")
        out += body
        out += b"\nendobj\n"

    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for i in range(1, len(objects) + 1):
        out += f"{offsets[i]:010d} 00000 n \n".encode("ascii")

    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    ).encode("ascii")

    return bytes(out)


def zpl_to_pdf(zpl_data: bytes, renderer_func, output_path: str = None) -> bytes:
    """
    Converte ZPL para PDF no tamanho físico exato da etiqueta.

    Args:
        zpl_data: Bytes da etiqueta em ZPL
        renderer_func: render_zpl(data) -> LabelRender
        output_path: Caminho opcional para salvar em disco

    Returns:
        Bytes do PDF

    Raises:
        ConversionError: Se não conseguir converter com segurança
    """
    try:
        logger.info("Iniciando conversão ZPL → PDF")
        render = _render_or_raise(zpl_data, renderer_func)
        logger.info("Etiqueta renderizada: %.1f × %.1f mm", render.width_mm, render.height_mm)

        packed_bits, _width_bytes, _height = _pack_bitmap(render)
        logger.debug("Bitmap empacotado para PDF")

        logger.info("Montando estrutura PDF")
        pdf_bytes = _build_pdf(
            render.width_mm, render.height_mm, render.width, render.height, packed_bits
        )

        if output_path:
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)
            logger.info("PDF salvo em: %s (%d bytes)", output_path, len(pdf_bytes))
        else:
            logger.info("PDF gerado: %d bytes", len(pdf_bytes))

        return pdf_bytes

    except ConversionError:
        raise
    except Exception as e:
        logger.error("Erro ao converter ZPL para PDF: %s", str(e))
        raise ConversionError(f"Erro ao converter ZPL para PDF: {str(e)}")
