"""
Testes para o módulo renderer (preview de etiquetas).
"""

import base64
import zlib

import pytest

from src.shopee_label_printer.renderer import (
    LabelRender,
    RenderError,
    decode_graphic_data,
    downsample,
    encode_code128,
    render_to_ppm,
    render_zpl,
    tokenize_zpl,
    unpack_bitmap,
)


def build_dg_label(raw: bytes, bytes_per_row: int) -> bytes:
    """Monta uma etiqueta ZPL mínima com um gráfico ~DG embutido."""
    zpl = (
        f"^XA~DGR:IMG.GRF,{len(raw)},{bytes_per_row},{raw.hex().upper()}"
        f"^FO0,0^XGR:IMG.GRF,1,1^FS^XZ"
    )
    return zpl.encode("latin-1")


class TestDecodeGraphicData:
    """Decodificação dos três formatos de campo gráfico da ZPL."""

    def test_plain_hex(self):
        assert decode_graphic_data("DEADBEEF", 2, 4) == bytes([0xDE, 0xAD, 0xBE, 0xEF])

    def test_lowercase_hex_is_accepted(self):
        assert decode_graphic_data("deadbeef", 2, 4) == bytes([0xDE, 0xAD, 0xBE, 0xEF])

    def test_repeat_code_uppercase(self):
        # 'J' = 4 repetições do 'F' seguinte -> FFFF -> 2 bytes
        assert decode_graphic_data("JF", 2, 2) == bytes([0xFF, 0xFF])

    def test_repeat_code_lowercase_is_multiple_of_20(self):
        # 'g' = 20 repetições
        result = decode_graphic_data("g0", 10, 10)
        assert result == bytes(10)

    def test_repeat_codes_are_additive(self):
        # 'gG' = 20 + 1 = 21 nibbles... usa linha de 11 bytes (22 nibbles)
        result = decode_graphic_data("gGF0", 11, 11)
        assert result[0] == 0xFF

    def test_comma_fills_row_with_white(self):
        assert decode_graphic_data(",", 2, 2) == bytes([0x00, 0x00])

    def test_bang_fills_row_with_black(self):
        assert decode_graphic_data("!", 2, 2) == bytes([0xFF, 0xFF])

    def test_colon_repeats_previous_row(self):
        # linha preta, depois repete
        assert decode_graphic_data("!:", 2, 4) == bytes([0xFF, 0xFF, 0xFF, 0xFF])

    def test_z64_roundtrip(self):
        raw = bytes([0x12, 0x34, 0x56, 0x78])
        payload = base64.b64encode(zlib.compress(raw)).decode()
        assert decode_graphic_data(f":Z64:{payload}:9999", 2, 4) == raw

    def test_b64_roundtrip(self):
        raw = bytes([0x12, 0x34, 0x56, 0x78])
        payload = base64.b64encode(raw).decode()
        assert decode_graphic_data(f":B64:{payload}:9999", 2, 4) == raw

    def test_incomplete_row_is_padded(self):
        # 3 nibbles numa linha de 2 bytes: completa com zero
        assert decode_graphic_data("FFF", 2, 2) == bytes([0xFF, 0xF0])

    def test_truncates_to_total_bytes(self):
        assert decode_graphic_data("FFFFFFFF", 2, 2) == bytes([0xFF, 0xFF])

    def test_invalid_bytes_per_row(self):
        with pytest.raises(RenderError):
            decode_graphic_data("FF", 0, 1)

    def test_unknown_scheme_raises(self):
        with pytest.raises(RenderError):
            decode_graphic_data(":X99:abcd:1", 2, 2)

    def test_corrupt_z64_raises(self):
        payload = base64.b64encode(b"nao eh zlib").decode()
        with pytest.raises(RenderError):
            decode_graphic_data(f":Z64:{payload}:1", 2, 4)


class TestUnpackBitmap:
    """Bits empacotados -> 1 byte por pixel."""

    def test_dimensions(self):
        bitmap = unpack_bitmap(bytes([0xFF, 0x00, 0x00, 0xFF]), 2)
        assert bitmap.width == 16
        assert bitmap.height == 2

    def test_bit_order_is_msb_first(self):
        bitmap = unpack_bitmap(bytes([0x80]), 1)
        assert bitmap.pixels[0] == 1
        assert bitmap.pixels[1] == 0

    def test_all_black_row(self):
        bitmap = unpack_bitmap(bytes([0xFF]), 1)
        assert list(bitmap.pixels) == [1] * 8

    def test_get_out_of_bounds_returns_zero(self):
        bitmap = unpack_bitmap(bytes([0xFF]), 1)
        assert bitmap.get(-1, 0) == 0
        assert bitmap.get(99, 0) == 0


