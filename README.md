# 🖨️ Shopee Label Printer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%2B-0078d4)

**Imprima etiquetas de envio da Shopee direto na sua impressora térmica, sem perder qualidade.**

Este programa importa ZIPs baixados da Shopee, extrai as etiquetas em formato ZPL/TSPL e envia cada uma **em modo RAW** (bytes crus) para uma impressora térmica compatível — preservando 100% da resolução original, sem conversão para PDF ou reamostragem.

## 🎯 O que faz

✅ Importar ZIP, pasta ou arquivo TXT/ZPL avulso da Shopee  
✅ Separar automaticamente múltiplas etiquetas concatenadas no mesmo arquivo  
✅ Enviar em modo RAW direto para a impressora térmica (não passa por PDF)  
✅ Interface gráfica amigável (tkinter)  
✅ Rodar 100% localmente — seus dados de endereço nunca são enviados a servidores  
✅ **Zero dependências externas** — não precisa `pip install` nada além do Python

## ⚡ Início Rápido

### Opção A: Rodar com Python instalado

1. Instale Python 3.10+: https://www.python.org/downloads/
   - Na instalação, marque **"Add Python to PATH"**

2. Clone o repositório ou baixe como ZIP

3. Abra o terminal/PowerShell na pasta do projeto e execute:
   ```bash
   python -m shopee_label_printer
   ```

4. Selecione seu ZIP da Shopee, escolha a impressora e clique em **"Imprimir"**

### Opção B: Usar o .exe standalone (sem Python)

1. Baixe o arquivo `ShopeeLabelPrinter.exe` mais recente em [Releases](https://github.com/brunotrolo/Shopee_Printer/releases)

2. Dê duplo clique no `.exe` — é isso, nenhuma instalação necessária

3. Funciona em qualquer Windows 10/11, com ou sem Python instalado

## 📋 Requisitos

### Sistema
- **Windows 10/11** (alvo principal)
- **Python 3.10+** (se rodar como script Python)
- Uma **impressora térmica compatível com TSPL/ZPL** (ex: FY-1075 203 DPI)

### Impressora
A impressora deve:
- Estar instalada e conectada no Windows antes de abrir o programa
- Aparecer em **Painel de Controle > Dispositivos e Impressoras**
- Ser compatível com comandos TSPL/ZPL (a maioria das térmicas de etiqueta funciona)

## 🚀 Como usar

1. **Importar**: Clique em **"Importar ZIP / Pasta / TXT"** e selecione o arquivo da Shopee
2. **Conferir**: Veja a lista de etiquetas encontradas
3. **Selecionar impressora**: Escolha sua impressora térmica no dropdown
4. **Imprimir**: Clique em **"Imprimir todas"** ou selecione algumas e clique em **"Imprimir selecionadas"**
5. **Log**: Acompanhe o andamento — ele avisa se alguma etiqueta falhou

## 📁 Estrutura do Projeto

```
shopee-label-printer/
├── src/
│   └── shopee_label_printer/
│       ├── __init__.py          # Pacote
│       ├── __main__.py          # Ponto de entrada (python -m)
│       ├── app.py               # Interface gráfica (tkinter)
│       ├── parser.py            # Extração de ZIP + separação de etiquetas
│       └── printer.py           # Envio RAW + listagem de impressoras
├── tests/
│   ├── test_parser.py           # Testes do parser
│   ├── test_printer.py          # Testes da impressão (mock)
│   └── fixtures/                # Dados de teste
├── docs/                        # Documentação (GitHub Pages)
├── LEIA-ME.md                   # Instruções de uso (português)
├── PLANO_DESENVOLVIMENTO.md     # Roadmap detalhado (5 fases)
├── CHANGELOG.md                 # Histórico de versões
├── LICENSE                      # MIT
└── README.md                    # Este arquivo
```

## 🔧 Desenvolvimento

### Rodar os testes

```bash
pip install pytest
pytest tests/
```

### Modularizar o código

O projeto está separado em 3 módulos principais:

- **`parser.py`**: Extração de ZIP, busca de arquivos, separação de etiquetas
- **`printer.py`**: Listagem de impressoras, envio RAW via winspool/lp
- **`app.py`**: Interface gráfica em tkinter

Isso permite testar a lógica de arquivo e impressão sem precisar de uma GUI ou impressora real.

### Gerar .exe standalone

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "ShopeeLabelPrinter" src/shopee_label_printer/app.py
```

O `.exe` será criado em `dist/ShopeeLabelPrinter.exe`.

## 📊 Roadmap

Veja [PLANO_DESENVOLVIMENTO.md](PLANO_DESENVOLVIMENTO.md) para o plano detalhado em 5 fases:

1. ✅ **Fase 0**: Fundação do repositório (estrutura de pastas, modularização)
2. ⏳ **Fase 1**: Estabilização (teste FY-1075, tratamento de erros, logging)
3. ⏳ **Fase 2**: Empacotamento profissional (CI/CD, GitHub Actions, GitHub Releases)
4. ⏳ **Fase 3**: Robustez de parsing (casos-limite, fixtures reais)
5. ⏳ **Fase 4-5**: UX + documentação (GitHub Pages, features extras)

## ⚠️ Limitações Conhecidas

- **Teste em hardware real ainda não foi feito** — a lógica foi validada, mas impressão na FY-1075 precisa ser testada
- Suporte oficial apenas para Windows (macOS/Linux têm fallback para CUPS, não testado)
- Impressora deve estar instalada antes de abrir o programa

## 🤝 Contribuição

Este é um projeto pessoal/pequeno. Contribuições em forma de:
- Relatos de bug
- Testes em diferentes impressoras
- Melhorias na documentação
- Sugestões de features

...são bem-vindas! Abra uma issue ou pull request.

## 📄 Licença

MIT — veja [LICENSE](LICENSE) para detalhes.

## 📧 Contato

Bruno Trolo — [@brunotrolo](https://github.com/brunotrolo)

---

**Dúvidas?** Leia o [LEIA-ME.md](LEIA-ME.md) para instruções de uso ou o [PLANO_DESENVOLVIMENTO.md](PLANO_DESENVOLVIMENTO.md) para detalhes técnicos.
