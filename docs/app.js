/*
 * Shopee Label Printer — versão web.
 *
 * Tudo roda no navegador: o ZIP é lido na memória da aba e nunca é enviado
 * para nenhum servidor. A etiqueta tem endereço e dados pessoais do
 * destinatário, e esse dado não deve sair do computador de quem vende.
 */
(function () {
  "use strict";

  const ZOOM_LEVELS = [
    { label: "Ajustar à janela", value: "fit" },
    { label: "100% (203 DPI)", value: "1" },
    { label: "75%", value: "0.75" },
    { label: "50%", value: "0.5" },
    { label: "25%", value: "0.25" },
  ];

  // Mesmos níveis da versão desktop. Vale só para o ZPL baixado — ver a nota
  // em applyPrintBoost (zpl.js).
  const BOOST_CHOICES = [
    { label: "Desligado", value: "desligado" },
    { label: "Leve", value: "leve" },
    { label: "Médio", value: "medio" },
    { label: "Forte", value: "forte" },
  ];

  const els = {};
  let labels = [];
  let currentIndex = -1;
  let currentRender = null;

  function $(id) {
    return document.getElementById(id);
  }

  function init() {
    [
      "dropzone", "file-input", "status", "label-list", "label-panel",
      "preview-canvas", "preview-stage", "preview-empty", "preview-meta",
      "zoom", "btn-print", "btn-png", "btn-zpl", "print-area", "print-size",
      "label-count", "boost",
    ].forEach((id) => {
      els[id.replace(/-(\w)/g, (_, c) => c.toUpperCase())] = $(id);
    });

    ZOOM_LEVELS.forEach((level) => {
      const option = document.createElement("option");
      option.value = level.value;
      option.textContent = level.label;
      els.zoom.appendChild(option);
    });

    BOOST_CHOICES.forEach((choice) => {
      const option = document.createElement("option");
      option.value = choice.value;
      option.textContent = choice.label;
      els.boost.appendChild(option);
    });

    els.dropzone.addEventListener("click", () => els.fileInput.click());
    els.dropzone.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        els.fileInput.click();
      }
    });
    els.fileInput.addEventListener("change", (event) => {
      handleFiles(event.target.files);
      els.fileInput.value = ""; // permite reimportar o mesmo arquivo
    });

    ["dragenter", "dragover"].forEach((type) =>
      els.dropzone.addEventListener(type, (event) => {
        event.preventDefault();
        els.dropzone.classList.add("dragover");
      })
    );
    ["dragleave", "drop"].forEach((type) =>
      els.dropzone.addEventListener(type, (event) => {
        event.preventDefault();
        els.dropzone.classList.remove("dragover");
      })
    );
    els.dropzone.addEventListener("drop", (event) => {
      if (event.dataTransfer.files.length) handleFiles(event.dataTransfer.files);
    });

    els.zoom.addEventListener("change", applyZoom);
    els.btnPrint.addEventListener("click", printLabel);
    els.btnPng.addEventListener("click", downloadPng);
    els.btnZpl.addEventListener("click", downloadZpl);

    window.addEventListener("resize", () => {
      if (currentRender && els.zoom.value === "fit") applyZoom();
    });

    setStatus("", "");
  }

  function setStatus(message, kind) {
    els.status.textContent = message;
    els.status.className = "status" + (kind ? " " + kind : "");
  }

  function showEmpty(message) {
    els.previewEmpty.innerHTML = message;
    els.previewEmpty.style.display = "block";
    els.previewCanvas.style.display = "none";
    els.previewMeta.textContent = "";
    setActionsEnabled(false);
  }

  function setActionsEnabled(enabled) {
    els.btnPrint.disabled = !enabled;
    els.btnPng.disabled = !enabled;
    els.btnZpl.disabled = !enabled;
  }

  // -- importação ----------------------------------------------------------
  async function handleFiles(fileList) {
    const files = Array.from(fileList || []);
    if (files.length === 0) return;

    setStatus("Lendo arquivo...", "warn");
    showEmpty('<div class="spinner"></div>Lendo etiquetas...');

    try {
      labels = await window.LabelZip.loadLabelsFromFiles(files);
    } catch (err) {
      labels = [];
      renderList();
      setStatus(err.message || String(err), "err");
      showEmpty("Não foi possível ler o arquivo.");
      return;
    }

    currentIndex = -1;
    currentRender = null;
    renderList();
    setStatus(`${labels.length} etiqueta(s) carregada(s)`, "ok");
    selectLabel(0);
  }

  function renderList() {
    els.labelList.innerHTML = "";
    els.labelCount.textContent = labels.length ? `${labels.length}` : "";

    labels.forEach((label, index) => {
      const item = document.createElement("li");
      item.dataset.index = String(index);

      const num = document.createElement("span");
      num.className = "num";
      num.textContent = index + 1;

      const name = document.createElement("span");
      name.className = "name";
      name.textContent = label.name;
      name.title = label.name;

      item.append(num, name);
      item.addEventListener("click", () => selectLabel(index));
      els.labelList.appendChild(item);
    });
  }

  // -- preview -------------------------------------------------------------
  async function selectLabel(index) {
    if (index < 0 || index >= labels.length) return;
    currentIndex = index;

    [...els.labelList.children].forEach((item, i) =>
      item.classList.toggle("active", i === index)
    );

    showEmpty('<div class="spinner"></div>Gerando preview...');

    try {
      currentRender = await window.ZPL.renderZpl(labels[index].data);
    } catch (err) {
      currentRender = null;
      showEmpty(
        "Não foi possível gerar o preview desta etiqueta.<br><small>" +
          escapeHtml(err.message || String(err)) +
          "</small>"
      );
      // O arquivo continua íntegro: dá para baixar o ZPL e imprimir no desktop.
      els.btnZpl.disabled = false;
      return;
    }

    window.ZPL.drawToCanvas(currentRender, els.previewCanvas);

    els.previewEmpty.style.display = "none";
    els.previewCanvas.style.display = "block";
    setActionsEnabled(true);

    els.previewMeta.textContent =
      `${currentRender.width} × ${currentRender.height} pontos · ` +
      `${currentRender.widthMm.toFixed(0)} × ${currentRender.heightMm.toFixed(0)} mm · ` +
      `${currentRender.dpi} DPI`;

    applyZoom();

    if (!currentRender.hasBitmap) {
      setStatus(
        "Esta etiqueta não traz imagem embutida — o preview é uma aproximação dos comandos ZPL.",
        "warn"
      );
    }
  }

  function applyZoom() {
    if (!currentRender) return;

    const setting = els.zoom.value;
    let scale;

    if (setting === "fit") {
      const stage = els.previewStage;
      const availableW = Math.max(stage.clientWidth - 48, 120);
      const availableH = Math.max(stage.clientHeight - 48, 120);
      scale = Math.min(availableW / currentRender.width, availableH / currentRender.height, 1);
    } else {
      scale = parseFloat(setting);
    }

    els.previewCanvas.style.width = Math.round(currentRender.width * scale) + "px";
    els.previewCanvas.style.height = "auto";
  }

  // -- ações ---------------------------------------------------------------
  function currentLabelName() {
    const name = labels[currentIndex]?.name || "etiqueta";
    return name.replace(/\.(txt|zpl|prn|tspl)$/i, "").replace(/[^\w.\- ]+/g, "_");
  }

  function printLabel() {
    if (!currentRender) return;

    // A página de impressão recebe o tamanho físico exato da etiqueta, para
    // o navegador não reescalar nada.
    const widthMm = currentRender.widthMm.toFixed(1);
    const heightMm = currentRender.heightMm.toFixed(1);
    els.printSize.textContent =
      `@media print { @page { size: ${widthMm}mm ${heightMm}mm; margin: 0; } ` +
      `#print-area img { width: ${widthMm}mm; height: ${heightMm}mm; } }`;

    const image = new Image();
    image.onload = () => {
      els.printArea.innerHTML = "";
      els.printArea.appendChild(image);
      window.print();
    };
    image.src = els.previewCanvas.toDataURL("image/png");
  }

  function downloadPng() {
    if (!currentRender) return;
    els.previewCanvas.toBlob((blob) => {
      saveBlob(blob, currentLabelName() + ".png");
    }, "image/png");
  }

  function downloadZpl() {
    if (currentIndex < 0) return;
    // Com "Desligado" (padrão) saem os bytes originais, sem nenhuma alteração.
    // É este arquivo que vai RAW para a impressora pelo aplicativo desktop.
    const level = els.boost.value;
    const data = window.ZPL.applyPrintBoost(labels[currentIndex].data, level);
    const suffix = level === "desligado" ? "" : `-reforco-${level}`;
    saveBlob(
      new Blob([data], { type: "application/octet-stream" }),
      currentLabelName() + suffix + ".zpl"
    );
  }

  function saveBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  document.addEventListener("DOMContentLoaded", init);
})();
