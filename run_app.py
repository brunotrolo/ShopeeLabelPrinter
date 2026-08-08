"""
Ponto de entrada do executável Windows (PyInstaller).

Por que este arquivo existe: o __main__.py usa import relativo
(`from .app import main`), que só funciona quando o Python trata a pasta como
pacote — ou seja, via `python -m shopee_label_printer`. O PyInstaller executa
o arquivo de entrada como script solto, sem contexto de pacote, e o import
relativo falha com "attempted relative import with no known parent package".

Este lançador usa import absoluto e funciona nos dois casos.
"""

import os
import sys

# Rodando a partir do código-fonte: precisa achar o pacote em src/.
# No executável já congelado o pacote vem embutido, então não mexe no path.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from shopee_label_printer.app import main

if __name__ == "__main__":
    main()
