# 🖨️ Shopee Label Print — Guia de Uso

Aplicativo profissional para imprimir etiquetas de envio da Shopee diretamente na sua impressora térmica, preservando 100% da resolução original.

**Disponível em:** Aplicativo desktop (.exe), versão web, ou biblioteca Python.

---

## ⚡ Início Rápido

### 🌐 Versão Web (Sem Instalação)
Abra https://brunotrolo.github.io/Shopee_Printer/, arraste seu ZIP da Shopee e veja o preview. Funciona em: Chrome 80+, Edge 80+, Firefox 113+, Safari 16.4+.

### 💻 Versão Desktop (.exe)
1. Baixe o `ShopeeLabelPrinter.exe` mais recente em [Releases](https://github.com/brunotrolo/Shopee_Printer/releases)
2. Execute o arquivo (nenhuma instalação necessária)
3. Funciona em Windows 10/11 — Python não é obrigatório

### 🐍 Versão Python
```bash
python -m shopee_label_printer
```
Requer Python 3.10+ (zero dependências externas)

---

## 🎯 O Que Faz

✅ **Importar** ZIP da Shopee, pastas ou arquivos TXT/ZPL/PRN/TSPL avulsos  
✅ **Separar automaticamente** múltiplas etiquetas concatenadas num mesmo arquivo  
✅ **Preview** de cada etiqueta na resolução nativa (203 DPI)  
✅ **Enviar RAW** para impressoras térmicas sem perder qualidade (apenas desktop)  
✅ **100% local** — seus dados de endereço não saem do seu computador  
✅ **Sem dependências** — usa apenas a biblioteca padrão do Python  
✅ **Versão web** — funciona em qualquer navegador moderno  

---

## 🚀 Como Usar

### Desktop (.exe)
1. Abra o programa
2. Clique em **"Importar ZIP / Pasta / TXT"** e selecione um arquivo da Shopee
3. Confira a lista de etiquetas encontradas e o **preview de cada uma** em 203 DPI
4. Escolha sua impressora térmica no dropdown
5. Clique em **"Imprimir Todas"** ou selecione algumas e clique em **"Imprimir Selecionadas"**
6. Acompanhe o log — ele avisa se alguma etiqueta falhar

### Versão Web
1. Abra https://brunotrolo.github.io/Shopee_Printer/
2. Arraste o ZIP para a área de soltar (ou clique para selecionar)
3. Escolha o **Modo de Saída**: **ZPL** (nativo), **TSPL** (FY-1075 compatível) ou **PDF**
4. Ajuste o **Reforço** se necessário (Leve/Médio/Forte/Customizado)
5. Baixe ou imprima pelo navegador

---

## 🖨️ Requisitos

### Windows Desktop / .exe
- **Windows 10/11** (64-bit)
- Impressora térmica compatível com **TSPL/ZPL** (ex: Godex FY-1075 a 203 DPI)
- Conexão USB ou rede à impressora

### Versão Web
- Navegador moderno (Chrome 80+, Edge 80+, Firefox 113+, Safari 16.4+)
- Sem instalação de software
- Funciona em Windows, Mac, Linux, iOS, Android

### Versão Python
- Python 3.10 ou superior
- Windows 10/11 (conexão à impressora via `winspool.drv`)
- macOS/Linux com suporte (usa CUPS, não totalmente testado)

---

## 🔍 Como Funciona o Preview

As etiquetas da Shopee trazem gráficos embutidos nos comandos `~DG` / `^GFA`. O preview:

- **Decodifica o bitmap** de hexadecimal ZPL (raw, compressão ASCII, Base64)
- **Renderiza 1:1** em 203 DPI (812 × 1218 pixels = 100 × 150 mm)
- **Redimensiona para exibição** usando média de área (preserva detalhes de 1 pixel)
- **Desenha elementos vetoriais** (códigos de barras Code 128, linhas, texto) por cima

O preview **nunca modifica** os bytes enviados à impressora — é apenas leitura. A impressora recebe o arquivo original byte a byte.

---

## ⚙️ Ajustes de Qualidade

### Reforço (Boost)
O programa oferece controles de **Reforço** para ajustar densidade e velocidade de impressão:
- **Leve** — traço mais firme
- **Médio** — traço bem escuro
- **Forte** — pode borrar o código
- **Customizado** — ajuste manual de DENSITY e SPEED
- **Desligado** — bytes originais (sem alteração)

**⚠️ Limitação conhecida:** Em testes com a FY-1075 atual, todos os níveis de reforço produzem resultado idêntico. Os controles estão inclusos para futuras melhorias e compatibilidade com outras impressoras.

### Modo de Saída
Escolha o formato para envio:
- **ZPL** — formato nativo Zebra (recomendado para impressoras Zebra genuínas)
- **TSPL** — formato TSC/Godex (recomendado para FY-1075)
- **PDF** — arquivo PDF (para guardar ou imprimir por outro caminho)

---

## 🐛 Solução de Problemas

### Lista de impressoras vazia?
- Certifique-se de que a impressora está instalada e conectada no Windows
- Ela deve aparecer em **Painel de Controle > Dispositivos e Impressoras**
- Reinicie o aplicativo

### Etiquetas saem com linhas finas ou muito escuras?
- **Desktop:** Ajuste o **Reforço** (Leve/Médio/Forte/Customizado) antes de imprimir
- **Web:** Use o dropdown **Modo de Saída** + configurações de **Reforço**
- **Nota:** Os controles de reforço estão inclusos para futuro; atualmente produzem saída idêntica

### Preview não mostra nada?
- Certifique-se de que o ZIP da Shopee contém arquivos ZPL/TSPL válidos
- Verifique se o arquivo não está corrompido
- Tente exportar como PNG primeiro para isolar o problema

### Não consegue imprimir pela web?
- Use a versão desktop para impressão em modo RAW
- A versão web é melhor para preview e exportação (PNG, PDF)

---

## 📁 Estrutura do Projeto

```
Shopee-Label-Print/
├── src/shopee_label_printer/
│   ├── __init__.py              # Metadados do pacote
│   ├── __main__.py              # Ponto de entrada (python -m)
│   ├── app.py                   # GUI (tkinter) + preview
│   ├── parser.py                # Extração ZIP + separação etiquetas
│   ├── printer.py               # Envio RAW + listagem impressoras
│   ├── renderer.py              # ZPL → decodificação imagem
│   ├── converters.py            # ZPL → conversão TSPL/PDF
│   ├── config.py                # Configurações persistentes
│   ├── logger.py                # Logging arquivo + console
│   ├── utils.js                 # Ordenação impressoras, formatação
│   └── validators.py            # Validação etiquetas
├── tests/                       # 125+ testes automatizados
├── docs/                        # App web (GitHub Pages)
│   ├── index.html
│   ├── app.js                   # Lógica frontend
│   ├── zpl.js                   # Decodificador ZPL (JavaScript)
│   ├── converters.js            # Conversão formatos
│   └── style.css
├── README.md                    # Documentação English
├── LEIA-ME.md                   # Este arquivo
├── PLANO_DESENVOLVIMENTO.md     # Roadmap técnico (5 fases)
├── CHANGELOG.md                 # Histórico versões
├── LICENSE                      # Licença MIT
└── ShopeeLabelPrinter.spec      # Configuração PyInstaller
```

---

## 🔧 Desenvolvimento

### Rodar Testes
```bash
pip install pytest
pytest tests/
```

### Gerar .exe
**Opção 1: Automático (GitHub Actions)**
1. Acesse [Actions](https://github.com/brunotrolo/Shopee_Printer/actions)
2. Selecione "Build Executável" → Run workflow
3. Baixe o `.exe` da execução concluída

**Opção 2: Manual com PyInstaller**
```bash
pip install pyinstaller
pyinstaller ShopeeLabelPrinter.spec --onefile --windowed
# Saída: dist/ShopeeLabelPrinter.exe
```

### Desenvolvimento Web Local
```bash
cd docs
python -m http.server 8000
# Abra http://localhost:8000
```

---

## 📊 Roadmap

Veja [PLANO_DESENVOLVIMENTO.md](PLANO_DESENVOLVIMENTO.md) para o plano detalhado:

1. ✅ **Fase 0**: Fundação do projeto
2. ⏳ **Fase 1**: Estabilização (pendente teste FY-1075 real)
3. ✅ **Fase 2**: Empacotamento profissional
4. ✅ **Fase 3**: Parsing robusto
5. ✅ **Fase 4–5**: UX, preview, versão web

---

## ⚠️ Limitações Conhecidas

- **Teste em hardware real pendente** — lógica e decodificação validadas com 125+ testes, mas impressão na FY-1075 real ainda não foi realizada
- **Versão web não envia RAW** — restrição do sandbox do navegador; imprime via driver do sistema
- **Todas as etiquetas importadas têm o mesmo resultado de impressão** — os controles de reforço estão inclusos para futuras melhorias e compatibilidade com outras impressoras
- Macros e sobreposições de código de barras não suportadas

---

## 🤝 Contribuindo

Contribuições bem-vindas:
- Relatos de bugs
- Testes em diferentes impressoras
- Melhorias na documentação
- Sugestões de features

Abra uma issue ou pull request no [GitHub](https://github.com/brunotrolo/Shopee_Printer).

---

## 📄 Licença

MIT — veja [LICENSE](LICENSE) para detalhes.

---

## 📞 Contato

**Bruno Trolo** — [@brunotrolo](https://github.com/brunotrolo)

Dúvidas? Consulte:
- [README.md](README.md) — Documentação em English
- [PLANO_DESENVOLVIMENTO.md](PLANO_DESENVOLVIMENTO.md) — Detalhes técnicos
- [CHANGELOG.md](CHANGELOG.md) — Histórico de versões

---

**Última atualização:** Agosto 2026  
**Versão:** v0.3.1+ (pendente teste FY-1075)
