/*
 * Leitor de ZIP e separador de etiquetas — versão web.
 *
 * Porta de src/shopee_label_printer/parser.py. Usa DecompressionStream, que
 * é nativo do navegador: nenhuma biblioteca externa, nenhum upload. O arquivo
 * é lido na memória da própria aba e não sai do computador.
 */
(function (global) {
  "use strict";

  const LABEL_EXTENSIONS = [".txt", ".zpl", ".prn", ".tspl"];

  const SIG_EOCD = 0x06054b50;
  const SIG_CENTRAL = 0x02014b50;

  class ParserError extends Error {}

  async function inflateRaw(bytes) {
    if (typeof DecompressionStream === "undefined") {
      throw new ParserError(
        "Seu navegador não suporta leitura de ZIP. Use Chrome 80+, Firefox 113+ ou Safari 16.4+."
      );
    }
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }

  /** Lê um ZIP e devolve [{name, data}] com o conteúdo de cada arquivo. */
  async function readZip(arrayBuffer) {
    const view = new DataView(arrayBuffer);
    const bytes = new Uint8Array(arrayBuffer);

    // O EOCD fica no fim do arquivo, depois de um comentário de até 64 KB.
    let eocd = -1;
    const lowest = Math.max(0, bytes.length - 65557);
    for (let i = bytes.length - 22; i >= lowest; i--) {
      if (view.getUint32(i, true) === SIG_EOCD) {
        eocd = i;
        break;
      }
    }
    if (eocd < 0) throw new ParserError("Arquivo ZIP inválido ou corrompido.");

    const count = view.getUint16(eocd + 10, true);
    let offset = view.getUint32(eocd + 16, true);
    const entries = [];

    for (let i = 0; i < count; i++) {
      if (offset + 46 > bytes.length || view.getUint32(offset, true) !== SIG_CENTRAL) break;

      const method = view.getUint16(offset + 10, true);
      const compressedSize = view.getUint32(offset + 20, true);
      const nameLength = view.getUint16(offset + 28, true);
      const extraLength = view.getUint16(offset + 30, true);
      const commentLength = view.getUint16(offset + 32, true);
      const localOffset = view.getUint32(offset + 42, true);
      const name = new TextDecoder("utf-8").decode(
        bytes.subarray(offset + 46, offset + 46 + nameLength)
      );

      entries.push({ name, method, compressedSize, localOffset });
      offset += 46 + nameLength + extraLength + commentLength;
    }

    const files = [];
    for (const entry of entries) {
      if (entry.name.endsWith("/")) continue; // diretório

      const local = entry.localOffset;
      const localNameLength = view.getUint16(local + 26, true);
      const localExtraLength = view.getUint16(local + 28, true);
      const start = local + 30 + localNameLength + localExtraLength;
      const raw = bytes.subarray(start, start + entry.compressedSize);

      let data;
      if (entry.method === 0) {
        data = raw;
      } else if (entry.method === 8) {
        data = await inflateRaw(raw);
      } else {
        continue; // método de compressão que o navegador não abre
      }
      files.push({ name: entry.name, data });
    }
    return files;
  }

  function hasLabelExtension(name) {
    const lower = name.toLowerCase();
    return LABEL_EXTENSIONS.some((ext) => lower.endsWith(ext));
  }

  /** latin-1: 1 byte = 1 caractere, nenhum byte se perde no caminho. */
  function decodeLatin1(bytes) {
    let out = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      out += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return out;
  }

  function encodeLatin1(text) {
    const out = new Uint8Array(text.length);
    for (let i = 0; i < text.length; i++) out[i] = text.charCodeAt(i) & 0xff;
    return out;
  }

  // Blocos ^XA...^XZ completos ([\s\S] porque JS não tem flag DOTALL).
  const ZPL_BLOCK_RE = /\^XA[\s\S]*?\^XZ/g;

  // Comandos que realmente colocam algo no papel. Um bloco sem nenhum deles é
  // manutenção (^ID apaga gráfico da memória, ^DF salva formato).
  const PRINTABLE_RE = /\^(?:XG|GF|FD|FV|B[0-9A-Za-z])/i;

  /**
   * Alguns arquivos trazem várias etiquetas concatenadas no mesmo TXT.
   *
   * Uma etiqueta da Shopee não é um bloco só — são três, nesta ordem:
   *
   *   ~DGR:DEMO.GRF,124236,102,:Z64:...   baixa a imagem para a impressora
   *   ^XA ... ^XGR:DEMO.GRF,1,1 ... ^XZ   manda imprimir a imagem baixada
   *   ^XA ^IDR:DEMO.GRF ^FS ^XZ           apaga a imagem da memória
   *
   * Os três formam UMA etiqueta. Cortar em todo ^XA devolvia três, sendo que
   * duas apareciam em branco (o ^XG chama um gráfico que ficou no pedaço
   * anterior, e o ^ID não desenha nada).
   *
   * Regra: cada bloco ^XA...^XZ que imprime algo começa uma etiqueta nova e
   * leva junto o que veio antes dele (o ~DG) e os blocos de manutenção
   * que vierem depois.
   */
  function splitLabels(content) {
    const blocks = [...content.matchAll(ZPL_BLOCK_RE)];

    if (blocks.length === 0) {
      // Sem nenhum ^XA...^XZ fechado: arquivo só de downloads, ou truncado.
      let parts;
      if (content.includes("~DG")) parts = content.split(/(?=~DG)/);
      else if (content.includes("^XA")) parts = content.split(/(?=\^XA)/);
      else parts = [content];
      return parts.filter((part) => part.trim().length > 0);
    }

    const labels = [];
    let current = null;
    let pending = "";
    let lastEnd = 0;

    for (const match of blocks) {
      pending += content.slice(lastEnd, match.index);
      const block = match[0];
      lastEnd = match.index + block.length;

      if (PRINTABLE_RE.test(block)) {
        if (current !== null) labels.push(current);
        current = pending + block;
        pending = "";
      } else if (current !== null) {
        current += pending + block;
        pending = "";
      } else {
        pending += block;
      }
    }

    const tail = content.slice(lastEnd);
    if (current !== null) {
      if (tail.trim()) current += tail;
      labels.push(current);
    } else if ((pending + tail).trim()) {
      labels.push(pending + tail);
    }

    return labels.filter((label) => label.trim().length > 0);
  }

  /**
   * Recebe uma lista de File do navegador e devolve [{name, data}] por etiqueta.
   * Aceita .zip e arquivos de etiqueta soltos, igual ao aplicativo desktop.
   */
  async function loadLabelsFromFiles(fileList) {
    const labels = [];
    const sources = [];

    for (const file of fileList) {
      const buffer = await file.arrayBuffer();

      if (file.name.toLowerCase().endsWith(".zip")) {
        const inner = await readZip(buffer);
        const found = inner.filter((entry) => hasLabelExtension(entry.name));
        if (found.length === 0) {
          throw new ParserError(
            `Nenhuma etiqueta encontrada em ${file.name}.\n` +
              "Procurando por: .txt, .zpl, .prn, .tspl"
          );
        }
        found.sort((a, b) => a.name.localeCompare(b.name));
        sources.push(...found);
      } else {
        sources.push({ name: file.name, data: new Uint8Array(buffer) });
      }
    }

    if (sources.length === 0) throw new ParserError("Nenhum arquivo de etiqueta selecionado.");

    for (const source of sources) {
      if (source.data.length === 0) continue;

      const blocks = splitLabels(decodeLatin1(source.data));
      const baseName = source.name.split("/").pop();

      blocks.forEach((block, index) => {
        const name =
          blocks.length > 1
            ? `${baseName} (etiqueta ${index + 1}/${blocks.length})`
            : baseName;
        labels.push({ name, data: encodeLatin1(block) });
      });
    }

    if (labels.length === 0) throw new ParserError("Nenhuma etiqueta válida foi carregada.");
    return labels;
  }

  global.LabelZip = {
    ParserError,
    readZip,
    splitLabels,
    decodeLatin1,
    encodeLatin1,
    hasLabelExtension,
    loadLabelsFromFiles,
  };
})(window);
