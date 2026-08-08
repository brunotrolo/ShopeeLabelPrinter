/*
 * Conversores de formato: ZPL -> TSPL e ZPL -> PDF — versão web.
 *
 * Porta de src/shopee_label_printer/converters.py. Mesma regra: a etiqueta
 * real da Shopee traz o desenho inteiro embutido como imagem, então o
 * bitmap decodificado já é a etiqueta completa. Uma etiqueta com elementos
 * desenhados por fora do bitmap (texto/caixa/código como overlay) é
 * recusada, não aproximada — ver _render_or_raise no lado Python.
 *
 * O PDF é montado à mão (sem biblioteca) com CompressionStream("deflate"),
 * que no navegador produz um stream zlib — o mesmo formato que o
 * zlib.compress() do Python usa para /FlateDecode.
 */
(function (global) {
  "use strict";

  class ConversionError extends Error {}

  function rejectIfHasOverlays(render) {
    if (render.overlays && render.overlays.length > 0) {
      throw new ConversionError(
        "Esta etiqueta tem elementos desenhados por fora da imagem embutida " +
          "(texto, caixa ou código de barras) — a conversão só é confiável para " +
          "etiquetas onde tudo já vem como imagem, como as da Shopee. " +
          "Baixe em ZPL para não arriscar perder esses elementos."
      );
    }
  }

  /** Empacota render.pixels (1 byte por pixel, 1 = preto) em bits MSB-first. */
  function packBitmap(render) {
    const { width, height, pixels } = render;
    const bytesPerRow = (width + 7) >> 3;
    const packed = new Uint8Array(bytesPerRow * height);

    for (let y = 0; y < height; y++) {
      const rowPixelBase = y * width;
      const rowByteBase = y * bytesPerRow;
      for (let x = 0; x < width; x++) {
        if (pixels[rowPixelBase + x]) {
          packed[rowByteBase + (x >> 3)] |= 0x80 >> (x & 7);
        }
      }
    }
    return { packed, bytesPerRow, height };
  }

  // Mesmos níveis do lado Python (converters.py TSPL_BOOST_LEVELS).
  const TSPL_BOOST_LEVELS = {
    desligado: [null, null],
    leve: [10, 3],
    medio: [12, 2],
    forte: [15, 2],
  };

  /**
   * BITMAP x,y,largura_em_bytes,altura_em_pontos,modo,<dados binários>
   * (TSPL/TSPL2 Programming Manual, TSC) — dados crus, não hex/texto.
   */
  async function zplToTspl(render, boostLevel) {
    rejectIfHasOverlays(render);
    const { packed, bytesPerRow, height } = packBitmap(render);

    const [density, speed] = TSPL_BOOST_LEVELS[boostLevel] || [null, null];
    let boostCommands = "";
    if (speed !== null) boostCommands += `SPEED ${speed}\r\n`;
    if (density !== null) boostCommands += `DENSITY ${density}\r\n`;

    const header =
      `SIZE ${render.widthMm.toFixed(1)} mm,${render.heightMm.toFixed(1)} mm\r\n` +
      "GAP 3 mm,0 mm\r\n" +
      "DIRECTION 1\r\n" +
      boostCommands +
      "CLS\r\n" +
      `BITMAP 0,0,${bytesPerRow},${height},0,`;

    const headerBytes = new TextEncoder().encode(header);
    const footerBytes = new TextEncoder().encode("\r\nPRINT 1,1\r\n");

    const out = new Uint8Array(headerBytes.length + packed.length + footerBytes.length);
    out.set(headerBytes, 0);
    out.set(packed, headerBytes.length);
    out.set(footerBytes, headerBytes.length + packed.length);
    return out;
  }

  /** Comprime com zlib (RFC 1950) — o mesmo formato que /FlateDecode espera. */
  async function deflateZlib(bytes) {
    if (typeof CompressionStream === "undefined") {
      throw new ConversionError(
        "Seu navegador não suporta compressão nativa. Use Chrome 80+, Firefox 113+ ou Safari 16.4+."
      );
    }
    const stream = new Blob([bytes]).stream().pipeThrough(new CompressionStream("deflate"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }

  function concatBytes(parts) {
    const total = parts.reduce((sum, p) => sum + p.length, 0);
    const out = new Uint8Array(total);
    let offset = 0;
    for (const p of parts) {
      out.set(p, offset);
      offset += p.length;
    }
    return out;
  }

  /**
   * Monta um PDF de uma página só com uma imagem 1-bit (DeviceGray) ocupando
   * a página inteira. /Decode [1 0] inverte a tabela padrão do DeviceGray:
   * bit 1 (preto no nosso render) vira componente 0 (preto no PDF).
   */
  async function buildPdf(widthMm, heightMm, widthPx, heightPx, packedBits) {
    const compressed = await deflateZlib(packedBits);
    const enc = new TextEncoder();

    const widthPt = (widthMm * 72) / 25.4;
    const heightPt = (heightMm * 72) / 25.4;

    const contentStream = enc.encode(
      `q\n${widthPt.toFixed(2)} 0 0 ${heightPt.toFixed(2)} 0 0 cm\n/Im0 Do\nQ\n`
    );

    const obj1 = enc.encode("<< /Type /Catalog /Pages 2 0 R >>");
    const obj2 = enc.encode("<< /Type /Pages /Kids [3 0 R] /Count 1 >>");
    const obj3 = enc.encode(
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${widthPt.toFixed(2)} ${heightPt.toFixed(2)}] ` +
        "/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>"
    );
    const obj4 = concatBytes([
      enc.encode(`<< /Length ${contentStream.length} >>\nstream\n`),
      contentStream,
      enc.encode("\nendstream"),
    ]);
    const obj5 = concatBytes([
      enc.encode(
        `<< /Type /XObject /Subtype /Image /Width ${widthPx} /Height ${heightPx} ` +
          "/ColorSpace /DeviceGray /BitsPerComponent 1 /Decode [1 0] " +
          `/Filter /FlateDecode /Length ${compressed.length} >>\nstream\n`
      ),
      compressed,
      enc.encode("\nendstream"),
    ]);

    const objects = [obj1, obj2, obj3, obj4, obj5];

    // TextEncoder faz UTF-8: bytes >0x7F viram sequências multi-byte, então o
    // marcador binário (só um comentário para editores reconhecerem que o
    // arquivo não é texto puro) precisa ser montado como bytes crus, não
    // através de enc.encode numa string com esses code points.
    const binaryMarker = concatBytes([
      enc.encode("%PDF-1.4\n%"),
      new Uint8Array([0xe2, 0xe3, 0xcf, 0xd3]),
      enc.encode("\n"),
    ]);
    const chunks = [binaryMarker];
    let pos = chunks[0].length;
    const offsets = [0];

    for (let i = 0; i < objects.length; i++) {
      offsets.push(pos);
      const head = enc.encode(`${i + 1} 0 obj\n`);
      const tail = enc.encode("\nendobj\n");
      chunks.push(head, objects[i], tail);
      pos += head.length + objects[i].length + tail.length;
    }

    const xrefOffset = pos;
    let xrefText = `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
    for (let i = 1; i <= objects.length; i++) {
      xrefText += `${String(offsets[i]).padStart(10, "0")} 00000 n \n`;
    }
    xrefText += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;
    chunks.push(enc.encode(xrefText));

    return concatBytes(chunks);
  }

  async function zplToPdf(render) {
    rejectIfHasOverlays(render);
    const { packed } = packBitmap(render);
    return buildPdf(render.widthMm, render.heightMm, render.width, render.height, packed);
  }

  global.LabelConverters = {
    ConversionError,
    TSPL_BOOST_LEVELS,
    packBitmap,
    zplToTspl,
    zplToPdf,
    buildPdf,
  };
})(window);
