# 🤝 Guia de Contribuição

Obrigado por considerar contribuir para o ShopeeLabelPrinter! Este documento descreve como fazer isso.

## 📋 Código de Conduta

Esperamos que todos os contribuidores mantenham um ambiente respeitoso e inclusivo. Violações podem resultar em exclusão.

---

## 🚀 Como Começar

### 1. Prepare o Ambiente

```bash
# Clone o repositório
git clone https://github.com/brunotrolo/ShopeeLabelPrinter.git
cd ShopeeLabelPrinter

# Crie um ambiente virtual (recomendado)
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate

# Instale dependências de desenvolvimento
pip install -e ".[dev]"
```

### 2. Crie uma Branch

```bash
git checkout -b feature/sua-feature
# Ou para bug fix:
git checkout -b fix/descricao-bug
```

### 3. Faça suas Mudanças

**Siga estes padrões:**

- **Estilo de código**: Python 3.10+, seguindo PEP 8
- **Type hints**: Adicione tipos em novos métodos/funções
- **Docstrings**: Código novo deve ter docstrings (formato Google)
- **Testes**: Adicione testes para novas features
- **Logging**: Use `logger` em vez de `print()`, sem f-strings

**Exemplo:**

```python
def process_label(data: bytes, boost: str = "leve") -> bytes:
    """
    Processa etiqueta ZPL com reforço opcional.
    
    Args:
        data: Bytes da etiqueta em ZPL
        boost: Nível de reforço ("leve", "medio", "forte")
    
    Returns:
        Bytes processados prontos para impressora
    
    Raises:
        ValueError: Se boost não está em níveis válidos
    """
    logger.info("Processando etiqueta com boost=%s", boost)
    # ... implementação
    return processed_data
```

### 4. Rode Testes e Linting

```bash
# Testes
pytest tests/ -v

# Type checking
mypy src/shopee_label_printer/

# Linting
ruff check src/ tests/

# Cobertura de testes
pytest tests/ --cov=src --cov-report=html
```

### 5. Commit com Mensagem Clara

```bash
git add <arquivos>
git commit -m "🐛 Fix: Corrigir injeção de comando em _show_log_dir()

- Usar subprocess.run() em vez de os.system()
- Suportar Windows, macOS e Linux
- Adicionar tratamento de erro com messagebox

Fixes #123"
```

**Use emojis no início:**
- 🐛 `fix:` - Correção de bug
- ✨ `feat:` - Nova feature
- 🐎 `perf:` - Melhoria de performance
- 📚 `docs:` - Documentação
- 🔒 `security:` - Problema de segurança
- ♻️ `refactor:` - Refatoração
- ✅ `test:` - Testes

### 6. Abra uma Pull Request

**Checklist antes de fazer push:**

- [ ] Testes passando (`pytest tests/`)
- [ ] Type checking passando (`mypy src/`)
- [ ] Linting passando (`ruff check`)
- [ ] Cobertura não diminuiu
- [ ] Commits com mensagens claras
- [ ] Docstrings adicionadas
- [ ] Type hints adicionados (onde aplicável)

**Abra PR com descrição clara:**

```markdown
## 📝 Descrição

Breve descrição do que foi mudado e por quê.

## 🔗 Issue

Fecha #123

## 🧪 Teste

Como testar a mudança:
- [ ] Passo 1
- [ ] Passo 2

## 📸 Screenshots

Se aplicável, adicione screenshots.
```

---

## 📂 Estrutura de Diretórios

```
src/shopee_label_printer/
├── __init__.py              # Versão e exports
├── __main__.py              # Ponto de entrada CLI
├── app.py                   # Interface gráfica (tkinter)
├── printer.py               # Integração com impressora
├── renderer.py              # Renderização de preview
├── parser.py                # Parse de arquivos ZPL/TSPL
├── converters.py            # Conversão de formatos (ZPL→TSPL→PDF)
├── config.py                # Configurações
├── validators.py            # Validação de dados
├── logger.py                # Sistema de logging
└── utils.py                 # Funções utilitárias

tests/
├── conftest.py              # Fixtures compartilhadas
├── test_parser.py           # Testes de parser
├── test_renderer.py         # Testes de renderer
├── test_printer.py          # Testes de printer
├── test_converters.py       # Testes de converters
├── test_config.py           # Testes de config
├── test_validators.py       # Testes de validators
├── test_utils.py            # Testes de utils
└── test_integration.py      # Testes end-to-end
```

---

## 🎯 Áreas Prioritárias

### 🚀 Oportunidades de Contribuição

**Fácil (bom para começar):**
- Melhorar docstrings em módulos Python
- Adicionar mais testes
- Melhorar documentação em português/inglês
- Criar exemplos de uso

**Médio:**
- Refatorar UI (extrair classes PreviewPanel, PrinterControls)
- Adicionar configurações visuais (temas, fontes)
- Melhorar mensagens de erro

**Difícil:**
- Suporte a macOS/Linux (impressoras CUPS)
- Melhorar performance de renderização
- Novos formatos de arquivo (SVG, etc)

---

## 🐛 Reportando Bugs

Use GitHub Issues com template abaixo:

```markdown
## 🐛 Descrição do Bug

Descrição clara e concisa.

## 📋 Passos para Reproduzir

1. Faça login
2. Carregue arquivo X
3. Clique em "Imprimir"

## ❌ Comportamento Atual

O que acontece de errado

## ✅ Comportamento Esperado

O que deveria acontecer

## 📸 Screenshots

Se aplicável

## 🖥️ Ambiente

- OS: Windows 10 / macOS / Linux
- Navegador: Chrome / Firefox / Safari
- Versão: v0.5.0
```

---

## ❓ Dúvidas?

- 📧 Email: bruno@trolo.dev
- 🐦 Twitter: [@brunotrolo](https://twitter.com/brunotrolo)
- 💬 GitHub Issues: [Abra uma issue](https://github.com/brunotrolo/ShopeeLabelPrinter/issues)

---

## 📜 Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob a [MIT License](LICENSE).
