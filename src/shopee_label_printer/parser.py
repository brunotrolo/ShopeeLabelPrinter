"""
Módulo de parsing: extração e separação de etiquetas.
Com tratamento robusto de erros.
"""

import os
import re
import zipfile
import tempfile
from pathlib import Path
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

LABEL_EXTENSIONS = {".txt", ".zpl", ".prn", ".tspl"}


class ParserError(Exception):
    """Erro no parsing de arquivos."""
    pass


def extract_zip_to_temp(zip_path: str) -> str:
    """
    Extrai o ZIP para uma pasta temporária e retorna o caminho dela.

    Raises:
        ParserError: Se o ZIP não puder ser lido
    """
    try:
        if not os.path.exists(zip_path):
            raise ParserError(f"Arquivo não encontrado: {zip_path}")

        if not zipfile.is_zipfile(zip_path):
            raise ParserError(f"Arquivo não é um ZIP válido: {zip_path}")

        tmp_dir = tempfile.mkdtemp(prefix="shopee_labels_")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)

        logger.info(f"ZIP extraído para: {tmp_dir}")
        return tmp_dir

    except ParserError:
        raise
    except Exception as e:
        raise ParserError(f"Erro ao extrair ZIP: {str(e)}")


def find_label_files(folder: str) -> List[str]:
    """
    Varre a pasta (recursivo) procurando arquivos de etiqueta.

    Raises:
        ParserError: Se a pasta não existir
    """
    if not os.path.isdir(folder):
        raise ParserError(f"Pasta não encontrada: {folder}")

    files = []
    try:
        for root, _dirs, names in os.walk(folder):
            for name in names:
                if Path(name).suffix.lower() in LABEL_EXTENSIONS:
                    files.append(os.path.join(root, name))
    except Exception as e:
        raise ParserError(f"Erro ao buscar arquivos: {str(e)}")

    logger.debug(f"Encontrados {len(files)} arquivo(s) de etiqueta")
    return sorted(files)


# Blocos ^XA...^XZ completos. DOTALL porque o bloco pode ter quebras de linha.
_ZPL_BLOCK_RE = re.compile(r"\^XA.*?\^XZ", re.DOTALL)

# Comandos que realmente colocam algo no papel. Um bloco sem nenhum deles é
# manutenção (^ID apaga gráfico da memória, ^DF salva formato) e não é etiqueta.
_PRINTABLE_RE = re.compile(r"\^(?:XG|GF|FD|FV|B[0-9A-Za-z])", re.IGNORECASE)


def split_labels(content: str) -> List[str]:
    """
    Alguns arquivos trazem mais de uma etiqueta concatenada no mesmo TXT.
    Divide o conteúdo em blocos individuais, um por etiqueta.

    Uma etiqueta da Shopee não é um bloco só — são três, nesta ordem:

        ~DGR:DEMO.GRF,124236,102,:Z64:...   baixa a imagem para a impressora
        ^XA ... ^XGR:DEMO.GRF,1,1 ... ^XZ   manda imprimir a imagem baixada
        ^XA ^IDR:DEMO.GRF ^FS ^XZ           apaga a imagem da memória

    Os três formam UMA etiqueta. Cortar em todo ^XA devolvia três, sendo que
    duas apareciam em branco no preview (o ^XG chama um gráfico que ficou no
    pedaço anterior, e o ^ID não desenha nada) — e as duas eram enviadas à
    impressora como se fossem etiquetas de verdade.

    A regra usada aqui: cada bloco ^XA...^XZ que imprime alguma coisa começa
    uma etiqueta nova e leva junto o que veio antes dele (o ~DG) e os blocos
    de manutenção que vierem depois.
    """
    blocks = list(_ZPL_BLOCK_RE.finditer(content))

    if not blocks:
        # Sem nenhum ^XA...^XZ fechado: arquivo só de downloads, ou truncado.
        if "~DG" in content:
            parts = re.split(r"(?=~DG)", content)
        elif "^XA" in content:
            parts = re.split(r"(?=\^XA)", content)
        else:
            parts = [content]
        return [p for p in parts if p.strip()]

    labels: List[str] = []
    current: str | None = None
    pending = ""        # material fora de bloco (o ~DG mora aqui)
    last_end = 0

    for match in blocks:
        pending += content[last_end:match.start()]
        block = match.group(0)
        last_end = match.end()

        if _PRINTABLE_RE.search(block):
            if current is not None:
                labels.append(current)
            current = pending + block
            pending = ""
        elif current is not None:
            current += pending + block
            pending = ""
        else:
            pending += block

    # O que sobrar depois do último ^XZ vai junto, mesmo sendo só uma quebra de
    # linha: descartar mudaria os bytes entregues à impressora, e a promessa do
    # projeto é que eles cheguem exatamente como vieram da Shopee.
    tail = content[last_end:]
    if current is not None:
        labels.append(current + tail)
    elif (pending + tail).strip():
        labels.append(pending + tail)

    return [label for label in labels if label.strip()]


def load_labels_from_path(path: str) -> List[Tuple[str, bytes]]:
    """
    Aceita um .zip, uma pasta já extraída, ou um único arquivo .txt/.zpl.
    Retorna lista de tuplas (nome_origem, bytes_da_etiqueta).

    Raises:
        ParserError: Se o caminho não existir ou não contiver etiquetas
    """
    if not os.path.exists(path):
        raise ParserError(f"Caminho não existe: {path}")

    labels = []

    try:
        if os.path.isdir(path):
            source_files = find_label_files(path)
        elif path.lower().endswith(".zip"):
            tmp_dir = extract_zip_to_temp(path)
            source_files = find_label_files(tmp_dir)
        else:
            source_files = [path]

        if not source_files:
            raise ParserError(
                f"Nenhuma etiqueta encontrada em: {path}\n"
                "Procurando por: .txt, .zpl, .prn, .tspl"
            )

        for file_path in source_files:
            try:
                with open(file_path, "rb") as f:
                    raw = f.read()

                if not raw:
                    logger.warning(f"Arquivo vazio: {file_path}")
                    continue

                # decodifica em latin-1 (1 byte = 1 char, não perde nenhum byte)
                text = raw.decode("latin-1")
                blocks = split_labels(text)

                for i, block in enumerate(blocks):
                    name = Path(file_path).name
                    if len(blocks) > 1:
                        name = f"{name} (etiqueta {i + 1}/{len(blocks)})"
                    labels.append((name, block.encode("latin-1")))

                logger.info(f"Carregadas {len(blocks)} etiqueta(s) de {Path(file_path).name}")

            except Exception as e:
                logger.error(f"Erro ao ler arquivo {file_path}: {str(e)}")
                raise ParserError(f"Erro ao ler {Path(file_path).name}: {str(e)}")

        if not labels:
            raise ParserError("Nenhuma etiqueta válida foi carregada")

        logger.info(f"Total: {len(labels)} etiqueta(s) carregada(s)")
        return labels

    except ParserError:
        raise
    except Exception as e:
        raise ParserError(f"Erro desconhecido ao carregar etiquetas: {str(e)}")
