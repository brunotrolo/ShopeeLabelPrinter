# 🔒 Política de Segurança

## Relatando Vulnerabilidades

Se você descobre uma vulnerabilidade de segurança no ShopeeLabelPrinter, **não abra uma issue pública**. Em vez disso, reporte de forma privada.

### 📧 Como Reportar

Envie um email para: **bruno@trolo.dev**

**Inclua:**
- Descrição da vulnerabilidade
- Passos para reproduzir
- Impacto potencial
- Sugestão de fix (se houver)

**NÃO inclua:**
- Proof-of-concept funcional
- Dados de testes reais
- Informações de sistema

### ⏱️ Processo

1. **Você reporta** → Recebemos em até 24h
2. **Investigamos** → Confirmamos e avaliamos impacto (até 7 dias)
3. **Corrigimos** → Fazemos patch e testamos
4. **Coordenação** → Combinamos data de divulgação pública
5. **Divulgação** → Release de segurança com crédito a você

---

## 🛡️ Práticas de Segurança

Este projeto segue estas práticas:

### ✅ Implementado

- ✅ **Zero Dependências Externas**: Apenas stdlib Python 3.10+
- ✅ **Type Hints**: Validação de tipos com mypy
- ✅ **Input Validation**: Todas as entradas são validadas (range, tipo, tamanho)
- ✅ **Error Handling**: Exceções específicas, sem leakage de info sensitiva
- ✅ **Logging**: Logs estruturados sem dados pessoais
- ✅ **Code Review**: PRs requerem review antes de merge
- ✅ **Automated Tests**: 1400+ LOC de testes com 56% cobertura
- ✅ **No Hardcoded Secrets**: Configurações via arquivo/env var

### 🔄 Verificações em CI/CD

- ✅ Testes em 3 OS (Windows, macOS, Linux)
- ✅ Testes em 3 Python versions (3.10, 3.11, 3.12)
- ✅ Type checking com mypy
- ✅ Linting com ruff
- ✅ Code coverage tracking

---

## 🚫 Conhecidas Limitações

### Segurança de Dados

**Dados 100% Locais:**
- Etiquetas Shopee **nunca** saem do computador
- Nada é enviado para servidor externo
- Conversões acontecem offline

**Exceção - Versão Web:**
- Dados processados no browser do usuário (JavaScript)
- Não há servidor backend
- GitHub Pages hospeda apenas código estático

### Controle de Acesso

**Desktop (.exe):**
- Acesso a impressoras via drivers do sistema (Windows)
- Acesso a arquivos do usuário (onde quer que clique)
- **Recomendação:** Rode com permissões mínimas necessárias

**Python CLI:**
- Acesso via `winspool.drv` (Windows) ou CUPS (Linux/macOS)
- Acesso a arquivos onde apontado

---

## 📋 Checklist de Segurança para Releases

Antes de cada release v1.0+:

- [ ] Executar análise de segurança estática (`bandit`)
- [ ] Validar não há hardcoded secrets
- [ ] Revisão de segurança manual de mudanças críticas
- [ ] Confirmar testes passam em todos os OS/Python versions
- [ ] Validar mypy e ruff sem erros
- [ ] Testar em impressora real (se possível)
- [ ] Criar release notes mencionando patches de segurança

---

## 🔐 Melhores Práticas para Usuários

Se você usa o ShopeeLabelPrinter:

- ✅ **Mantenha atualizado**: Baixe a versão mais recente
- ✅ **Reporte bugs**: Se encontrar problema, reporte privadamente
- ✅ **Use versão .exe com cuidado**: Rode com user account (não admin)
- ✅ **Verifique checksums**: Valide hash de downloads
- ✅ **Backup de etiquetas**: Mantenha backup dos ZIPs do Shopee
- ✅ **Segura sua impressora**: Acesso via rede deve ter senha

---

## 📚 Referências de Segurança

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [CWE List](https://cwe.mitre.org/) - Common Weaknesses
- [PEP 3143](https://www.python.org/dev/peps/pep-3143/) - Daemon Processes

---

## 📞 Contato

- **Segurança**: bruno@trolo.dev (use subject: `[SECURITY]`)
- **Bugs**: [GitHub Issues](https://github.com/brunotrolo/ShopeeLabelPrinter/issues)
- **Geral**: [GitHub Discussions](https://github.com/brunotrolo/ShopeeLabelPrinter/discussions)

---

**Última atualização**: 2026-08-08  
**Próxima revisão**: 2026-12-08
