/*
 * Renderizador ZPL/TSPL — versão web.
 *
 * Porta fiel de src/shopee_label_printer/renderer.py: as duas versões
 * decodificam a etiqueta exatamente do mesmo jeito, então o preview do
 * navegador e o do aplicativo desktop mostram a mesma imagem.
 *
 * Os bytes originais nunca são alterados: este módulo só lê.
 */
(function (global) {
  "use strict";

  const DEFAULT_DPI = 203;          // FY-1075
  const DEFAULT_WIDTH_DOTS = 812;   // 4" a 203 DPI
  const DEFAULT_HEIGHT_DOTS = 1218; // 6" a 203 DPI

  class RenderError extends Error {}

  // -- decodificação do campo gráfico (~DG / ^GFA) --------------------------

  function isHexDigit(ch) {
    return (ch >= "0" && ch <= "9") || (ch >= "A" && ch <= "F") || (ch >= "a" && ch <= "f");
  }

  function decodeBase64Variant(data) {
    const parts = data.split(":");
    if (parts.length < 3) throw new RenderError("campo gráfico B64/Z64 malformado");

    const scheme = parts[1].toUpperCase();
    let raw;
    try {
      const binary = atob(parts[2]);
      raw = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) raw[i] = binary.charCodeAt(i);
    } catch (err) {
      throw new RenderError("base64 inválido no campo gráfico");
    }

    if (scheme === "Z64") {
      // O inflate do Z64 é assíncrono no navegador; quem chama resolve antes.
      throw new RenderError("Z64_ASYNC");
    }
    if (scheme !== "B64") {
      throw new RenderError("esquema de codificação gráfica não suportado: " + scheme);
    }
    return raw;
  }

  /**
   * Hexadecimal com o esquema de compressão ASCII da ZPL.
   *   G..Y -> 1..19    g..z -> 20,40,...,400   (somam: 'hG' = 41)
   *   ','  -> completa a linha com branco
   *   '!'  -> completa a linha com preto
   *   ':'  -> repete a linha anterior
   */
  function decodeCompressedHex(data, bytesPerRow, totalBytes) {
    const nibblesPerRow = bytesPerRow * 2;
    const out = [];
    let row = "";
    let prevRow = null;
    let repeat = 0;

    const flushRows = () => {
      while (row.length >= nibblesPerRow) {
        const full = row.slice(0, nibblesPerRow);
        for (let i = 0; i < full.length; i += 2) {
          out.push(parseInt(full.substr(i, 2), 16));
        }
        prevRow = full;
        row = row.slice(nibblesPerRow);
      }
    };

    for (const char of data) {
      if (char === " " || char === "\t" || char === "\r" || char === "\n") continue;

      if (char >= "G" && char <= "Y") {
        repeat += char.charCodeAt(0) - 71 + 1; // 'G' = 71
        continue;
      }
      if (char >= "g" && char <= "z") {
        repeat += (char.charCodeAt(0) - 103 + 1) * 20; // 'g' = 103
        continue;
      }

      if (char === ",") {
        row += "0".repeat(nibblesPerRow - row.length);
      } else if (char === "!") {
        row += "F".repeat(nibblesPerRow - row.length);
      } else if (char === ":") {
        row = prevRow !== null ? prevRow : "0".repeat(nibblesPerRow);
      } else if (isHexDigit(char)) {
        row += char.toUpperCase().repeat(repeat || 1);
      } else {
        repeat = 0;
        continue;
      }

      repeat = 0;
      flushRows();
    }

    if (row.length > 0) {
      row += "0".repeat(nibblesPerRow - row.length);
      flushRows();
    }

    let bytes = Uint8Array.from(out);
    if (totalBytes > 0 && bytes.length !== totalBytes) {
      const fixed = new Uint8Array(totalBytes);
      fixed.set(bytes.subarray(0, Math.min(bytes.length, totalBytes)));
      bytes = fixed;
    }
    return bytes;
  }

  async function inflateZlib(bytes) {
    if (typeof DecompressionStream === "undefined") {
      throw new RenderError("navegador sem suporte a DecompressionStream");
    }
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }

  /** Pré-descomprime todos os blocos :Z64: para o render poder ser síncrono. */
  async function expandZ64Blocks(text) {
    const pattern = /:Z64:([A-Za-z0-9+/=]+):(-?\d+)/g;
    const matches = [...text.matchAll(pattern)];
    if (matches.length === 0) return text;

    let result = "";
    let last = 0;
    for (const match of matches) {
      result += text.slice(last, match.index);
      try {
        const binary = atob(match[1]);
        const compressed = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) compressed[i] = binary.charCodeAt(i);
        const raw = await inflateZlib(compressed);
        let hex = "";
        for (const byte of raw) hex += byte.toString(16).padStart(2, "0").toUpperCase();
        result += hex;
      } catch (err) {
        result += match[0]; // deixa como está; o campo será ignorado no render
      }
      last = match.index + match[0].length;
    }
    return result + text.slice(last);
  }

  function decodeGraphicData(data, bytesPerRow, totalBytes) {
    if (bytesPerRow <= 0) throw new RenderError("bytes por linha inválido no campo gráfico");
    const stripped = data.trim();
    if (stripped.startsWith(":")) return decodeBase64Variant(stripped);
    return decodeCompressedHex(stripped, bytesPerRow, totalBytes);
  }

  /** Bits empacotados -> 1 byte por pixel (1 = preto). */
  function unpackBitmap(raw, bytesPerRow) {
    if (bytesPerRow <= 0) throw new RenderError("bytes por linha inválido");
    const height = Math.floor(raw.length / bytesPerRow);
    const width = bytesPerRow * 8;
    const pixels = new Uint8Array(width * height);

    for (let y = 0; y < height; y++) {
      const base = y * bytesPerRow;
      const outBase = y * width;
      for (let bx = 0; bx < bytesPerRow; bx++) {
        const byte = raw[base + bx];
        if (!byte) continue;
        const px = outBase + bx * 8;
        for (let bit = 0; bit < 8; bit++) {
          if (byte & (0x80 >> bit)) pixels[px + bit] = 1;
        }
      }
    }
    return { width, height, pixels };
  }

  // -- tokenização ----------------------------------------------------------

  function tokenizeZpl(text) {
    const tokens = [];
    let i = 0;
    const n = text.length;

    while (i < n) {
      const char = text[i];
      if (char !== "^" && char !== "~") {
        i++;
        continue;
      }

      let j = i + 1;
      let name = "";
      while (j < n && name.length < 2 && /[a-zA-Z]/.test(text[j])) {
        name += text[j].toUpperCase();
        j++;
      }
      if (!name) {
        i++;
        continue;
      }

      const command = char + name;
      if (command === "^FD" || command === "^FV") {
        let end = text.indexOf("^FS", j);
        if (end === -1) end = n;
        tokens.push([command, text.slice(j, end)]);
        i = end;
      } else {
        let k = j;
        while (k < n && text[k] !== "^" && text[k] !== "~") k++;
        tokens.push([command, text.slice(j, k)]);
        i = k;
      }
    }
    return tokens;
  }

  function intArg(parts, index, fallback = 0) {
    if (index >= parts.length) return fallback;
    const match = /^\s*(-?\d+)/.exec(parts[index]);
    return match ? parseInt(match[1], 10) : fallback;
  }

  function digitsOnly(value) {
    const cleaned = (value || "").replace(/\D/g, "");
    return cleaned ? parseInt(cleaned, 10) : 0;
  }

  function normalizeGraphicName(raw) {
    let name = (raw || "").trim().toUpperCase();
    if (name.includes(":")) name = name.split(":").slice(1).join(":");
    if (name.includes(".")) name = name.slice(0, name.lastIndexOf("."));
    return name;
  }

  // -- Code 128 -------------------------------------------------------------

  const CODE128_PATTERNS = [
    "212222","222122","222221","121223","121322","131222","122213","122312","132212","221213",
    "221312","231212","112232","122132","122231","113222","123122","123221","223211","221132",
    "221231","213212","223112","312131","311222","321122","321221","312212","322112","322211",
    "212123","212321","232121","111323","131123","131321","112313","132113","132311","211313",
    "231113","231311","112133","112331","132131","113123","113321","133121","313121","211331",
    "231131","213113","213311","213131","311123","311321","331121","312113","312311","332111",
    "314111","221411","431111","111224","111422","121124","121421","141122","141221","112214",
    "112412","122114","122411","142112","142211","241211","221114","413111","241112","134111",
    "111242","121142","121241","114212","124112","124211","411212","421112","421211","212141",
    "214121","412121","111143","111341","131141","114113","114311","411113","411311","113141",
    "114131","311141","411131","211412","211214","211232","2331112",
  ];

  function encodeCode128(value) {
    const text = (value || "").trim();
    if (!text) return [];

    const useC = /^\d+$/.test(text) && text.length % 2 === 0;
    let start;
    let codes;

    if (useC) {
      start = 105;
      codes = [];
      for (let i = 0; i < text.length; i += 2) codes.push(parseInt(text.substr(i, 2), 10));
    } else {
      start = 104;
      codes = [];
      for (const ch of text) {
        const code = ch.charCodeAt(0);
        if (code >= 32 && code <= 126) codes.push(code - 32);
      }
    }

    let checksum = start;
    codes.forEach((code, index) => {
      checksum += (index + 1) * code;
    });
    checksum %= 103;

    const sequence = [start, ...codes, checksum, 106];
    const widths = [];
    for (const code of sequence) {
      const pattern = CODE128_PATTERNS[code];
      if (pattern) for (const digit of pattern) widths.push(parseInt(digit, 10));
    }
    return widths;
  }

  // -- render ---------------------------------------------------------------

  function blit(render, bitmap, originX, originY) {
    const srcX0 = Math.max(0, -originX);
    const srcX1 = Math.min(bitmap.width, render.width - originX);
    if (srcX1 <= srcX0) return;

    for (let y = 0; y < bitmap.height; y++) {
      const targetY = originY + y;
      if (targetY < 0 || targetY >= render.height) continue;
      const src = y * bitmap.width;
      const dst = targetY * render.width + originX;
      for (let x = srcX0; x < srcX1; x++) {
        if (bitmap.pixels[src + x]) render.pixels[dst + x] = 1;
      }
    }
  }

  function parseDownloadGraphic(params) {
    const parts = splitLimit(params, ",", 4);
    if (parts.length < 4) return [null, null];
    const name = normalizeGraphicName(parts[0]);
    try {
      const total = digitsOnly(parts[1]);
      const perRow = digitsOnly(parts[2]);
      return [name, unpackBitmap(decodeGraphicData(parts[3], perRow, total), perRow)];
    } catch (err) {
      return [name, null];
    }
  }

  function parseGraphicField(params) {
    const parts = splitLimit(params, ",", 5);
    if (parts.length < 5) return null;
    try {
      const total = digitsOnly(parts[2]);
      const perRow = digitsOnly(parts[3]);
      return unpackBitmap(decodeGraphicData(parts[4], perRow, total), perRow);
    } catch (err) {
      return null;
    }
  }

  /** split preservando o resto no último elemento (equivalente ao maxsplit do Python). */
  function splitLimit(text, sep, limit) {
    const parts = text.split(sep);
    if (parts.length <= limit) return parts;
    return parts.slice(0, limit - 1).concat(parts.slice(limit - 1).join(sep));
  }

  function renderZplSync(text, options = {}) {
    const dpi = options.dpi || DEFAULT_DPI;
    const tokens = tokenizeZpl(text);

    const stored = new Map();
    const placed = [];
    const overlays = [];

    let width = options.defaultWidth || DEFAULT_WIDTH_DOTS;
    let height = options.defaultHeight || DEFAULT_HEIGHT_DOTS;
    let explicitWidth = false;
    let explicitHeight = false;
    let maxX = 0;
    let maxY = 0;

    let homeX = 0, homeY = 0;
    let curX = 0, curY = 0;
    let fontH = 20, fontW = 0;
    let barcodeH = 50, barcodeW = 2;
    let inverted = false;
    let pending = null;

    for (const [command, params] of tokens) {
      const parts = params.split(",");

      switch (command) {
        case "^PW": {
          const value = intArg(parts, 0);
          if (value > 0) { width = value; explicitWidth = true; }
          break;
        }
        case "^LL": {
          const value = intArg(parts, 0);
          if (value > 0) { height = value; explicitHeight = true; }
          break;
        }
        case "^LH":
          homeX = intArg(parts, 0);
          homeY = intArg(parts, 1);
          break;
        case "^FO":
        case "^FT":
          curX = homeX + intArg(parts, 0);
          curY = homeY + intArg(parts, 1);
          inverted = false;
          break;
        case "^FR":
          inverted = true;
          break;
        case "^A":
          fontH = intArg(parts, 1, 20) || 20;
          fontW = intArg(parts, 2, 0);
          break;
        case "^BY":
          barcodeW = intArg(parts, 0, 2) || 2;
          barcodeH = intArg(parts, 2, barcodeH) || barcodeH;
          break;
        case "^BC":
          pending = {
            kind: "barcode", x: curX, y: curY,
            height: intArg(parts, 1, 0) || barcodeH,
            thickness: barcodeW, data: "", modules: [],
          };
          break;
        case "^BQ":
          pending = {
            kind: "qr", x: curX, y: curY,
            thickness: intArg(parts, 2, 3) || 3, data: "", modules: [],
          };
          break;
        case "^GB": {
          const boxW = intArg(parts, 0);
          const boxH = intArg(parts, 1);
          overlays.push({
            kind: "box", x: curX, y: curY,
            width: boxW, height: boxH, thickness: intArg(parts, 2, 1) || 1,
          });
          maxX = Math.max(maxX, curX + boxW);
          maxY = Math.max(maxY, curY + boxH);
          break;
        }
        case "^FD":
        case "^FV":
          if (pending) {
            pending.data = params;
            if (pending.kind === "barcode") pending.modules = encodeCode128(params);
            overlays.push(pending);
            maxX = Math.max(maxX, pending.x + pending.modules.length * pending.thickness);
            maxY = Math.max(maxY, pending.y + (pending.height || 0));
            pending = null;
          } else if (params.trim()) {
            overlays.push({
              kind: "text", x: curX, y: curY, data: params,
              fontHeight: fontH, fontWidth: fontW || Math.round(fontH * 0.6), inverted,
            });
            maxY = Math.max(maxY, curY + fontH);
          }
          break;
        case "^FS":
          pending = null;
          inverted = false;
          break;
        case "~DG": {
          const [name, bitmap] = parseDownloadGraphic(params);
          if (bitmap) stored.set(name, bitmap);
          break;
        }
        case "^XG": {
          const name = normalizeGraphicName(parts[0] || "");
          const bitmap = stored.get(name) || (stored.size ? stored.values().next().value : null);
          if (bitmap) {
            placed.push([curX, curY, bitmap]);
            maxX = Math.max(maxX, curX + bitmap.width);
            maxY = Math.max(maxY, curY + bitmap.height);
          }
          break;
        }
        case "^GF": {
          const bitmap = parseGraphicField(params);
          if (bitmap) {
            placed.push([curX, curY, bitmap]);
            maxX = Math.max(maxX, curX + bitmap.width);
            maxY = Math.max(maxY, curY + bitmap.height);
          }
          break;
        }
        default:
          break;
      }
    }

    // A Shopee costuma mandar ~DG sem o ^XG correspondente.
    if (placed.length === 0 && stored.size > 0) {
      const bitmap = stored.values().next().value;
      placed.push([0, 0, bitmap]);
      maxX = Math.max(maxX, bitmap.width);
      maxY = Math.max(maxY, bitmap.height);
    }

    // ^PW/^LL mandam quando presentes: 812 pontos ocupam 102 bytes por linha
    // (816 bits) e os 4 bits de sobra são só preenchimento.
    if (!explicitWidth) width = Math.max(width, maxX);
    if (!explicitHeight) height = Math.max(height, maxY);

    if (width <= 0 || height <= 0) {
      throw new RenderError("não foi possível determinar o tamanho da etiqueta");
    }

    const render = {
      width, height, dpi, overlays,
      pixels: new Uint8Array(width * height),
      hasBitmap: placed.length > 0,
      widthMm: (width / dpi) * 25.4,
      heightMm: (height / dpi) * 25.4,
    };

    for (const [originX, originY, bitmap] of placed) blit(render, bitmap, originX, originY);
    return render;
  }

  /** Render assíncrono: expande blocos Z64 antes de rasterizar. */
  async function renderZpl(data, options = {}) {
    let text;
    if (typeof data === "string") {
      text = data;
    } else {
      // latin-1: 1 byte = 1 caractere, nenhum byte se perde
      let out = "";
      const chunk = 0x8000;
      for (let i = 0; i < data.length; i += chunk) {
        out += String.fromCharCode.apply(null, data.subarray(i, i + chunk));
      }
      text = out;
    }
    if (text.includes(":Z64:")) text = await expandZ64Blocks(text);
    return renderZplSync(text, options);
  }

  /** Pinta o render num canvas na resolução nativa (1 pixel = 1 ponto). */
  function drawToCanvas(render, canvas) {
    canvas.width = render.width;
    canvas.height = render.height;

    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, render.width, render.height);

    const image = ctx.createImageData(render.width, render.height);
    const buffer = new Uint32Array(image.data.buffer);
    const black = 0xff000000; // ABGR little-endian
    const white = 0xffffffff;
    for (let i = 0; i < render.pixels.length; i++) {
      buffer[i] = render.pixels[i] ? black : white;
    }
    ctx.putImageData(image, 0, 0);

    drawOverlays(ctx, render.overlays);
    return canvas;
  }

  function drawOverlays(ctx, overlays) {
    ctx.fillStyle = "#000000";
    ctx.strokeStyle = "#000000";

    for (const overlay of overlays) {
      if (overlay.kind === "text") {
        ctx.font = `${Math.max(6, overlay.fontHeight)}px "Helvetica Neue", Arial, sans-serif`;
        ctx.textBaseline = "top";
        ctx.fillStyle = "#000000";
        ctx.fillText(overlay.data, overlay.x, overlay.y);
      } else if (overlay.kind === "box") {
        ctx.lineWidth = Math.max(1, overlay.thickness);
        ctx.strokeRect(overlay.x, overlay.y, overlay.width, overlay.height);
      } else if (overlay.kind === "barcode") {
        ctx.fillStyle = "#000000";
        let cursor = overlay.x;
        overlay.modules.forEach((module, index) => {
          const span = module * overlay.thickness;
          if (index % 2 === 0 && span > 0) ctx.fillRect(cursor, overlay.y, span, overlay.height);
          cursor += span;
        });
      } else if (overlay.kind === "qr") {
        const side = Math.max(20, 25 * overlay.thickness);
        ctx.save();
        ctx.setLineDash([6, 6]);
        ctx.lineWidth = 2;
        ctx.strokeRect(overlay.x, overlay.y, side, side);
        ctx.restore();
        ctx.font = "16px Arial, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("QR", overlay.x + side / 2, overlay.y + side / 2);
        ctx.textAlign = "start";
      }
    }
  }

  // -- reforço de impressão -------------------------------------------------
  //
  // Mesmos valores de PRINT_BOOST_LEVELS em printer.py: o ZPL baixado aqui tem
  // que sair igual ao que a versão desktop enviaria com o mesmo nível.
  //
  // Só serve para o arquivo baixado. A impressão pelo navegador manda uma
  // imagem pelo driver do sistema, e nesse caminho a impressora nunca vê
  // comando ZPL nenhum — ^MD e ^PR seriam descartados. Quem controla o
  // escurecimento ali é a configuração do driver.
  const PRINT_BOOST_LEVELS = {
    desligado: [null, null],
    leve: [6, 3],
    medio: [12, 2],
    forte: [18, 2],
  };

  /**
   * Insere ^MD (escurecimento) e ^PR (velocidade) logo após o primeiro ^XA.
   *
   * Não mexe no desenho: os dois comandos controlam o calor da cabeça térmica
   * e a velocidade do papel, não o conteúdo. Nenhum ponto é movido — engrossar
   * o bitmap alargaria também as barras do código de barras e estragaria a
   * proporção barra/espaço que o leitor mede.
   */
  function applyPrintBoost(data, level) {
    const [darkness, speed] = PRINT_BOOST_LEVELS[level] || [null, null];
    if (darkness === null && speed === null) return data;

    // procura os bytes de "^XA"
    let at = -1;
    for (let i = 0; i + 2 < data.length; i++) {
      if (data[i] === 0x5e && data[i + 1] === 0x58 && data[i + 2] === 0x41) {
        at = i + 3;
        break;
      }
    }
    if (at === -1) return data;

    let commands = "";
    if (darkness !== null) commands += `^MD${darkness}`;
    if (speed !== null) commands += `^PR${speed}`;

    const extra = new Uint8Array(commands.length);
    for (let i = 0; i < commands.length; i++) extra[i] = commands.charCodeAt(i);

    const out = new Uint8Array(data.length + extra.length);
    out.set(data.subarray(0, at), 0);
    out.set(extra, at);
    out.set(data.subarray(at), at + extra.length);
    return out;
  }

  global.ZPL = {
    PRINT_BOOST_LEVELS,
    applyPrintBoost,
    DEFAULT_DPI,
    DEFAULT_WIDTH_DOTS,
    DEFAULT_HEIGHT_DOTS,
    RenderError,
    decodeGraphicData,
    unpackBitmap,
    tokenizeZpl,
    encodeCode128,
    renderZpl,
    renderZplSync,
    drawToCanvas,
  };
})(window);