class TestTokenizeZpl:
    """Quebra do fluxo ZPL em comandos."""

    def test_basic_commands(self):
        tokens = tokenize_zpl("^XA^FO10,20^FS^XZ")
        names = [name for name, _ in tokens]
        assert names == ["^XA", "^FO", "^FS", "^XZ"]

    def test_field_data_is_literal_until_fs(self):
        tokens = dict(tokenize_zpl("^FDRua ^ Numero 10^FS"))
        assert tokens["^FD"] == "Rua ^ Numero 10"

    def test_single_letter_command_keeps_designator_in_params(self):
        tokens = dict(tokenize_zpl("^A0N,30,20"))
        assert tokens["^A"] == "0N,30,20"

    def test_tilde_commands_are_recognized(self):
        tokens = tokenize_zpl("~DGR:A.GRF,4,2,FFFF")
        assert tokens[0][0] == "~DG"

    def test_unterminated_field_data_does_not_crash(self):
        tokens = dict(tokenize_zpl("^FDsem fim"))
        assert tokens["^FD"] == "sem fim"


class TestRenderZpl:
    """Render completo de etiquetas."""

    def test_embedded_bitmap_is_decoded(self):
        raw = bytes([0xFF, 0x00, 0x00, 0xFF])
        render = render_zpl(build_dg_label(raw, 2), default_width=16, default_height=2)

        assert render.has_bitmap
        assert render.width == 16
        assert render.height == 2
        # primeira linha: 8 pretos, 8 brancos
        assert list(render.pixels[0:8]) == [1] * 8
        assert list(render.pixels[8:16]) == [0] * 8

    def test_graphic_without_xg_is_still_previewed(self):
        # A Shopee costuma mandar ~DG sem ^XG — precisa aparecer mesmo assim.
        raw = bytes([0xFF, 0xFF])
        zpl = f"^XA~DGR:IMG.GRF,2,2,{raw.hex().upper()}^XZ".encode("latin-1")
        render = render_zpl(zpl, default_width=16, default_height=1)
        assert render.has_bitmap
        assert sum(render.pixels) == 16

    def test_graphic_field_gf_command(self):
        raw = bytes([0xFF, 0xFF])
        zpl = f"^XA^FO0,0^GFA,2,2,2,{raw.hex().upper()}^FS^XZ".encode("latin-1")
        render = render_zpl(zpl, default_width=16, default_height=1)
        assert render.has_bitmap
        assert sum(render.pixels) == 16

    def test_field_origin_offsets_the_bitmap(self):
        raw = bytes([0xFF])
        zpl = f"^XA~DGR:A.GRF,1,1,{raw.hex().upper()}^FO8,1^XGR:A.GRF,1,1^FS^XZ"
        render = render_zpl(zpl.encode("latin-1"), default_width=16, default_height=2)
        assert list(render.pixels[0:16]) == [0] * 16
        assert list(render.pixels[16:24]) == [0] * 8
        assert list(render.pixels[24:32]) == [1] * 8

    def test_print_width_and_length_define_size(self):
        render = render_zpl(b"^XA^PW600^LL900^FO0,0^FDoi^FS^XZ")
        assert render.width == 600
        assert render.height == 900

    def test_print_width_crops_bitmap_padding(self):
        # 812 pontos ocupam 102 bytes/linha = 816 bits; os 4 bits de sobra
        # são preenchimento e não podem virar margem no preview.
        raw = bytes([0xFF] * 102)
        zpl = (
            f"^XA^PW812^LL1218~DGR:A.GRF,102,102,{raw.hex().upper()}"
            f"^FO0,0^XGR:A.GRF,1,1^FS^XZ"
        )
        render = render_zpl(zpl.encode("latin-1"))
        assert render.width == 812
        assert render.height == 1218

    def test_defaults_to_4x6_inches_at_203dpi(self):
        render = render_zpl(b"^XA^FO0,0^FDoi^FS^XZ")
        assert render.width == 812
        assert render.height == 1218
        assert round(render.width_mm) == 102
        assert round(render.height_mm) == 152

    def test_text_becomes_overlay(self):
        render = render_zpl(b"^XA^A0N,40,30^FO10,20^FDJoao da Silva^FS^XZ")
        texts = [o for o in render.overlays if o.kind == "text"]
        assert len(texts) == 1
        assert texts[0].data == "Joao da Silva"
        assert texts[0].font_height == 40

    def test_box_becomes_overlay(self):
        render = render_zpl(b"^XA^FO5,5^GB100,50,3^FS^XZ")
        boxes = [o for o in render.overlays if o.kind == "box"]
        assert len(boxes) == 1
        assert (boxes[0].width, boxes[0].height, boxes[0].thickness) == (100, 50, 3)

    def test_barcode_becomes_overlay_with_modules(self):
        render = render_zpl(b"^XA^BY2^FO10,10^BCN,80,Y,N,N^FD12345678^FS^XZ")
        barcodes = [o for o in render.overlays if o.kind == "barcode"]
        assert len(barcodes) == 1
        assert barcodes[0].data == "12345678"
        assert barcodes[0].modules

    def test_label_home_shifts_origin(self):
        raw = bytes([0xFF])
        zpl = f"^XA^LH8,0~DGR:A.GRF,1,1,{raw.hex().upper()}^FO0,0^XGR:A.GRF,1,1^FS^XZ"
        render = render_zpl(zpl.encode("latin-1"), default_width=16, default_height=1)
        assert list(render.pixels[0:8]) == [0] * 8
        assert list(render.pixels[8:16]) == [1] * 8

    def test_malformed_graphic_is_skipped_not_fatal(self):
        render = render_zpl(b"^XA~DGR:A.GRF,bad^FO0,0^FDok^FS^XZ")
        assert not render.has_bitmap
        assert any(o.kind == "text" for o in render.overlays)

    def test_bytes_are_never_mutated(self):
        raw = bytes([0xAA, 0x55])
        original = build_dg_label(raw, 2)
        copy = bytes(original)
        render_zpl(original)
        assert original == copy


