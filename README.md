# 🖨️ Shopee Label Printer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%2B-0078d4)

**Imprima etiquetas de envio da Shopee direto na sua impressora térmica, sem perder qualidade.**

Importa os ZIPs baixados da Shopee, extrai as etiquetas em formato ZPL/TSPL, **mostra o preview de cada uma em 203 DPI** e envia **em modo RAW** (bytes crus) para uma impressora térmica compatível — preservando 100% da resolução original, sem conversão para PDF ou reamostragem.

## 🖥️ Duas versões

| | 💻 **Desktop** (.exe) | 🌐 **Web** ([abrir](https://brunotrolo.github.io/Shopee_Printer/)) |
|---|---|---|
| Importar ZIP / pasta / TXT | ✅ | ✅ |
| Separar etiquetas concatenadas | ✅ | ✅ |
| Preview em 203 DPI | ✅ | ✅ |
| **Envio RAW (resolução máxima)** | ✅ | ❌ o navegador não permite |
| Impressão pelo driver do sistema | — | ✅ em 100 × 150 mm |
| Imprimir várias de uma vez | ✅ | ❌ uma por vez |
| Exportar PNG / ZPL | — | ✅ |
| Instalação | baixar o .exe | ✅ nenhuma |
| Mac / Linux / celular | ❌ Windows | ✅ qualquer navegador |
| Dados ficam no seu computador | ✅ | ✅ |

As duas compartilham o mesmo algoritmo de decodificação (`renderer.py` e `docs/zpl.js`), então **o preview é idêntico**. A diferença está só em como cada uma chega até a impressora.

> **Por que a web não imprime em RAW?** Nenhum navegador consegue mandar bytes crus para uma impressora — é uma restrição do sandbox do navegador, não uma limitação deste projeto. A versão web imprime pelo driver do sistema, no tamanho físico exato. Para a fidelidade byte a byte na FY-1075, use a versão desktop.

**Fluxo recomendado:** confira as etiquetas no navegador — de qualquer aparelho, sem instalar nada — e mande imprimir pelo desktop.

## 🎯 O que faz

✅ Importar ZIP, pasta ou arquivo TXT/ZPL avulso da Shopee  
✅ Separar automaticamente múltiplas etiquetas concatenadas no mesmo arquivo  
✅ **Preview da etiqueta antes de imprimir**, na resolução nativa da impressora  
✅ Enviar em modo RAW direto para a impressora térmica (não passa por PDF)  
✅ Rodar 100% localmente — seus dados de endereço nunca são enviados a servidores  
✅ **Zero dependências externas** — não precisa `pip install` nada além do Python

## ⚡ Início Rápido

### Opção A: Versão web (não instala nada)

Abra **[brunotrolo.github.io/Shopee_Printer](https://brunotrolo.github.io/Shopee_Printer/)**, arraste o ZIP e veja o preview. Funciona em Chrome 80+, Edge 80+, Firefox 113+ e Safari 16.4+.

### Opção B: Usar o .exe standalone (sem Python)

1. Baixe o `ShopeeLabelPrinter.exe` mais recente em [Releases](https://github.com/brunotrolo/Shopee_Printer/releases)
2. Dê duplo clique no `.exe` — nenhuma instalação necessária
3. Funciona em qualquer Windows 10/11, com ou sem Python instalado

> ⚠️ **Ainda não há nenhuma Release publicada.** O `.exe` é gerado pelo GitHub
> Actions — veja [como gerar](#-como-gerar-o-exe) logo abaixo. É de graça e não
> precisa instalar nada no seu computador.

## 🏗️ Como gerar o .exe

O `.exe` é compilado pelo GitHub, num Windows de verdade — você não precisa ter
o PyInstaller nem o Python instalados. Há dois jeitos.

### Jeito 1: pelo site, só clicando (mais fácil)

Serve para testar. O arquivo fica guardado por 90 dias na página da execução.

1. Vá em **[Actions](https://github.com/brunotrolo/Shopee_Printer/actions)**
2. Na coluna da esquerda, clique em **Build Executável**
3. À direita, clique em **Run workflow** → escolha `main` → **Run workflow**
4. Espere uns 3–5 minutos (a bolinha fica verde ✓)
5. Clique na execução e baixe **ShopeeLabelPrinter-exe**, no rodapé da página
6. É um `.zip` — descompacte e o `.exe` está dentro

### Jeito 2: publicar uma Release (o link permanente)

É isto que faz o botão "Baixar" do site funcionar e cria o link
`releases/latest/download/ShopeeLabelPrinter.exe`.

1. Vá em **[Releases](https://github.com/brunotrolo/Shopee_Printer/releases)** → **Create a new release**
2. Em **Choose a tag**, digite a versão atual do projeto — hoje `v0.3.1`
   (veja em `__init__.py`) — e clique em **Create new tag: v0.3.1 on publish**
3. Em **Release title**, escreva `v0.3.1`
4. Clique em **Publish release**
5. Isso dispara o build sozinho; em uns minutos o `.exe` aparece anexado à Release

> A tag deve bater com a versão do pacote. O `v1.0.0` está reservado para
> depois do teste de impressão na FY-1075 real — enquanto isso não acontecer,
> chamar de 1.0.0 seria dizer que está pronto sem ninguém ter conferido.

#### ⚠️ Se você apagar uma Release e criar de novo

**Apagar a Release não apaga a tag.** Ao recriar reaproveitando a tag que
sobrou, o GitHub não dispara evento de tag nova — antigamente o build não
rodava e a Release ficava publicada sem o `.exe`. O workflow hoje também
reage a `release: published`, então isso já está resolvido.

Mas atenção a outra coisa: **a tag continua apontando para o commit antigo**.
Se houve correções depois dela, o `.exe` sai com o código velho. Para pegar o
código atual, apague também a tag e use uma versão nova:

1. **Code** → **Tags** → aba de tags → apague a tag antiga
2. Crie a Release com uma tag nova (ex: `v0.3.2`), que nasce apontando para o
   topo da `main`

> **Windows vai avisar "editor desconhecido"** na primeira execução — é esperado,
> porque o `.exe` não tem assinatura digital paga. Clique em
> **Mais informações → Executar assim mesmo**.

### Opção C: Rodar com Python instalado

1. Instale Python 3.10+: https://www.python.org/downloads/
   - Na instalação, marque **"Add Python to PATH"**
2. Clone o repositório ou baixe como ZIP
3. Abra o terminal/PowerShell na pasta do projeto e execute:
   ```bash
   python -m shopee_label_printer
   ```
4. Selecione seu ZIP da Shopee, confira o preview, escolha a impressora e clique em **"Imprimir"**

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
2. **Conferir**: Veja a lista de etiquetas encontradas e **o preview de cada uma**
3. **Selecionar impressora**: Escolha sua impressora térmica no dropdown
4. **Imprimir**: Clique em **"Imprimir todas"** ou selecione algumas e clique em **"Selecionadas"**
5. **Log**: Acompanhe o andamento — ele avisa se alguma etiqueta falhou

## 🔍 Como funciona o preview

A etiqueta da Shopee traz o desenho embutido como um bitmap nos comandos `~DG` / `^GFA`.
O preview decodifica esse bitmap e mostra **1 pixel para cada ponto impresso** — ou seja,
exatamente o que vai sair na FY-1075 (203 DPI, 812 × 1218 pontos numa etiqueta 100 × 150 mm).

São aceitos os três formatos que a ZPL usa para o campo gráfico: hexadecimal puro,
hexadecimal com compressão ASCII (`G-Y`, `g-z`, `,`, `!`, `:`) e `:Z64:` / `:B64:`.
Comandos vetoriais (`^GB`, `^FD`, `^BC` Code 128) são desenhados por cima.

Para caber na tela, a imagem é reduzida por **média de área** e não por vizinho mais
próximo — sem isso, as barras de 1 ponto do código de barras sumiriam na redução.

> O preview **nunca altera os bytes** que vão para a impressora: ele só lê. O envio
> continua sendo o arquivo original, byte a byte.

## 📁 Estrutura do Projeto

```
shopee-label-printer/
├── src/
│   └── shopee_label_printer/
│       ├── __init__.py          # Pacote
│       ├── __main__.py          # Ponto de entrada (python -m)
│       ├── app.py               # Interface gráfica (tkinter) + preview
│       ├── parser.py            # Extração de ZIP + separação de etiquetas
│       ├── printer.py           # Envio RAW + listagem de impressoras
│       ├── renderer.py          # Decodificação ZPL -> imagem (preview)
│       ├── config.py            # Configuração persistente
│       ├── logger.py            # Log em arquivo + tela
│       ├── utils.py             # Ordenação de impressoras, formatação
│       └── validators.py        # Validação de etiquetas
├── tests/                       # 125 testes automatizados
├── docs/                        # ► APLICATIVO WEB (GitHub Pages)
│   ├── index.html               # Interface
│   ├── app.js                   # Lógica da tela
│   ├── zip.js                   # Leitura de ZIP (DecompressionStream)
│   ├── zpl.js                   # Renderizador ZPL (porta de renderer.py)
│   └── style.css
├── LEIA-ME.md                   # Instruções de uso (português)
├── PLANO_DESENVOLVIMENTO.md     # Roadmap detalhado (5 fases)
├── CHANGELOG.md                 # Histórico de versões
├── LICENSE                      # MIT
└── README.md                    # Este arquivo
```

### Versão web em desenvolvimento

A pasta `docs/` é servida direto pelo GitHub Pages — não há build. Para testar local:

```bash
cd docs && python -m http.server 8000
# abra http://localhost:8000
```

`docs/zpl.js` é uma porta fiel de `src/shopee_label_printer/renderer.py`.
**Mudou a decodificação num? Mude no outro** — os dois devem produzir a mesma
imagem para a mesma etiqueta.

## 🔧 Desenvolvimento

### Rodar os testes

```bash
pip install pytest
pytest tests/
```

### Módulos

- **`parser.py`**: Extração de ZIP, busca de arquivos, separação de etiquetas
- **`printer.py`**: Listagem de impressoras, envio RAW via winspool/lp
- **`renderer.py`**: Decodificação do ZPL em imagem, para o preview
- **`app.py`**: Interface gráfica em tkinter

Isso permite testar parsing, decodificação e impressão sem precisar de GUI nem de impressora real.

### Gerar .exe standalone

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "ShopeeLabelPrinter" src/shopee_label_printer/app.py
```

O `.exe` será criado em `dist/ShopeeLabelPrinter.exe`.

## 📊 Roadmap

Veja [PLANO_DESENVOLVIMENTO.md](PLANO_DESENVOLVIMENTO.md) para o plano detalhado em 5 fases:

1. ✅ **Fase 0**: Fundação do repositório (estrutura de pastas, modularização)
2. ⏳ **Fase 1**: Estabilização — tratamento de erros e logging prontos; **falta o teste na FY-1075**
3. ✅ **Fase 2**: Empacotamento profissional (CI/CD, GitHub Actions, GitHub Releases)
4. ✅ **Fase 3**: Robustez de parsing (casos-limite, decodificação de gráficos)
5. ✅ **Fase 4-5**: UX + preview + versão web no GitHub Pages

## ⚠️ Limitações Conhecidas

- **Teste em hardware real ainda não foi feito** — a lógica e a decodificação foram validadas com testes automatizados, mas a impressão na FY-1075 continua sendo o bloqueador do 1.0.0
- A **versão web não imprime em RAW** — nenhum navegador consegue; ela imprime pelo driver do sistema, no tamanho físico exato
- **QR Code (`^BQ`) aparece como marcador** no preview, não decodificado. Na prática isso raramente aparece: a Shopee manda a etiqueta inteira como bitmap, e aí o QR vem desenhado dentro dele — o que é renderizado normalmente
- Envio RAW oficialmente só no Windows (macOS/Linux têm fallback para CUPS, não testado)
- A impressora deve estar instalada antes de abrir o programa

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
