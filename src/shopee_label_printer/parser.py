"""
Módulo de parsing: extração e separação de etiquetas.
"""

import os
import re
import zipfile
import tempfile
from pathlib import Path

LABEL_EXTENSIONS = {".txt", ".zpl", ".prn", ".tspl"}


def extract_zip_to_temp(zip_path: str) -> str:
    """Extrai o ZIP para uma pasta temporária e retorna o caminho dela."""
    tmp_dir = tempfile.mkdtemp(prefix="shopee_labels_")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmp_dir)
    return tmp_dir


def find_label_files(folder: str):
    """Varre a pasta (recursivo) procurando arquivos de etiqueta."""
    files = []
    for root, _dirs, names in os.walk(folder):
        for name in names:
            if Path(name).suffix.lower() in LABEL_EXTENSIONS:
                files.append(os.path.join(root, name))
    return sorted(files)


def split_labels(content: str):
    """
    Alguns arquivos trazem mais de uma etiqueta concatenada no mesmo TXT.
    Divide o conteúdo em blocos individuais, um por etiqueta.
    """
    if "~DG" in content:
        # Cada etiqueta com imagem embutida começa com ~DG
        parts = re.split(r"(?=~DG)", content)
    elif "^XA" in content:
        # ZPL sem imagem embutida: cada etiqueta começa com ^XA
        parts = re.split(r"(?=\^XA)", content)
    else:
        parts = [content]
    return [p for p in parts if p.strip()]


def load_labels_from_path(path: str):
    """
    Aceita um .zip, uma pasta já extraída, ou um único arquivo .txt/.zpl.
    Retorna lista de tuplas (nome_origem, bytes_da_etiqueta).
    """
    labels = []

    if os.path.isdir(path):
        source_files = find_label_files(path)
    elif path.lower().endswith(".zip"):
        tmp_dir = extract_zip_to_temp(path)
        source_files = find_label_files(tmp_dir)
    else:
        source_files = [path]

    for file_path in source_files:
        with open(file_path, "rb") as f:
            raw = f.read()
        # decodifica em latin-1 (1 byte = 1 char, não perde nenhum byte)
        text = raw.decode("latin-1")
        blocks = split_labels(text)
        for i, block in enumerate(blocks):
            name = Path(file_path).name
            if len(blocks) > 1:
                name = f"{name} (etiqueta {i + 1}/{len(blocks)})"
            labels.append((name, block.encode("latin-1")))

    return labels
