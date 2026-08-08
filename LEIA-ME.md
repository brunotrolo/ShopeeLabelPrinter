# Shopee Label Printer

Programa com interface gráfica: você importa o ZIP (ou TXT) que a Shopee
fornece, e ele manda cada etiqueta **em modo bruto (RAW)** direto pra sua
impressora térmica FY-1075 — sem converter pra PDF, sem reamostrar nada,
sem perder resolução.

Esta versão **não depende de nenhuma biblioteca externa** (nada de
`pip install`). Usa só recursos que já vêm dentro do Python e do Windows.

---

## Opção A — Rodar direto (mais simples de começar)

1. Instale o Python: https://www.python.org/downloads/
   - Na instalação, marque **"Add Python to PATH"**.
2. Dê duplo clique em `shopee_print_app.py`.

Pronto — não precisa instalar mais nada além do Python em si.

---

## Opção B — Gerar um `.exe` que roda sem Python (recomendado)

Se você quer nunca mais depender de ter Python instalado — inclusive pra
usar em outro PC — faça isso **uma única vez**:

1. Instale o Python normalmente (só dessa vez, pra gerar o `.exe`).
2. Abra o Prompt de Comando na pasta onde está o `shopee_print_app.py` e rode:
   ```
   pip install pyinstaller
   pyinstaller --onefile --windowed --name "ShopeeLabelPrinter" shopee_print_app.py
   ```
3. Isso vai criar uma pasta `dist` com o arquivo `ShopeeLabelPrinter.exe`.
4. Esse `.exe` já é standalone — você pode copiar ele pra área de trabalho,
   pra um pendrive, ou pra qualquer outro PC Windows, e ele funciona sem
   precisar instalar Python lá. É só dar duplo clique.

*Observação: o `.exe` gerado funciona no Windows que você usou pra gerá-lo
e em outros Windows de mesma arquitetura (64 bits, que é o padrão hoje em
dia). Não tentei gerar esse `.exe` por aqui porque preciso rodar esse passo
dentro de um Windows de verdade para o resultado ser confiável — mas o
comando acima é padrão e funciona bem para esse tipo de programa.*

---

## Como usar (as duas opções)

1. Abra o programa (`.py` ou `.exe`).
2. Clique em **"Importar ZIP / Pasta / TXT"** e selecione o arquivo da Shopee.
3. Confira a lista de etiquetas encontradas.
4. Escolha a impressora FY-1075 no menu suspenso.
5. Clique em **"Imprimir todas"** (ou selecione algumas e clique em
   "Imprimir selecionadas").
6. Acompanhe o log — ele avisa se alguma etiqueta falhou.

## O que o programa faz por trás dos panos

- Se você importar um `.zip`, extrai tudo numa pasta temporária.
- Procura arquivos `.txt`, `.zpl`, `.prn` ou `.tspl`.
- Se um único arquivo tiver mais de uma etiqueta colada (vários blocos
  `~DG`/`^XA`), separa automaticamente em etiquetas individuais.
- Envia cada etiqueta como bytes crus pro spooler de impressão do Windows,
  em modo `RAW`, usando chamadas nativas do sistema (`winspool.drv`) — o
  mesmo conteúdo, byte a byte, que estava no arquivo original da Shopee.

## Se a lista de impressoras vier vazia

Confirme que a FY-1075 está instalada e ligada — ela precisa aparecer em
Painel de Controle > Dispositivos e Impressoras antes de abrir o app.