class TestCode128:
    """Codificação Code 128 usada no preview do código de barras."""

    def test_empty_returns_no_bars(self):
        assert encode_code128("") == []

    def test_numeric_uses_subset_c(self):
        # subset C: start + 4 pares + checksum = 6 simbolos de 6 barras, + stop de 7
        widths = encode_code128("12345678")
        assert len(widths) == 6 * 6 + 7

    def test_alphanumeric_uses_subset_b(self):
        widths = encode_code128("SP123")
        # start + 5 chars + checksum = 7 simbolos de 6 + stop de 7
        assert len(widths) == 7 * 6 + 7

    def test_all_widths_are_positive(self):
        assert all(w > 0 for w in encode_code128("BR987654321"))

    def test_odd_digits_fall_back_to_subset_b(self):
        widths = encode_code128("123")
        assert len(widths) == 5 * 6 + 7


class TestDownsample:
    """Redução por média de área para caber na tela."""

    def _solid_render(self, width, height, value=1):
        return LabelRender(
            width=width,
            height=height,
            pixels=bytearray([value] * (width * height)),
        )

    def test_factor_one_inverts_to_grayscale(self):
        width, height, gray = downsample(self._solid_render(2, 2), 1)
        assert (width, height) == (2, 2)
        assert list(gray) == [0, 0, 0, 0]  # preto

    def test_white_stays_white(self):
        _width, _height, gray = downsample(self._solid_render(2, 2, value=0), 1)
        assert list(gray) == [255] * 4

    def test_area_average_produces_midtone(self):
        # tabuleiro 2x2 com metade preta -> cinza médio
        render = LabelRender(width=2, height=2, pixels=bytearray([1, 0, 0, 1]))
        width, height, gray = downsample(render, 2)
        assert (width, height) == (1, 1)
        assert 100 < gray[0] < 160

    def test_output_dimensions_shrink_by_factor(self):
        width, height, _ = downsample(self._solid_render(90, 60), 3)
        assert (width, height) == (30, 20)

    def test_thin_line_survives_as_gray(self):
        # linha de 1 ponto num bloco 4x4 não pode sumir
        render = LabelRender(width=4, height=4, pixels=bytearray(16))
        for y in range(4):
            render.pixels[y * 4] = 1
        _, _, gray = downsample(render, 4)
        assert gray[0] < 255


class TestPpmOutput:
    """Saída PPM consumida pelo tkinter."""

    def test_header_and_size(self):
        render = LabelRender(width=4, height=4, pixels=bytearray(16))
        ppm = render_to_ppm(render, factor=1)
        assert ppm.startswith(b"P6\n4 4\n255\n")
        assert len(ppm) == len(b"P6\n4 4\n255\n") + 4 * 4 * 3

    def test_black_pixel_is_zero_triplet(self):
        render = LabelRender(width=1, height=1, pixels=bytearray([1]))
        ppm = render_to_ppm(render, factor=1)
        assert ppm[-3:] == b"\x00\x00\x00"

    def test_white_pixel_is_255_triplet(self):
        render = LabelRender(width=1, height=1, pixels=bytearray([0]))
        ppm = render_to_ppm(render, factor=1)
        assert ppm[-3:] == b"\xff\xff\xff"
