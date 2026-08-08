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
    { label: "Leve — traço mais firme", value: "leve" },
    { label: "Médio — traço bem escuro", value: "medio" },
    { label: "Forte — pode borrar o código", value: "forte" },
    { label: "Customizado", value: "customizado" },
    { label: "Desligado (bytes originais)", value: "desligado" },
  ];

  // Modos de saída — igual ao desktop
  const MODE_CHOICES = [
    { label: "ZPL (Zebra nativo)", value: "zpl" },
    { label: "TSPL (FY-1075, compatível)", value: "tspl" },
    { label: "PDF (arquivo)", value: "pdf" },
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
      "zoom", "btn-print", "btn-png", "btn-download", "print-area", "print-size",
      "label-count", "boost", "mode",
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

    MODE_CHOICES.forEach((choice) => {
      const option = document.createElement("option");
      option.value = choice.value;
      option.textContent = choice.label;
      els.mode.appendChild(option);
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
    els.btnDownload.addEventListener("click", downloadInSelectedMode);
    els.mode.addEventListener("change", updateDownloadButtonLabel);
    els.boost.addEventListener("change", updateCustomBoostUI);
    els.boost.value = "leve";
    els.mode.value = "tspl";
    updateDownloadButtonLabel();
    updateCustomBoostUI();

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
    els.btnDownload.disabled = !enabled;
  }

  function updateDownloadButtonLabel() {
    const labels = { zpl: "📄 Baixar ZPL", tspl: "📄 Baixar TSPL", pdf: "📄 Baixar PDF" };
    els.btnDownload.textContent = labels[els.mode.value] || labels.zpl;
  }

  function updateCustomBoostUI() {
    let customUI = document.getElementById("custom-boost-ui");
    if (els.boost.value === "customizado") {
      if (!customUI) {
        customUI = document.createElement("div");
        customUI.id = "custom-boost-ui";
        customUI.style.marginTop = "8px";
        customUI.style.padding = "8px";
        customUI.style.backgroundColor = "#f8f9fa";
        customUI.style.borderRadius = "4px";
        customUI.style.fontSize = "12px";
        customUI.innerHTML = `
          <div style="margin-bottom: 8px; font-weight: bold;">⚙️ Ajuste Personalizado</div>
          <div style="margin-bottom: 6px;">
            DENSITY (0-15):
            <input type="range" id="custom-density" min="0" max="15" value="12" style="width: 120px; vertical-align: middle;">
            <span id="density-value" style="margin-left: 8px;">12</span>
          </div>
          <div style="margin-bottom: 6px;">
            SPEED (pol/s):
            <input type="range" id="custom-speed" min="1" max="4" value="2" style="width: 120px; vertical-align: middle;">
            <span id="speed-value" style="margin-left: 8px;">2</span>
          </div>
          <div style="font-size: 11px; color: #666; margin-top: 8px; line-height: 1.4;">
            <strong>DENSITY:</strong> Aumentar = mais escuro | Diminuir = mais claro<br>
            <strong>SPEED:</strong> Aumentar = mais rápido (menos escuro) | Diminuir = mais lento (mais escuro)
          </div>
        `;
        els.boost.parentElement.parentElement.insertBefore(customUI, els.boost.parentElement.nextSibling);

        document.getElementById("custom-density").addEventListener("input", (e) => {
          document.getElementById("density-value").textContent = e.target.value;
        });
        document.getElementById("custom-speed").addEventListener("input", (e) => {
          document.getElementById("speed-value").textContent = e.target.value;
        });
      }
    } else if (customUI) {
      customUI.remove();
    }
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
      // O arquivo continua íntegro: dá para baixar o ZPL (não TSPL/PDF, que
      // dependem do preview) e imprimir no desktop.
      els.btnDownload.disabled = els.mode.value !== "zpl";
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

  async function downloadTspl() {
    const level = els.boost.value;
    let data;
    let suffix = level === "desligado" ? "" : `-reforco-${level}`;

    if (level === "customizado") {
      const density = parseInt(document.getElementById("custom-density").value);
      const speed = parseInt(document.getElementById("custom-speed").value);
      data = await window.LabelConverters.zplToTspl(
        currentRender,
        level,
        density,
        speed
      );
      suffix = `-custom-d${density}-s${speed}`;
    } else {
      data = await window.LabelConverters.zplToTspl(currentRender, level);
    }

    saveBlob(
      new Blob([data], { type: "application/octet-stream" }),
      currentLabelName() + suffix + ".tspl"
    );
  }

  async function downloadPdf() {
    const data = await window.LabelConverters.zplToPdf(currentRender);
    saveBlob(new Blob([data], { type: "application/pdf" }), currentLabelName() + ".pdf");
  }

  async function downloadInSelectedMode() {
    if (currentIndex < 0) return;
    const mode = els.mode.value;

    try {
      if (mode === "tspl") {
        if (!currentRender) throw new Error("Sem preview, não é possível converter para TSPL.");
        await downloadTspl();
      } else if (mode === "pdf") {
        if (!currentRender) throw new Error("Sem preview, não é possível gerar o PDF.");
        await downloadPdf();
      } else {
        downloadZpl();
      }
    } catch (err) {
      const message = err.message || String(err);
      setStatus(message, "err");
      alert(message);
    }
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
