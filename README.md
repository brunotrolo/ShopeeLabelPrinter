# 🖨️ Shopee Label Print

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%2B-0078d4)
[![GitHub release](https://img.shields.io/github/release/brunotrolo/shopee-label-print.svg)](https://github.com/brunotrolo/shopee-label-print/releases)

**Print Shopee shipping labels directly on your thermal printer with zero quality loss.**

A lightweight, zero-dependency tool to import Shopee label ZIPs, decode ZPL/TSPL graphics in real-time, display a pixel-perfect preview at 203 DPI, and send **raw bytes** (RAW mode) to compatible thermal label printers — preserving 100% original resolution with no PDF conversion or resampling.

**Available as:** Professional desktop application (.exe), responsive web app, or Python library.

## ⚡ Quick Start

### 🌐 Web Version (No Installation)
Open **[brunotrolo.github.io/Shopee_Printer](https://brunotrolo.github.io/shopee-label-print/)**, drag your Shopee ZIP file, and preview instantly. Works in modern browsers: Chrome 80+, Edge 80+, Firefox 113+, Safari 16.4+.

### 💻 Desktop Version (.exe)
1. Download latest `ShopeeLabelPrinter.exe` from [Releases](https://github.com/brunotrolo/shopee-label-print/releases)
2. Run the executable (no installation required)
3. Works on any Windows 10/11 — Python not required

### 🐍 Python Version
```bash
python -m shopee_label_printer
```
Requires Python 3.10+ with `pip install` (zero external dependencies)

---

## 🎯 What It Does

✅ **Import** Shopee ZIP files, folders, or individual TXT/ZPL/PRN/TSPL files  
✅ **Auto-separate** multiple concatenated labels in a single file  
✅ **Preview** each label at native 203 DPI before printing  
✅ **Send RAW** to thermal printers with zero quality loss (desktop only)  
✅ **100% Local** — your recipient addresses never leave your computer  
✅ **Zero Dependencies** — uses only Python standard library (no `pip install` needed)  
✅ **Cross-Platform Web** — run on Windows, Mac, Linux, or mobile browsers  

---

## 📊 Feature Comparison

| Feature | 💻 Desktop (.exe) | 🌐 Web | 🐍 Python CLI |
|---------|:---:|:---:|:---:|
| Import Shopee ZIP | ✅ | ✅ | ✅ |
| Auto-separate labels | ✅ | ✅ | ✅ |
| 203 DPI preview | ✅ | ✅ | ✅ |
| **RAW send (max quality)** | ✅ | ❌ | ✅ |
| Print via system driver | — | ✅ | ❌ |
| Batch print multiple labels | ✅ | ❌ | ✅ |
| Export PNG/PDF | — | ✅ | ❌ |
| No installation needed | — | ✅ | — |
| Works on Mac/Linux | ❌ | ✅ | ✅ |
| Data stays on device | ✅ | ✅ | ✅ |
| Customizable heat/speed | ✅ | ✅ | ✅ |

**Both desktop and web use the same decoding algorithm**, so previews are identical. The difference is how each connects to the printer.

> **Why doesn't the web version use RAW mode?**  
> Browser sandboxing prevents direct access to printer hardware. The web version prints through your OS driver at the exact physical size (100 × 150 mm). For byte-perfect output on thermal printers, use the desktop version.

**Recommended workflow:** Preview labels in the browser on any device, then print via desktop for maximum quality.

---

## 🖥️ System Requirements

### Windows Desktop / .exe
- **Windows 10/11** (64-bit)
- Thermal printer with **TSPL/ZPL support** (e.g., Godex/ZebraLink FY-1075 at 203 DPI)
- USB or network connection to printer

### Web Version
- Modern browser (Chrome 80+, Edge 80+, Firefox 113+, Safari 16.4+)
- No software installation required
- Works on Windows, Mac, Linux, iOS, Android

### Python Version
- Python 3.10 or later
- Windows 10/11 (printer connectivity via `winspool.drv`)
- macOS/Linux support available (uses CUPS, not fully tested)

---

## 🚀 How to Use

### Desktop / .exe
1. **Import**: Click "Import ZIP / Folder / TXT" and select a Shopee file
2. **Preview**: View the label list and individual label previews at 203 DPI
3. **Select printer**: Choose your thermal printer from the dropdown
4. **Print**: Click "Print All" or select specific labels and click "Print Selected"
5. **Monitor**: Watch the log for any errors or warnings

### Web Version
1. Open https://brunotrolo.github.io/shopee-label-print/
2. Drag your ZIP file into the drop zone (or click to select)
3. Choose print mode: **ZPL** (raw native), **TSPL** (FY-1075 compatible), or **PDF**
4. Adjust output boost if needed (Leve/Médio/Forte/Customizado)
5. Download or print via browser

### Python CLI
```bash
python -m shopee_label_printer [--zip-path PATH] [--print-all] [--printer-name NAME]
```

---

## 🔍 How the Preview Works

Shopee labels include embedded graphics via `~DG` / `^GFA` commands. The preview:

- **Decodes the bitmap** from ZPL hexadecimal (raw, ASCII-compressed, Base64)
- **Renders 1:1** at 203 DPI (812 × 1218 pixels = 100 × 150 mm)
- **Scales for display** using area averaging (preserves 1-pixel barcode details)
- **Draws vector elements** (Code 128 barcodes, lines, text) on top

The preview **never modifies** the bytes sent to the printer — it's read-only. The printer receives the original file byte-for-byte.

---

## 📁 Project Structure

```
Shopee-Label-Print/
├── src/shopee_label_printer/
│   ├── __init__.py              # Package metadata
│   ├── __main__.py              # Entry point (python -m)
│   ├── app.py                   # GUI (tkinter) + preview
│   ├── parser.py                # ZIP extraction + label separation
│   ├── printer.py               # RAW send + printer list
│   ├── renderer.py              # ZPL → image decoding
│   ├── converters.py            # ZPL → TSPL/PDF conversion
│   ├── config.py                # Persistent settings
│   ├── logger.py                # File + console logging
│   ├── utils.py                 # Printer ordering, formatting
│   └── validators.py            # Label validation
├── tests/                       # 125+ automated tests
├── docs/                        # Web app (GitHub Pages)
│   ├── index.html
│   ├── app.js                   # Frontend logic
│   ├── zpl.js                   # ZPL decoder (JavaScript port)
│   ├── converters.js            # Format conversion
│   └── style.css
├── README.md                    # This file
├── LEIA-ME.md                   # Portuguese guide
├── PLANO_DESENVOLVIMENTO.md     # Technical roadmap (5 phases)
├── CHANGELOG.md                 # Version history
├── LICENSE                      # MIT License
└── ShopeeLabelPrinter.spec      # PyInstaller config
```

---

## 🔧 Development & Building

### Run Tests
```bash
pip install pytest
pytest tests/
```

### Build Desktop .exe
**Option 1: Automatic (via GitHub Actions)**
1. Go to [Actions](https://github.com/brunotrolo/shopee-label-print/actions)
2. Select "Build Executável" → Run workflow
3. Download the `.exe` from the completed run

**Option 2: Manual with PyInstaller**
```bash
pip install pyinstaller
pyinstaller ShopeeLabelPrinter.spec --onefile --windowed
# Output: dist/ShopeeLabelPrinter.exe
```

### Local Web Development
```bash
cd docs
python -m http.server 8000
# Open http://localhost:8000
```

**Important:** `docs/zpl.js` must mirror `src/shopee_label_printer/renderer.py` — changes to one must be ported to the other.

---

## 📊 Roadmap

See [PLANO_DESENVOLVIMENTO.md](PLANO_DESENVOLVIMENTO.md) for detailed 5-phase plan:

1. ✅ **Phase 0**: Project foundation (structure, modules)
2. ⏳ **Phase 1**: Stability — error handling, logging (pending FY-1075 hardware test)
3. ✅ **Phase 2**: Professional packaging (CI/CD, GitHub Actions, Releases)
4. ✅ **Phase 3**: Robust parsing (edge cases, graphic decoding)
5. ✅ **Phase 4–5**: UX, preview, web version on GitHub Pages

---

## ⚠️ Known Limitations

- **Hardware test pending** — logic and decoding validated with 125+ tests, but real FY-1075 printing not yet verified (blocker for v1.0.0)
- **Web version doesn't send RAW** — browser sandbox restriction; prints via OS driver instead
- **QR codes** (`^BQ`) render as a marker in preview (rarely occurs; Shopee usually embeds QR in the bitmap)
- **Macros and barcode overlays** not supported (etiquetas with vector elements outside the embedded bitmap are rejected)
- **All boost levels currently produce identical results** — this is a known limitation being addressed separately; custom boost controls are included for future flexibility

---

## 🐛 Troubleshooting

### Empty printer list?
- Printer must be installed and connected before opening the app
- Check **Control Panel > Devices and Printers**
- Try restarting the application

### Labels look faint or dark?
- Desktop: Adjust **Boost Level** (Leve/Médio/Forte/Customizado) before printing
- Web: Use **Modo de Saída** dropdown + Boost settings (TSPL/ZPL)
- Note: Boost controls are included for future use; current FY-1075 printer produces identical output regardless of boost level

### Preview shows nothing?
- Ensure the Shopee ZIP contains valid ZPL/TSPL files
- Check that the file isn't corrupted
- Try exporting as PNG first to isolate the issue

### Can't print from web version?
- Use the desktop version for RAW mode printing
- Web version works best for preview and export (PNG, PDF)

---

## 📈 SEO Keywords

*Shopee label printer | thermal label printer | ZPL to TSPL converter | shipping label software | Godex printer tool | FY-1075 label software | Brazilian shipping labels | etiqueta Shopee | impressora térmica | conversor ZPL | print Shopee labels | label thermal printer | ZPL TSPL conversion*

---

## 🤝 Contributing

This is an active project. Contributions welcome:
- Bug reports and fixes
- Hardware testing (especially FY-1075)
- Documentation improvements
- Feature suggestions

Open an issue or pull request on [GitHub](https://github.com/brunotrolo/shopee-label-print).

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 📞 Contact & Support

**Bruno Trolo** — [@brunotrolo](https://github.com/brunotrolo)

Questions? Read:
- [LEIA-ME.md](LEIA-ME.md) — Portuguese user guide
- [PLANO_DESENVOLVIMENTO.md](PLANO_DESENVOLVIMENTO.md) — Technical details
- [CHANGELOG.md](CHANGELOG.md) — Version history

---

**Last updated:** August 2026  
**Version:** v0.3.1+ (pending FY-1075 hardware test)
