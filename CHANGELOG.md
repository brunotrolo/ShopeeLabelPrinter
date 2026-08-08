# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/),
e este projeto segue [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não Lançado]

### Planejado para v1.0.0
- ⏳ Teste de impressão na impressora FY-1075 real (bloqueador do 1.0.0)
- ⏳ Renderização de QR Code no preview (hoje aparece como marcador)
- ⏳ Impressão de várias etiquetas de uma vez na versão web
- ⏳ Suporte a múltiplos idiomas (i18n)

## [0.3.0] - 2026-08-08

### Adicionado
- **Preview da etiqueta** na resolução nativa da impressora (203 DPI, 1 pixel = 1 ponto):
  - Novo módulo `renderer.py` que decodifica os bitmaps embutidos (`~DG`, `^GFA`)
    nos três formatos que a ZPL aceita: hex puro, hex com compressão ASCII
    (`G-Y`, `g-z`, `,`, `!`, `:`) e `:Z64:`/`:B64:`
  - Redução por média de área, que preserva traços de 1 ponto — sem isso o
    código de barras vira um borrão no preview reduzido
  - Renderização de `^GB` (caixas), `^FD` (texto) e `^BC` (Code 128)
- **Versão web** em `docs/`, publicada no GitHub Pages:
  - Importa ZIP por clique ou arrastar-e-soltar, lendo o ZIP no próprio
    navegador com `DecompressionStream` — sem biblioteca externa e sem upload
  - Mesmo preview em 203 DPI da versão desktop (mesmo algoritmo de decodificação)
  - Exportar PNG, exportar o ZPL original e imprimir no tamanho físico exato
  - Layout responsivo e tema claro/escuro automático
- **Preview no aplicativo desktop**: painel lateral com zoom (ajustar / 100% / 50% / 33% / 25%)
- 47 novos testes automatizados (total: 125)

### Corrigido
- **Etiqueta fantasma em branco**: um arquivo com uma única etiqueta era
  dividido em duas porque a separação cortava no `~DG`, que fica *dentro* do
  bloco `^XA...^XZ` — isso separava o cabeçalho (`^XA^PW^LL`) da imagem. O
  bloco vazio aparecia na lista e era enviado à impressora no "Imprimir todas".
  Agora o corte é feito no `^XA`, com o `~DG` só como alternativa para arquivos
  que não têm `^XA` nenhum.
- **Aplicativo desktop travava ao abrir**: `setup_logging()` emitia a primeira
  mensagem antes de `_build_ui()` criar o widget de log, causando `AttributeError`
  na inicialização.
- Preview respeitava o preenchimento do bitmap: uma etiqueta de 812 pontos ocupa
  102 bytes por linha (816 bits) e os 4 bits de sobra apareciam como margem.

### Mudado
- Versão: 0.2.0 → 0.3.0
- `docs/` deixou de ser uma página institucional e passou a ser o aplicativo web
- `pyproject.toml` estava com a versão desatualizada (0.1.0)

## [0.2.0] - 2026-08-08

### Adicionado
- **Logging profissional**: arquivo em %APPDATA%/ShopeeLabelPrinter + console
- **Tratamento robusto de erros**: classes ParserError e PrinterError com mensagens amigáveis
- **Suite de testes expandida**: 72 testes automatizados (parser, printer, validators, config, utils)
- **Validadores de rótulo**: validação de ZPL/TSPL, tamanho, encoding
- **Sistema de configuração**: persistent settings em JSON
- **Estatísticas de uso**: histórico de impressões, impressora favorita
- **GitHub Actions**: workflows para CI/CD (testes + build automático)
- **Melhorias de UX**: 
  - Detecção automática de impressora térmica
  - Botão para abrir diretório de logs
  - Indicadores visuais (✓, ❌, ⚠️)
  - Formatação melhorada da interface

### Mudado
- Versão: 0.1.0 → 0.2.0
- Módulos separados agora com tratamento de erros robusto

### Melhorado
- Interface com feedback visual durante operações
- Mensagens de erro mais explicativas
- Logging de cada etapa da importação e impressão

## [0.1.0] - 2026-08-08

### Adicionado
- MVP funcional: importação de ZIP, separação de etiquetas, envio RAW
- Interface gráfica em tkinter
- Suporte para Windows (winspool) e macOS/Linux (CUPS)
- Zero dependências externas (apenas stdlib Python)
- PyInstaller configurado para gerar .exe standalone
- Estrutura de repositório profissional (src/, tests/, docs/)
- Modularização (parser.py, printer.py, app.py)
- Documentação básica (README, CHANGELOG, LICENSE)
