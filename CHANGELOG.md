# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/),
e este projeto segue [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não Lançado]

### Adicionado
- Estrutura de pastas profissional (src/, tests/, docs/)
- Modularização do código (parser.py, printer.py, app.py)
- Suite básica de testes com pytest
- README.md completo com instruções
- CHANGELOG.md (este arquivo)

### Planejado para v1.0.0
- Teste de impressão na impressora FY-1075 real
- Logging em arquivo
- Tratamento de erros mais robusto
- CI/CD com GitHub Actions
- GitHub Pages com documentação

## [0.1.0] - 2026-08-08

### Adicionado
- MVP funcional: importação de ZIP, separação de etiquetas, envio RAW
- Interface gráfica em tkinter
- Suporte para Windows (winspool) e macOS/Linux (CUPS)
- Zero dependências externas (apenas stdlib Python)
- PyInstaller configurado para gerar .exe standalone
