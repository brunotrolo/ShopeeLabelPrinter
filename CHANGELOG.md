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

## [0.4.1] - 2026-08-08

### Corrigido
- **A separação descartava o que vinha depois do último `^XZ`.** A etiqueta real
  da Shopee termina com uma quebra de linha, e ela era jogada fora: 12337 bytes
  entregues no lugar dos 12338 originais. Não muda o que sai impresso, mas o
  projeto promete entregar os bytes exatamente como vieram — e não estava.
  Agora `"".join(split_labels(conteudo)) == conteudo`, com teste travando isso.

### Adicionado
- **Reforço do ZPL na versão web**, aplicado ao arquivo baixado, com os mesmos
  quatro níveis da versão desktop. Verificado no navegador que os bytes saem
  idênticos aos que o desktop enviaria em cada nível.

  Não afeta a impressão pelo próprio navegador — nesse caminho a impressora
  recebe uma imagem pelo driver do sistema e nenhum comando ZPL chega até ela.
  A página passou a dizer isso e a indicar onde fica o ajuste de densidade nas
  preferências de impressão do Windows.

## [0.4.0] - 2026-08-08

### Corrigido
- **Envio RAW no Windows sem `argtypes`/`restype`**: sem declarar os tipos, o
  ctypes trata ponteiros e handles como inteiros de 32 bits. No Windows 64 bits
  o handle da impressora era truncado, e as chamadas seguintes podiam falhar ou
  escrever em endereço errado. Todas as funções do `winspool` agora têm tipos
  declarados.
- **Falhas de impressão não diziam o motivo**: a `WinDLL` passa a ser aberta com
  `use_last_error=True` e as mensagens trazem o código e o texto de erro do
  Windows. Antes, qualquer problema virava "não foi possível" — sem diagnóstico.
- **Envio parcial passava como sucesso**: gravar menos bytes que o total só
  gerava um aviso no log e o programa dizia que imprimiu. A etiqueta chegaria
  cortada na impressora e o usuário só descobriria olhando o papel. Agora é erro.

### Adicionado
- **Botão "Testar"**: envia uma etiqueta mínima em ZPL e outra em TSPL. Serve
  para o caso "não sai nada e nenhum erro aparece" — a etiqueta da Shopee é ZPL,
  e uma impressora em modo TSPL ignora comandos ZPL caladamente. Ver qual das
  duas sai no papel identifica a linguagem.
- **Reforço de impressão** (`^MD` escurecimento + `^PR` velocidade), em quatro
  níveis, para traço fino sair cheio. Desligado por padrão.

  É a única função do projeto que altera os bytes enviados, e só age quando o
  usuário escolhe. Mesmo assim **não mexe no desenho**: `^MD` e `^PR` controlam
  o calor da cabeça térmica e a velocidade do papel, não o conteúdo — nenhum
  ponto é acrescentado ou movido. Engrossar o bitmap alargaria também as barras
  do código de barras e mudaria a proporção barra/espaço, que é justamente o que
  o leitor mede; por isso se mexe no calor, nunca na geometria.

## [0.3.1] - 2026-08-08

### Corrigido
- **Uma etiqueta da Shopee aparecia como três, sendo duas em branco.**
  Conferido com um ZIP real baixado do painel: a etiqueta não é um bloco ZPL
  só, são três, nesta ordem:

  ```
  ~DGR:DEMO.GRF,124236,102,:Z64:...   baixa a imagem para a impressora
  ^XA ... ^XGR:DEMO.GRF,1,1 ... ^XZ   manda imprimir a imagem baixada
  ^XA ^IDR:DEMO.GRF ^FS ^XZ           apaga a imagem da memória
  ```

  A separação cortava em todo `^XA` e devolvia os três pedaços como etiquetas
  distintas. Só o primeiro tinha imagem; o segundo chamava um gráfico que
  ficara no pedaço anterior e o terceiro só apagava memória — daí os dois
  brancos no preview. Pior: no "Imprimir todas" os três iam para a impressora
  como se fossem etiquetas de verdade.

  Agora cada bloco `^XA...^XZ` que imprime alguma coisa começa uma etiqueta e
  leva junto o `~DG` que veio antes e os blocos de manutenção que vêm depois.
  Corrigido nas duas versões (`parser.py` e `docs/zip.js`).

- **O `.exe` nunca teria sido gerado**: o workflow apontava o PyInstaller para
  `__main__.py`, que usa import relativo e falha quando executado como script
  solto. Novo `run_app.py` como ponto de entrada, com `--paths src`.
- Aviso do preview aparecia cortado ao abrir o programa (`winfo_width()`
  devolve 1 antes do primeiro layout).

### Adicionado
- `workflow_dispatch` no build: dá para gerar o `.exe` pelo botão "Run workflow"
  na aba Actions, sem criar tag e sem usar o terminal
- O `.exe` é anexado como artefato em toda execução, não só quando há tag
- `permissions: contents: write`, necessário para o passo de Release publicar

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
