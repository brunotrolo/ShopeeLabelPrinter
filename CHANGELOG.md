# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/),
e este projeto segue [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não Lançado]

### Planejado para v1.0.0
- ⏳ Teste de impressão na impressora FY-1075 real
- ⏳ Detecção automática melhorada de impressora térmica
- ⏳ GitHub Pages com documentação completa
- ⏳ Suporte a múltiplos idiomas (i18n)

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
