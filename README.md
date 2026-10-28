# ☁️ CloudConvert

A tiny, offline floating desktop cloud file converter built with **Tauri 2.x**, **TypeScript + Vite**, and a **Python helper engine**.

Drop a file onto the cloud, pick your target format, and get the converted file saved right next to the original without ever overwriting.

---

## 🎯 Supported Formats

- **Documents**: `DOC`, `DOCX`, `PDF`
- **Presentations**: `PPT`, `PPTX`, `PDF`

### Conversion Matrix & Engines

| From | To | Engine Strategy |
|---|---|---|
| DOC / DOCX | PDF | Microsoft Word, fallback to LibreOffice |
| PPT / PPTX | PDF | Microsoft PowerPoint, fallback to LibreOffice |
| PDF | DOCX | Bundled Python `pdf2docx` |
| PDF | DOC | `pdf2docx` to DOCX, then Office/LibreOffice to DOC |
| PDF | PPTX | Bundled PyMuPDF + `python-pptx` (Images or Editable mode) |
| PDF | PPT | PDF to PPTX, then Office/LibreOffice to PPT |
| DOC ↔ DOCX | | Microsoft Word, fallback to LibreOffice |
| PPT ↔ PPTX | | Microsoft PowerPoint, fallback to LibreOffice |

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────┐
│  UI (Tauri webview): floating cloud, popover, settings │
├────────────────────────────────────────────────────────┤
│  Rust core: frameless transparent window, edge-snap,   │
│  tray menu, drag-drop, job queue, IPC relay            │
├────────────────────────────────────────────────────────┤
│  Python helper: per-conversion sidecar process         │
│   ├─ Signature detector (magic bytes, encryption check)│
│   ├─ Conversion pipeline registry with auto-fallback   │
│   └─ Standard NDJSON stdout protocol                   │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### 1. Test Python Helper & Run Unit Tests
```bash
# Run all unit tests and integration tests
python3 -m unittest discover -s tests -v

# Run engine detection CLI
python3 helper/main.py detect-engines

# Run file signature detection
python3 helper/main.py detect-file --in tests/fixtures/sample.pdf
```

### 2. Frontend Development & Preview
```bash
# Install web dependencies
npm install

# Start Vite dev server for UI preview
npm run dev

# Build production web bundle
npm run build
```

### 3. Tauri Desktop App
```bash
# Run Tauri desktop app
npm run tauri dev

# Build release package (.dmg / .msi / .deb)
npm run tauri build
```

---

## 🌟 Key Features

1. **Floating Cloud Window**:
   - 72x72 px at rest, frameless, transparent background.
   - Always-on-top, hidden from Dock / Taskbar.
   - Screen edge snapping within 24 px.
   - Remembers position across restarts.
2. **Visual States**:
   - `Idle`: 70% opacity, gentle shadow.
   - `Hover`: 100% opacity, lift, tooltip.
   - `Drag-over`: 1.15x scale, soft blue glow, `+` center badge.
   - `Invalid Drag`: Amber shake animation, "Unsupported file" tooltip.
   - `Processing`: Pulsing animation with circular SVG progress ring.
   - `Success`: Green checkmark badge (1.5s).
   - `Error`: Red exclamation badge with clickable details.
3. **Format Picker Card**:
   - Pops up beside the cloud on file drop or selection.
   - Displays only formats valid for the source file.
   - Supports Presentation mode selection: **Images (exact look)** vs **Editable**.
4. **Safety & Privacy**:
   - 100% offline. Zero network calls or tracking.
   - Collision-safe output: never overwrites existing files (`_converted`, `_converted_2`, ...).
   - Atomic temporary workspaces cleaned up after conversion.
