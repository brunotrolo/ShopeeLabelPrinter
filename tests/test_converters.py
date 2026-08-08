"""
Testes para o módulo converters (ZPL -> TSPL, ZPL -> PDF).
"""

import zlib

import pytest

from src.shopee_label_printer.converters import (
    TSPL_BOOST_LEVELS,
    ConversionError,
    _build_pdf,
    _invert_bitmap,
    _pack_bitmap,
    zpl_to_pdf,
    zpl_to_tspl,
)
from src.shopee_label_printer.renderer import render_zpl


def build_dg_label(raw: bytes, bytes_per_row: int, width: int, height: int) -> bytes:
    """Etiqueta ZPL mínima com um gráfico ~DG embutido, igual ao formato real da Shopee."""
    zpl = (
        f"^XA^PW{width}^LL{height}~DGR:IMG.GRF,{len(raw)},{bytes_per_row},{raw.hex().upper()}"
        f"^FO0,0^XGR:IMG.GRF,1,1^FS^XZ"
    )
    return zpl.encode("latin-1")


def diagonal_bitmap(size: int) -> bytes:
    """Bitmap size x size com uma linha diagonal de 1 ponto (fácil de conferir depois)."""
    bytes_per_row = (size + 7) // 8
    rows = bytearray(bytes_per_row * size)
    for y in range(size):
        bit = y % size
        rows[y * bytes_per_row + bit // 8] |= 0x80 >> (bit % 8)
    return bytes(rows), bytes_per_row


TEST_ZPL_WITH_OVERLAY = (
    b"^XA\r\n^FO40,40^A0N,45,45^FDTESTE^FS\r\n^XZ\r\n"
)


class TestPackBitmap:
    def test_repacks_to_the_same_bytes(self):
        raw, bytes_per_row = diagonal_bitmap(16)
        zpl = build_dg_label(raw, bytes_per_row, 16, 16)
        render = render_zpl(zpl)

        packed, width_bytes, height = _pack_bitmap(render)

        assert packed == raw
        assert width_bytes == bytes_per_row
        assert height == 16

    def test_pads_rows_to_byte_boundary(self):
        # 12 pontos de largura -> 2 bytes por linha (16 bits), não 1.5
        raw = bytes([0xFF, 0xF0]) * 4
        zpl = build_dg_label(raw, 2, 12, 4)
        render = render_zpl(zpl)

        packed, width_bytes, height = _pack_bitmap(render)

        assert width_bytes == 2
        assert len(packed) == 2 * 4


class TestZplToTspl:
    def test_produces_bitmap_command_not_printbitmap(self):
        raw, bpr = diagonal_bitmap(16)
        zpl = build_dg_label(raw, bpr, 16, 16)

        tspl = zpl_to_tspl(zpl, render_zpl)

        assert b"BITMAP 0,0,2,16,0," in tspl
        assert b"PRINTBITMAP" not in tspl

    def test_bitmap_data_is_raw_binary_not_hex_text(self):
        """
        O manual TSPL manda os bytes crus depois da última vírgula do
        comando, não uma string hexadecimal — se fosse hex, o byte 0x80
        apareceria como os dois caracteres ASCII '8' e '0' (0x38 0x30).
        A polaridade é invertida para TSPL (0=preto em TSPL vs 1=preto em render).
        """
        raw, bpr = diagonal_bitmap(16)
        zpl = build_dg_label(raw, bpr, 16, 16)

        tspl = zpl_to_tspl(zpl, render_zpl)
        inverted_raw = _invert_bitmap(raw)

        assert inverted_raw in tspl

    def test_includes_print_command(self):
        raw, bpr = diagonal_bitmap(8)
        zpl = build_dg_label(raw, bpr, 8, 8)

        tspl = zpl_to_tspl(zpl, render_zpl)

        assert tspl.rstrip(b"\r\n").endswith(b"PRINT 1,1")

    def test_declares_label_size_from_the_render(self):
        raw, bpr = diagonal_bitmap(16)
        zpl = build_dg_label(raw, bpr, 16, 16)
        render = render_zpl(zpl)

        tspl = zpl_to_tspl(zpl, render_zpl)

        expected = f"SIZE {render.width_mm:.1f} mm,{render.height_mm:.1f} mm".encode()
        assert expected in tspl

    def test_rejects_label_with_vector_overlays(self):
        """
        Uma etiqueta com texto/caixa desenhado fora do bitmap não pode virar
        TSPL silenciosamente incompleto — precisa recusar, não aproximar.
        """
        with pytest.raises(ConversionError):
            zpl_to_tspl(TEST_ZPL_WITH_OVERLAY, render_zpl)

    def test_boost_off_by_default_has_no_density_or_speed(self):
        raw, bpr = diagonal_bitmap(8)
        zpl = build_dg_label(raw, bpr, 8, 8)

        tspl = zpl_to_tspl(zpl, render_zpl)

        assert b"DENSITY" not in tspl
        assert b"SPEED" not in tspl

    @pytest.mark.parametrize("level", ["leve", "medio", "forte"])
    def test_boost_levels_add_density_and_speed_commands(self, level):
        raw, bpr = diagonal_bitmap(8)
        zpl = build_dg_label(raw, bpr, 8, 8)

        tspl = zpl_to_tspl(zpl, render_zpl, boost_level=level)

        density, speed = TSPL_BOOST_LEVELS[level]
        assert f"DENSITY {density}".encode() in tspl
        assert f"SPEED {speed}".encode() in tspl

    def test_boost_commands_come_before_bitmap_data(self):
        """DENSITY/SPEED têm que valer antes do CLS+BITMAP, não depois."""
        raw, bpr = diagonal_bitmap(8)
        zpl = build_dg_label(raw, bpr, 8, 8)

        tspl = zpl_to_tspl(zpl, render_zpl, boost_level="forte")

        assert tspl.index(b"DENSITY") < tspl.index(b"BITMAP")

    def test_real_shopee_three_block_label_converts(self):
        """O formato real (~DG + ^XG + ^ID) precisa converter sem erro."""
        raw, bpr = diagonal_bitmap(8)
        download = f"~DGR:DEMO.GRF,{len(raw)},{bpr},{raw.hex().upper()}"
        printblk = "^XA^MMT,Y^PON^MNY^FO0,0^XGR:DEMO.GRF,1,1^FS^PQ1,0,0,N^XZ"
        cleanup = "^XA^IDR:DEMO.GRF^FS^XZ"
        zpl = (download + printblk + cleanup).encode("latin-1")

        tspl = zpl_to_tspl(zpl, render_zpl)

        assert b"BITMAP" in tspl


class TestZplToPdf:
    def test_produces_valid_pdf_header_and_trailer(self):
        raw, bpr = diagonal_bitmap(16)
        zpl = build_dg_label(raw, bpr, 16, 16)

        pdf = zpl_to_pdf(zpl, render_zpl)

        assert pdf.startswith(b"%PDF-1.4")
        assert pdf.rstrip().endswith(b"%%EOF")

    def test_xref_offsets_point_at_declared_objects(self):
        """Cada offset no xref precisa apontar exatamente para 'N 0 obj'."""
        raw, bpr = diagonal_bitmap(16)
        zpl = build_dg_label(raw, bpr, 16, 16)

        pdf = zpl_to_pdf(zpl, render_zpl)

        xref_pos = pdf.rindex(b"xref")
        xref_section = pdf[xref_pos:]
        # pula "xref", "0 N" e a entrada livre "0000000000 65535 f "
        lines = xref_section.split(b"\n")[3:]

        for i, line in enumerate(lines[:5], start=1):
            if not line.strip() or line.startswith(b"trailer"):
                break
            offset = int(line[:10])
            assert pdf[offset:offset + len(f"{i} 0 obj".encode())] == f"{i} 0 obj".encode()

    def test_embedded_image_stream_length_matches_declared_length(self):
        raw, bpr = diagonal_bitmap(16)
        zpl = build_dg_label(raw, bpr, 16, 16)

        pdf = zpl_to_pdf(zpl, render_zpl)

        # Extrai o /Length declarado do objeto de imagem e confere que bate
        # com o tamanho real do stream comprimido.
        marker = b"/Filter /FlateDecode /Length "
        start = pdf.index(marker) + len(marker)
        end = pdf.index(b" >>", start)
        declared_length = int(pdf[start:end])

        stream_start = pdf.index(b"stream\n", end) + len(b"stream\n")
        stream_end = pdf.index(b"\nendstream", stream_start)
        actual_length = stream_end - stream_start

        assert declared_length == actual_length
        # E o conteúdo tem que descomprimir de volta pro bitmap original.
        assert zlib.decompress(pdf[stream_start:stream_end]) == raw

    def test_rejects_label_with_vector_overlays(self):
        with pytest.raises(ConversionError):
            zpl_to_pdf(TEST_ZPL_WITH_OVERLAY, render_zpl)

    def test_can_save_to_disk(self, tmp_path):
        raw, bpr = diagonal_bitmap(8)
        zpl = build_dg_label(raw, bpr, 8, 8)
        output = tmp_path / "etiqueta.pdf"

        zpl_to_pdf(zpl, render_zpl, output_path=str(output))

        assert output.exists()
        assert output.read_bytes().startswith(b"%PDF-1.4")


class TestBuildPdfDecodePolarity:
    def test_bit_one_decodes_to_black(self):
        """
        render.pixels usa 1 = preto. /Decode [1 0] no PDF precisa inverter a
        tabela padrão do DeviceGray para que a amostra 1 vire componente 0
        (preto) — senão a etiqueta sai em negativo.
        """
        packed = bytes([0b10000000])  # 1 pixel preto, 7 brancos
        pdf = _build_pdf(1.0, 1.0, 8, 1, packed)

        assert b"/Decode [1 0]" in pdf
        assert b"/ColorSpace /DeviceGray" in pdf
        assert b"/BitsPerComponent 1" in pdf
