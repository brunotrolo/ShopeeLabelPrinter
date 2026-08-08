"""
Renderizador de etiquetas ZPL/TSPL para preview.

Princípio: este módulo NUNCA altera os bytes que vão para a impressora.
Ele só *lê* a etiqueta e reconstrói uma imagem para exibição na tela.
O envio RAW continua usando os bytes originais (ver printer.py).

A etiqueta da Shopee traz o desenho embutido como bitmap (~DG / ^GFA).
Decodificando esse bitmap obtemos o preview na resolução nativa da
impressora — 203 DPI, 1 pixel da imagem = 1 ponto impresso.
"""

import base64
import binascii
import re
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# FY-1075: 203 DPI (8 pontos por mm). Etiqueta padrão 100x150mm.
DEFAULT_DPI = 203
DEFAULT_WIDTH_DOTS = 812      # 4" * 203
DEFAULT_HEIGHT_DOTS = 1218    # 6" * 203

_HEX_DIGITS = set("0123456789ABCDEFabcdef")


class RenderError(Exception):
    """Erro ao renderizar o preview de uma etiqueta."""


@dataclass
class Bitmap:
    """Bitmap 1 bit por pixel já desempacotado: 1 byte por pixel, 1 = preto."""

    width: int
    height: int
    pixels: bytearray

    def get(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.pixels[y * self.width + x]
        return 0


@dataclass
class Overlay:
    """Elemento vetorial desenhado por cima do bitmap (texto, caixa, código)."""

    kind: str                      # "text" | "box" | "barcode" | "qr"
    x: int
    y: int
    data: str = ""
    width: int = 0
    height: int = 0
    thickness: int = 1
    font_height: int = 20
    font_width: int = 0
    rotation: int = 0
    inverted: bool = False
    modules: List[int] = field(default_factory=list)  # barras do Code 128


@dataclass
class LabelRender:
    """Resultado do render: bitmap de fundo + elementos vetoriais."""

    width: int
    height: int
    dpi: int = DEFAULT_DPI
    pixels: bytearray = field(default_factory=bytearray)
    overlays: List[Overlay] = field(default_factory=list)
    has_bitmap: bool = False

    @property
    def width_mm(self) -> float:
        return self.width / self.dpi * 25.4

    @property
    def height_mm(self) -> float:
        return self.height / self.dpi * 25.4


# ---------------------------------------------------------------------------
# Decodificação dos dados gráficos (~DG / ^GFA)
# ---------------------------------------------------------------------------

def decode_graphic_data(data: str, bytes_per_row: int, total_bytes: int) -> bytes:
    """
    Decodifica o campo de dados de um ~DG ou ^GFA.

    Suporta os três formatos que a ZPL aceita:
      - hexadecimal puro
      - hexadecimal com compressão ASCII (G-Y, g-z, ',', '!', ':')
      - :Z64:<base64 zlib>:<crc>  e  :B64:<base64>:<crc>

    Retorna os bytes crus do bitmap (bits empacotados, 1 = ponto preto).
    """
    if bytes_per_row <= 0:
        raise RenderError("bytes por linha inválido no campo gráfico")

    stripped = data.strip()

    # Formato B64/Z64 usado quando a etiqueta vem comprimida.
    if stripped.startswith(":"):
        return _decode_base64_variant(stripped)

    return _decode_compressed_hex(stripped, bytes_per_row, total_bytes)


def _decode_base64_variant(data: str) -> bytes:
    parts = data.split(":")
    # [""], ["", "Z64", "<payload>", "<crc>"]
    if len(parts) < 3:
        raise RenderError("campo gráfico B64/Z64 malformado")

    scheme = parts[1].upper()
    payload = parts[2]

    try:
        raw = base64.b64decode(payload)
    except (binascii.Error, ValueError) as exc:
        raise RenderError(f"base64 inválido no campo gráfico: {exc}")

    if scheme == "Z64":
        try:
            raw = zlib.decompress(raw)
        except zlib.error as exc:
            raise RenderError(f"falha ao descomprimir campo gráfico Z64: {exc}")
    elif scheme != "B64":
        raise RenderError(f"esquema de codificação gráfica não suportado: {scheme}")

    return raw


def _decode_compressed_hex(data: str, bytes_per_row: int, total_bytes: int) -> bytes:
    """
    Decodifica hex com o esquema de compressão ASCII da ZPL.

    Códigos de repetição:
      G..Y -> 1..19        g..z -> 20,40,...,400   (somam entre si: 'hG' = 41)
    Códigos de linha:
      ','  -> completa a linha com zeros (branco)
      '!'  -> completa a linha com 0xFF (preto)
      ':'  -> repete a linha anterior
    """
    nibbles_per_row = bytes_per_row * 2
    out = bytearray()
    row = bytearray()
    prev_row: Optional[bytes] = None
    repeat = 0

    for char in data:
        if char in " \t\r\n":
            continue

        if "G" <= char <= "Y":
            repeat += ord(char) - ord("G") + 1
            continue
        if "g" <= char <= "z":
            repeat += (ord(char) - ord("g") + 1) * 20
            continue

        if char == ",":
            row.extend(b"0" * (nibbles_per_row - len(row)))
        elif char == "!":
            row.extend(b"F" * (nibbles_per_row - len(row)))
        elif char == ":":
            row = bytearray(prev_row if prev_row is not None else b"0" * nibbles_per_row)
        elif char in _HEX_DIGITS:
            row.extend(char.upper().encode("ascii") * (repeat or 1))
        else:
            # Caractere fora do alfabeto do campo gráfico: ignora.
            repeat = 0
            continue

        repeat = 0

        while len(row) >= nibbles_per_row:
            full = bytes(row[:nibbles_per_row])
            out.extend(bytes.fromhex(full.decode("ascii")))
            prev_row = full
            del row[:nibbles_per_row]

    if row:  # última linha incompleta: completa com branco
        row.extend(b"0" * (nibbles_per_row - len(row)))
        out.extend(bytes.fromhex(bytes(row).decode("ascii")))

    if total_bytes > 0:
        if len(out) > total_bytes:
            del out[total_bytes:]
        elif len(out) < total_bytes:
            out.extend(b"\x00" * (total_bytes - len(out)))

    return bytes(out)


def unpack_bitmap(raw: bytes, bytes_per_row: int) -> Bitmap:
    """Converte bits empacotados em um Bitmap de 1 byte por pixel."""
    if bytes_per_row <= 0:
        raise RenderError("bytes por linha inválido")

    height = len(raw) // bytes_per_row
    width = bytes_per_row * 8
    pixels = bytearray(width * height)

    for y in range(height):
        base = y * bytes_per_row
        out_base = y * width
        for bx in range(bytes_per_row):
            byte = raw[base + bx]
            if not byte:
                continue
            px = out_base + bx * 8
            for bit in range(8):
                if byte & (0x80 >> bit):
                    pixels[px + bit] = 1

    return Bitmap(width=width, height=height, pixels=pixels)


# ---------------------------------------------------------------------------
# Tokenização do fluxo ZPL
# ---------------------------------------------------------------------------

def tokenize_zpl(text: str) -> List[Tuple[str, str]]:
    """
    Quebra o fluxo ZPL em (comando, parâmetros).

    O comando é o prefixo '^' ou '~' seguido de até 2 letras. Os parâmetros
    vão até o próximo '^' ou '~' — exceto em ^FD, cujo conteúdo é literal e
    só termina em ^FS.
    """
    tokens: List[Tuple[str, str]] = []
    i = 0
    n = len(text)

    while i < n:
        char = text[i]
        if char not in "^~":
            i += 1
            continue

        j = i + 1
        name = ""
        while j < n and len(name) < 2 and text[j].isalpha():
            name += text[j].upper()
            j += 1

        if not name:
            i += 1
            continue

        command = char + name

        if command in ("^FD", "^FV"):
            end = text.find("^FS", j)
            if end == -1:
                end = n
            tokens.append((command, text[j:end]))
            i = end
        else:
            k = j
            while k < n and text[k] not in "^~":
                k += 1
            tokens.append((command, text[j:k]))
            i = k

    return tokens


def _int_arg(parts: List[str], index: int, default: int = 0) -> int:
    if index >= len(parts):
        return default
    match = re.match(r"\s*(-?\d+)", parts[index])
    return int(match.group(1)) if match else default


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------

def render_zpl(
    data: bytes,
    dpi: int = DEFAULT_DPI,
    default_width: int = DEFAULT_WIDTH_DOTS,
    default_height: int = DEFAULT_HEIGHT_DOTS,
) -> LabelRender:
    """
    Reconstrói a etiqueta como imagem na resolução nativa da impressora.

    1 pixel do resultado = 1 ponto impresso (203 DPI na FY-1075), que é a
    máxima resolução que a impressora consegue produzir.
    """
    text = data.decode("latin-1") if isinstance(data, (bytes, bytearray)) else data
    tokens = tokenize_zpl(text)

    stored: Dict[str, Bitmap] = {}
    placed: List[Tuple[int, int, Bitmap]] = []
    overlays: List[Overlay] = []

    width = default_width
    height = default_height
    explicit_width = False
    explicit_height = False
    max_x = 0
    max_y = 0

    home_x = home_y = 0
    cur_x = cur_y = 0
    font_h, font_w = 20, 0
    barcode_h, barcode_w = 50, 2
    inverted = False
    pending: Optional[Overlay] = None

    for command, params in tokens:
        parts = params.split(",")

        if command == "^PW":
            value = _int_arg(parts, 0)
            if value > 0:
                width = value
                explicit_width = True

        elif command == "^LL":
            value = _int_arg(parts, 0)
            if value > 0:
                height = value
                explicit_height = True

        elif command == "^LH":
            home_x, home_y = _int_arg(parts, 0), _int_arg(parts, 1)

        elif command in ("^FO", "^FT"):
            cur_x = home_x + _int_arg(parts, 0)
            cur_y = home_y + _int_arg(parts, 1)
            inverted = False

        elif command == "^FR":
            inverted = True

        elif command == "^A":
            # ^A0N,30,20 -> designador de fonte, orientação, altura, largura
            font_h = _int_arg(parts, 1, 20) or 20
            font_w = _int_arg(parts, 2, 0)

        elif command == "^BY":
            barcode_w = _int_arg(parts, 0, 2) or 2
            barcode_h = _int_arg(parts, 2, barcode_h) or barcode_h

        elif command == "^BC":
            height_arg = _int_arg(parts, 1, 0)
            pending = Overlay(
                kind="barcode",
                x=cur_x,
                y=cur_y,
                height=height_arg or barcode_h,
                thickness=barcode_w,
            )

        elif command == "^BQ":
            pending = Overlay(kind="qr", x=cur_x, y=cur_y, thickness=_int_arg(parts, 2, 3) or 3)

        elif command == "^GB":
            box_w = _int_arg(parts, 0)
            box_h = _int_arg(parts, 1)
            thick = _int_arg(parts, 2, 1) or 1
            overlays.append(
                Overlay(kind="box", x=cur_x, y=cur_y, width=box_w, height=box_h, thickness=thick)
            )
            max_x = max(max_x, cur_x + box_w)
            max_y = max(max_y, cur_y + box_h)

        elif command in ("^FD", "^FV"):
            value = params
            if pending is not None:
                pending.data = value
                if pending.kind == "barcode":
                    pending.modules = encode_code128(value)
                overlays.append(pending)
                max_x = max(max_x, pending.x + len(pending.modules) * pending.thickness)
                max_y = max(max_y, pending.y + pending.height)
                pending = None
            elif value.strip():
                overlays.append(
                    Overlay(
                        kind="text",
                        x=cur_x,
                        y=cur_y,
                        data=value,
                        font_height=font_h,
                        font_width=font_w or int(font_h * 0.6),
                        inverted=inverted,
                    )
                )
                max_y = max(max_y, cur_y + font_h)

        elif command == "^FS":
            pending = None
            inverted = False

        elif command == "~DG":
            name, bitmap = _parse_download_graphic(params)
            if bitmap is not None:
                stored[name] = bitmap

        elif command == "^XG":
            name = _normalize_graphic_name(parts[0] if parts else "")
            bitmap = stored.get(name) or (next(iter(stored.values())) if stored else None)
            if bitmap is not None:
                placed.append((cur_x, cur_y, bitmap))
                max_x = max(max_x, cur_x + bitmap.width)
                max_y = max(max_y, cur_y + bitmap.height)

        elif command == "^GF":
            bitmap = _parse_graphic_field(params)
            if bitmap is not None:
                placed.append((cur_x, cur_y, bitmap))
                max_x = max(max_x, cur_x + bitmap.width)
                max_y = max(max_y, cur_y + bitmap.height)

    # Uma etiqueta que só baixou o gráfico (~DG) sem dar ^XG ainda deve
    # aparecer no preview — é o formato que a Shopee costuma usar.
    if not placed and stored:
        bitmap = next(iter(stored.values()))
        placed.append((0, 0, bitmap))
        max_x = max(max_x, bitmap.width)
        max_y = max(max_y, bitmap.height)

    # ^PW/^LL, quando presentes, mandam: um bitmap de 812 pontos ocupa 102
    # bytes por linha (816 bits) e os 4 bits de sobra são só preenchimento —
    # respeitar o ^PW evita mostrar essa margem fantasma no preview.
    if not explicit_width:
        width = max(width, max_x)
    if not explicit_height:
        height = max(height, max_y)

    if width <= 0 or height <= 0:
        raise RenderError("não foi possível determinar o tamanho da etiqueta")

    render = LabelRender(
        width=width,
        height=height,
        dpi=dpi,
        pixels=bytearray(width * height),
        overlays=overlays,
        has_bitmap=bool(placed),
    )

    for origin_x, origin_y, bitmap in placed:
        _blit(render, bitmap, origin_x, origin_y)

    return render


def _normalize_graphic_name(raw: str) -> str:
    """'R:LOGO.GRF' -> 'LOGO'."""
    name = raw.strip().upper()
    if ":" in name:
        name = name.split(":", 1)[1]
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return name


def _parse_download_graphic(params: str) -> Tuple[str, Optional[Bitmap]]:
    """~DGd:o.x,t,w,data"""
    parts = params.split(",", 3)
    if len(parts) < 4:
        return "", None

    name = _normalize_graphic_name(parts[0])
    try:
        total = int(re.sub(r"\D", "", parts[1]) or 0)
        per_row = int(re.sub(r"\D", "", parts[2]) or 0)
        raw = decode_graphic_data(parts[3], per_row, total)
        return name, unpack_bitmap(raw, per_row)
    except (RenderError, ValueError) as exc:
        logger.warning("Campo ~DG ignorado no preview: %s", exc)
        return name, None


def _parse_graphic_field(params: str) -> Optional[Bitmap]:
    """^GFa,b,c,d,data — 'a' é o formato (A = ASCII hex)."""
    parts = params.split(",", 4)
    if len(parts) < 5:
        return None

    try:
        total = int(re.sub(r"\D", "", parts[2]) or 0)
        per_row = int(re.sub(r"\D", "", parts[3]) or 0)
        raw = decode_graphic_data(parts[4], per_row, total)
        return unpack_bitmap(raw, per_row)
    except (RenderError, ValueError) as exc:
        logger.warning("Campo ^GF ignorado no preview: %s", exc)
        return None


def _blit(render: LabelRender, bitmap: Bitmap, origin_x: int, origin_y: int) -> None:
    """
    Compõe um bitmap sobre a etiqueta (OR — ponto preto nunca some).

    Trabalha por fatias de linha inteira: a etiqueta da Shopee é um único
    bitmap do tamanho da etiqueta, e copiar linha a linha em vez de pixel a
    pixel deixa o preview instantâneo.
    """
    src_x0 = max(0, -origin_x)
    src_x1 = min(bitmap.width, render.width - origin_x)
    if src_x1 <= src_x0:
        return

    span = src_x1 - src_x0

    for y in range(bitmap.height):
        target_y = origin_y + y
        if not (0 <= target_y < render.height):
            continue

        src = y * bitmap.width + src_x0
        dst = target_y * render.width + origin_x + src_x0

        chunk = bitmap.pixels[src:src + span]
        target = render.pixels[dst:dst + span]

        if any(target):
            render.pixels[dst:dst + span] = bytes(a | b for a, b in zip(target, chunk))
        else:
            render.pixels[dst:dst + span] = chunk


# ---------------------------------------------------------------------------
# Code 128 (^BC) — usado quando a etiqueta traz o código como comando ZPL
# ---------------------------------------------------------------------------

_CODE128_PATTERNS = [
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312",
    "132212", "221213", "221312", "231212", "112232", "122132", "122231", "113222",
    "123122", "123221", "223211", "221132", "221231", "213212", "223112", "312131",
    "311222", "321122", "321221", "312212", "322112", "322211", "212123", "212321",
    "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121",
    "313121", "211331", "231131", "213113", "213311", "213131", "311123", "311321",
    "331121", "312113", "312311", "332111", "314111", "221411", "431111", "111224",
    "111422", "121124", "121421", "141122", "141221", "112214", "112412", "122114",
    "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112",
    "421211", "212141", "214121", "412121", "111143", "111341", "131141", "114113",
    "114311", "411113", "411311", "113141", "114131", "311141", "411131", "211412",
    "211214", "211232", "2331112",
]

_CODE128_STOP = 106


def encode_code128(value: str) -> List[int]:
    """
    Converte um texto em larguras de barras/espaços do Code 128.

    Retorna larguras alternadas começando por barra: [barra, espaço, barra, ...].
    Usa o subconjunto C quando o dado é totalmente numérico e par (mais denso,
    é o que impressoras térmicas escolhem nesse caso) e B no restante.
    """
    text = value.strip()
    if not text:
        return []

    use_c = text.isdigit() and len(text) % 2 == 0

    if use_c:
        start = 105
        codes = [int(text[i:i + 2]) for i in range(0, len(text), 2)]
    else:
        start = 104
        codes = [ord(c) - 32 for c in text if 32 <= ord(c) <= 126]

    checksum = start
    for position, code in enumerate(codes, start=1):
        checksum += position * code
    checksum %= 103

    sequence = [start] + codes + [checksum, _CODE128_STOP]

    widths: List[int] = []
    for code in sequence:
        if 0 <= code < len(_CODE128_PATTERNS):
            widths.extend(int(c) for c in _CODE128_PATTERNS[code])

    return widths


# ---------------------------------------------------------------------------
# Saída para a tela
# ---------------------------------------------------------------------------

def downsample(render: LabelRender, factor: int) -> Tuple[int, int, bytearray]:
    """
    Reduz o bitmap por média de área, devolvendo tons de cinza (0-255).

    Média de área (e não vizinho mais próximo) preserva traços finos de 1
    ponto — em código de barras isso é a diferença entre um preview legível
    e um borrão.
    """
    if factor <= 1:
        gray = bytearray(255 - 255 * p for p in render.pixels)
        return render.width, render.height, gray

    out_w = max(1, render.width // factor)
    out_h = max(1, render.height // factor)
    out = bytearray(out_w * out_h)
    src = render.pixels
    width = render.width
    area = factor * factor

    for oy in range(out_h):
        row_base = oy * out_w
        y0 = oy * factor
        y1 = min(y0 + factor, render.height)
        for ox in range(out_w):
            x0 = ox * factor
            x1 = min(x0 + factor, width)
            total = 0
            for y in range(y0, y1):
                total += sum(src[y * width + x0:y * width + x1])
            out[row_base + ox] = 255 - (total * 255 // area)

    return out_w, out_h, out


def to_ppm(width: int, height: int, gray: bytearray) -> bytes:
    """Empacota tons de cinza como PPM binário (P6), que o Tk lê nativamente."""
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    body = bytearray(width * height * 3)
    for i, value in enumerate(gray):
        body[i * 3] = body[i * 3 + 1] = body[i * 3 + 2] = value
    return header + bytes(body)


def render_to_ppm(render: LabelRender, factor: int = 3) -> bytes:
    """Atalho: render -> PPM pronto para tk.PhotoImage."""
    width, height, gray = downsample(render, factor)
    return to_ppm(width, height, gray)
