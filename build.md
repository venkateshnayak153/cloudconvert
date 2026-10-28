# CloudConvert: Build Document

A tiny floating cloud icon that lives on your desktop. Drop a file on it, pick a target format, get the converted file next to the original. Fully offline.

**Approach:** lightweight shell (Tauri) + use whatever converter engine is already installed on the machine (Microsoft Office, else LibreOffice) + small bundled helper for PDF to Word/PowerPoint.

---

## 1. Scope

### Supported formats
DOC, DOCX, PPT, PPTX, PDF. Nothing else.

### Conversion matrix

| From | To | Engine (priority order) | Expected quality |
|---|---|---|---|
| DOC / DOCX | PDF | MS Word, then LibreOffice | Excellent |
| PPT / PPTX | PDF | MS PowerPoint, then LibreOffice | Excellent |
| PDF | DOCX | `pdf2docx` (bundled) | Good for text PDFs, fair for complex layouts |
| PDF | DOC | PDF to DOCX, then DOCX to DOC via Word/LibreOffice | Same as above |
| PDF | PPTX | PyMuPDF/pypdfium2 + `python-pptx` (bundled) | Image mode: exact. Editable mode: layouts may shift |
| PDF | PPT | PDF to PPTX, then PPTX to PPT via PowerPoint/LibreOffice | Same as above |
| DOC to DOCX, DOCX to DOC | | MS Word, then LibreOffice | Very good |
| PPT to PPTX, PPTX to PPT | | MS PowerPoint, then LibreOffice | Very good |

### Out of scope
Excel, images, Markdown, OCR for scanned PDFs, cloud/online conversion, batch folder watching, Apple Pages. These can be added later through the registry (section 5).

### Honest limits
- PDF is a display format. PDF to Word/PowerPoint is never perfect in any tool. The app says so in the UI.
- Scanned (image-only) PDFs produce image-only output, with no editable text, because OCR is out of scope.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────┐
│  UI (Tauri webview): floating cloud, popup, settings │
├──────────────────────────────────────────────────────┤
│  Rust core: window mgmt, tray, drag-drop, autostart, │
│  job queue, spawns helper, relays progress           │
├──────────────────────────────────────────────────────┤
│  Python helper (sidecar, started per job, exits after)│
│   ├─ Detector (extension + file signature)           │
│   ├─ Registry: (source, target) → pipeline           │
│   └─ Engines: Word/PowerPoint │ LibreOffice │ Python │
└──────────────────────────────────────────────────────┘
```

### Why this split
- **Tauri shell:** about 5-15 MB, uses the OS's built-in web view, near-zero idle RAM. Ideal for an always-on icon.
- **Python helper:** all the PDF libraries are Python. It is started only when a file is dropped and exits afterward, so the idle cost is just the cloud.
- **Communication:** the Rust core spawns the helper with arguments and reads newline-delimited JSON from its stdout.

### Helper protocol

Command:
```
converter-helper convert --in "<path>" --to <pdf|docx|doc|pptx|ppt> --out-dir "<dir>" [--pptx-mode image|editable]
converter-helper detect-engines
```

Events on stdout, one JSON object per line:
```json
{"event":"started","job":"a1b2","engine":"libreoffice"}
{"event":"progress","job":"a1b2","percent":40,"stage":"Converting"}
{"event":"done","job":"a1b2","output":"C:/Users/me/Docs/report_converted.pdf"}
{"event":"error","job":"a1b2","code":"PASSWORD_PROTECTED","message":"This file is password protected."}
```

---

## 3. UI Design

### 3.1 The cloud (main widget)

- **Window:** frameless, transparent background, always on top, hidden from the taskbar/Dock and Alt-Tab.
- **Size:** 72 x 72 px at rest (scales with DPI).
- **Look:** a soft, flat cloud shape with a gentle drop shadow. No text at rest.
- **Idle opacity:** about 70%, going to 100% on hover.
- **Drag to move:** hold and drag anywhere on the cloud. Position is remembered across restarts. Snaps to the nearest screen edge if released within 24 px.
- **Multi-monitor/DPI:** position is stored per monitor and clamped on-screen if a monitor is unplugged.

#### Cloud states

| State | Appearance |
|---|---|
| Idle | Light blue-grey cloud, 70% opacity |
| Hover | Full opacity, slight lift, tooltip "Drop a file or click" |
| Drag-over | Cloud grows about 15%, blue glow, tiny "+" in the center |
| Invalid file dragged | Cloud shakes, turns amber, tooltip "Unsupported file" |
| Processing | Cloud pulses, circular progress ring around it |
| Success | Green tick for 1.5 s, then returns to idle |
| Error | Red "!" for 3 s, click to see details |

```
Idle          Drag-over        Processing       Success
  ☁︎             ☁︎ (+)           ☁︎ (◜◝)          ☁︎ (✓)
```

### 3.2 Format picker (appears when a file is dropped)

A small card that opens beside the cloud (on the side with more screen room). It shows the file name and only the formats that are valid for that file.

```
┌──────────────────────────────┐
│ 📄 Quarterly Report.docx     │
│ Convert to:                  │
│                              │
│  [ PDF ]   [ DOC ]           │
│                              │
│ ☐ Remember my choice         │
│ [ Cancel ]                   │
└──────────────────────────────┘
```

For a PDF it shows `[ DOCX ] [ DOC ] [ PPTX ] [ PPT ]`. Choosing PPTX/PPT shows a one-line sub-choice:

```
 Slides as:  (•) Images (exact look)   ( ) Editable (layout may shift)
```

- Pressing a format starts the job immediately.
- `Esc` or clicking outside closes the card.
- Dropping several files shows one card with a combined list and applies the same target format to all valid files.

### 3.3 Progress and result toast

A small toast attached to the cloud, not a full window:

```
┌───────────────────────────────────┐
│ Converting Quarterly Report…  40% │
│ ▓▓▓▓▓▓░░░░░░░░░░         [Cancel] │
└───────────────────────────────────┘
```

On success:

```
┌───────────────────────────────────────────┐
│ ✓ Quarterly Report_converted.pdf          │
│ [ Open ]  [ Show in folder ]  [ Copy path ]│
└───────────────────────────────────────────┘
```

On error: a plain-language message plus a `[ Details ]` link that shows the log excerpt.

### 3.4 Right-click / tray menu (same menu in both places)

```
Open file…          (opens the system file picker)
Recent conversions ▸ (last 10)
─────────────────
Settings…
Pause (hide cloud)
─────────────────
About
Quit
```

Left-clicking the cloud (without dragging) opens the file picker.

### 3.5 Settings window

One small window with four sections:

| Section | Options |
|---|---|
| **General** | Launch at login (on/off); Show cloud on all desktops; Idle opacity slider; Cloud size (S/M/L); Theme (system/light/dark) |
| **Output** | Save next to original (default) or a fixed folder; Filename suffix (default `_converted`); Open file after conversion (on/off) |
| **Engines** | Detected engines with status (Word ✓/✗, PowerPoint ✓/✗, LibreOffice ✓/✗); Preferred engine (Auto/Office/LibreOffice); "Install LibreOffice" link if none found |
| **PDF to PowerPoint** | Default mode: Images / Editable |

### 3.6 First-run screen

1. Short welcome: "Drop a file on the cloud to convert it."
2. Engine check, with green ticks, or a clear "Install LibreOffice (free)" button if no Office engine is found. PDF to Word/PowerPoint still works without one.
3. Ask whether to launch at login.

### 3.7 Accessibility and polish

- Full keyboard path: tray menu, then "Open file…", then format picker with Tab/Enter.
- Respects the OS reduced-motion setting (no pulse or shake).
- High-contrast friendly state icons (shape plus color, never color alone).
- Light/dark theme for the picker, toast and settings.

---

## 4. Functional Requirements

### 4.1 Core
1. Accept files by drag and drop onto the cloud or via the file picker.
2. Detect the real type from the file signature, not only the extension. Reject mismatches with a clear message.
3. Offer only valid target formats.
4. Convert in the background. The UI never blocks.
5. Save the output next to the source as `<name>_converted.<ext>`. If it exists, use `_converted_2`, `_converted_3`, and so on. Never overwrite.
6. Notify on completion with Open / Show in folder.
7. Cancel a running job and clean up its temp files.

### 4.2 Engine detection (run at startup and when Settings opens)
- **Windows:** check the registry/COM for `Word.Application` and `PowerPoint.Application`; then look for `soffice.exe` in Program Files and on PATH.
- **macOS:** check `/Applications/Microsoft Word.app`, `Microsoft PowerPoint.app`, then `/Applications/LibreOffice.app/Contents/MacOS/soffice`.
- **Linux:** `which soffice` / `libreoffice`.
- Choose the best available per conversion; allow the user to override in Settings.

### 4.3 Engine invocation details
- **Word/PowerPoint on Windows:** COM automation via `pywin32`, run hidden, with macros disabled (`AutomationSecurity = msoAutomationSecurityForceDisable`) and a hard timeout.
- **Word/PowerPoint on macOS:** AppleScript via `osascript`. This is more fragile, so LibreOffice is preferred on Mac by default (configurable).
- **LibreOffice:** `soffice --headless --norestore --convert-to <fmt> --outdir <tmp> <file>` with an isolated profile (`-env:UserInstallation=file:///<tmp-profile>`) so it never clashes with the user's open LibreOffice.
- **PDF to DOCX:** `pdf2docx` `Converter(...).convert(...)`.
- **PDF to PPTX, image mode:** render each page to an image at 150-200 DPI, create a `python-pptx` slide sized to the page aspect ratio, place the image full-bleed.
- **PDF to PPTX, editable mode:** extract text blocks (with font, size, position) and embedded images per page, then place them as text boxes and pictures.

### 4.4 Error handling

| Code | Cause | User message |
|---|---|---|
| `NO_ENGINE` | Needed engine missing | "Install LibreOffice (free) to convert this file type." |
| `PASSWORD_PROTECTED` | Encrypted file | "This file is password protected." |
| `CORRUPT_FILE` | Cannot be parsed | "This file looks damaged and could not be opened." |
| `UNSUPPORTED_TYPE` | Signature mismatch or unknown | "That file type isn't supported." |
| `TIMEOUT` | Job exceeded limit (default 5 min) | "The conversion took too long and was stopped." |
| `DISK_FULL` / `PERMISSION` | Output not writable | "Couldn't save next to the original. Choose another folder." |
| `ENGINE_CRASH` | Engine exited abnormally | "The converter stopped unexpectedly. Try again." |

On any error, fall back to the next engine in the priority list before showing the error.

### 4.5 Security and privacy
- Everything runs locally. There is no network code in the app, and no telemetry.
- Conversions run in a temp directory that is deleted afterward; only the final file is moved to the output folder.
- Macros are never executed.
- Input paths are passed to the helper as arguments, never through a shell string, to prevent command injection.
- Hard limits: file size cap (default 200 MB, configurable) and timeout.

### 4.6 Logging
Rotating local log file (last 5 files, 1 MB each) in the OS app-data folder. No file contents are logged, only names, engines, durations and error codes.

---

## 5. Project Structure

```
cloudconvert/
├─ src-tauri/
│  ├─ src/
│  │  ├─ main.rs            # app setup, window config
│  │  ├─ tray.rs            # tray icon + menu
│  │  ├─ jobs.rs            # queue, spawn helper, parse events
│  │  ├─ settings.rs        # load/save JSON settings
│  │  └─ engines.rs         # calls helper detect-engines
│  ├─ binaries/             # compiled helper per platform (sidecar)
│  ├─ icons/
│  ├─ capabilities/         # Tauri permission files
│  └─ tauri.conf.json
├─ src/                     # web UI (HTML/CSS/TypeScript)
│  ├─ cloud/                # cloud widget + states + animations
│  ├─ picker/               # format picker card
│  ├─ toast/                # progress/result toast
│  ├─ settings/             # settings window
│  └─ assets/               # cloud SVG, state icons
├─ helper/                  # Python sidecar
│  ├─ main.py               # CLI entry (convert, detect-engines)
│  ├─ detector.py           # extension + signature checks
│  ├─ registry.py           # (src, dst) → pipeline of steps
│  ├─ engines/
│  │  ├─ base.py            # Engine interface
│  │  ├─ word_com.py        # Windows COM
│  │  ├─ office_mac.py      # AppleScript
│  │  ├─ libreoffice.py
│  │  ├─ pdf_to_docx.py
│  │  └─ pdf_to_pptx.py
│  ├─ utils/ (paths.py, tempdir.py, events.py)
│  ├─ requirements.txt
│  └─ build_helper.spec     # PyInstaller spec
├─ tests/
│  ├─ fixtures/             # sample doc, docx, ppt, pptx, pdf (incl. encrypted, corrupt)
│  └─ test_*.py
├─ .github/workflows/build.yml
├─ LICENSE
└─ build.md
```

### Adding a format later
Each conversion is one registry entry, such as `("pdf","docx"): [PdfToDocx]` or `("docx","doc"): [OfficeOrLibre("doc")]`. Chained conversions (PDF to DOC) are lists of steps run in order.

---

## 6. Dependencies

### Build-time tools
| Tool | Version | Purpose |
|---|---|---|
| Rust (stable) | 1.77+ | Tauri core |
| Node.js | 20 LTS+ | Web UI build |
| Tauri CLI | 2.x | Build and bundle |
| Python | 3.11+ | Helper |
| PyInstaller | 6.x | Freeze the helper into one binary |

### Rust crates / Tauri plugins
- `tauri` 2.x with the tray-icon feature and `macos-private-api` (needed for transparent windows on macOS)
- `tauri-plugin-shell` (sidecar launch)
- `tauri-plugin-autostart` (launch at login)
- `tauri-plugin-dialog` (file picker)
- `tauri-plugin-store` (settings)
- `tauri-plugin-notification` (native notifications)
- `tauri-plugin-single-instance` (only one cloud)
- `serde`, `serde_json`

### Frontend
Vanilla TypeScript + Vite (no heavy framework; keeps the UI bundle tiny). CSS animations for the states.

### Python helper
| Package | Purpose | License |
|---|---|---|
| `pdf2docx` | PDF to DOCX | GPL-3.0 |
| `PyMuPDF` | PDF parsing and page rendering | AGPL-3.0 (commercial option) |
| `python-pptx` | Build PPTX | MIT |
| `pywin32` (Windows only) | Word/PowerPoint COM | PSF |
| `pikepdf` or `pypdf` | Detect encryption/corruption cheaply | MPL / BSD |
| `Pillow` | Image handling | HPND |

### Runtime (user's machine, not bundled)
Optional, one of: **Microsoft Word + PowerPoint** or **LibreOffice** (free, about 300 MB). Without either, only PDF to DOCX/PPTX/DOC/PPT-via-pipeline steps that don't need Office work, and the app prompts the user to install LibreOffice.

---

## 7. Size and Resource Budget

| Piece | Approx. size |
|---|---|
| Tauri shell | 5-15 MB |
| Python helper (frozen, includes PyMuPDF etc.) | 50-80 MB |
| **Total installer** | **about 60-95 MB** |
| Idle RAM | about 30-60 MB (webview) |
| Idle CPU | about 0% |

The helper is the largest piece because it bundles Python and the PDF libraries. It is only running during a conversion.

Options to shrink it further later: replace PyMuPDF with `pypdfium2` (BSD/Apache, smaller), and exclude unused modules in the PyInstaller spec.

---

## 8. OS Compatibility

| OS | Status | Notes |
|---|---|---|
| Windows 10 (1809+) / 11 | Full, primary target | Uses WebView2 (preinstalled on Win 11 and updated Win 10; installer bootstraps it otherwise). Best quality with MS Office via COM. |
| macOS 11+ (Intel and Apple Silicon) | Full | Build as a universal binary. Needs a Files-and-Folders permission prompt on first use. Needs code signing and notarization for distribution. Transparent window needs `macOSPrivateApi`. |
| Linux, X11 | Full | Uses WebKitGTK. Needs `libwebkit2gtk-4.1`. LibreOffice is the engine. |
| Linux, Wayland | Reduced | Compositors restrict always-on-top and absolute positioning. The app detects Wayland and falls back to **tray-only mode** (no floating cloud). |

---

## 9. Build and Packaging

1. **Freeze the helper** on each target OS:
   `pyinstaller --onefile --name converter-helper helper/main.py`
   Place the output in `src-tauri/binaries/` using Tauri's target-triple naming, for example `converter-helper-x86_64-pc-windows-msvc.exe`, `converter-helper-aarch64-apple-darwin`, `converter-helper-x86_64-unknown-linux-gnu`.
2. **Build the app:** `npm install && npm run tauri build`.
3. **Outputs:** Windows `.msi`/`.exe`; macOS `.dmg`; Linux `.AppImage` and `.deb`.
4. **CI:** GitHub Actions matrix over Windows, macOS and Ubuntu, because the helper must be frozen on each OS.
5. **Signing:** Windows (optional but avoids SmartScreen warnings), macOS (required: Developer ID plus notarization), Linux (none needed).
6. **Updates:** manual download at first. The Tauri updater plugin can be added later.

---

## 10. Build Phases

| Phase | Deliverable | Done when |
|---|---|---|
| 1 | Floating cloud: transparent, draggable, remembers position, all visual states with mock data, tray menu, single instance | Cloud can be moved and its states previewed |
| 2 | Drag-drop and file picker, type detection, format picker card | Dropping a file shows the correct target formats |
| 3 | Helper skeleton plus engine detection plus Office/LibreOffice to PDF | DOC/DOCX/PPT/PPTX convert to PDF end to end |
| 4 | DOC to DOCX and PPT to PPTX (and reverse) | Round-trip conversions work |
| 5 | PDF to DOCX, then PDF to DOC | Text PDFs convert acceptably |
| 6 | PDF to PPTX (image mode, then editable mode), then PPT | Both modes selectable |
| 7 | Settings, first-run flow, error messages, logging, cancel/timeout | All error codes in section 4.4 reproducible |
| 8 | Autostart, packaging, signing, CI, README | Installers build on all three OSes |

---

## 11. Testing

- **Fixtures:** simple and complex DOCX (tables, images, headers), PPTX with animations and notes, text PDF, scanned PDF, password-protected PDF, corrupt files, a file with the wrong extension, a very large file.
- **Unit tests:** detector, registry routing, output-name collision logic, event parsing.
- **Integration tests:** helper run against every fixture for every valid conversion, asserting the output opens (re-parse with `python-docx`/`python-pptx`/`pypdf`) and has a sensible page/slide count.
- **Manual checklist per OS:** drag, snap, restart position, multi-monitor, drag-over states, cancel mid-job, no engine installed, Office open at the same time, launch at login.
- **Performance targets:** cloud idle under 60 MB RAM; 10-page DOCX to PDF under 10 s on LibreOffice.

---

## 12. Licensing Notes

- `PyMuPDF` is AGPL and `pdf2docx` is GPL-3.0. **Personal use is fine.** If you distribute the app, the whole app would have to be released under a compatible open-source license, or you would need a commercial PyMuPDF license and a replacement for `pdf2docx`.
- LibreOffice and Microsoft Office are not bundled, only invoked, so their licenses don't pass to your app.
- Decide before distributing publicly. Choosing an open-source license (GPL-3.0/AGPL) for the project is the simplest path.

---

## 13. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| PDF to PPTX/DOCX fidelity complaints | Set expectations in the UI; offer image mode; explain in the first-run screen |
| Office COM hangs or leaves a zombie process | Hard timeout, kill the process tree, always release the COM object |
| LibreOffice profile lock when the user has it open | Isolated per-job profile directory |
| Transparent window glitches on some GPUs/Linux compositors | A setting to switch to an opaque rounded icon; tray-only fallback |
| macOS permission prompts confuse users | First-run explanation before triggering the prompt |
| Helper binary flagged by antivirus (PyInstaller false positives) | Code sign; consider Nuitka or a folder-mode build |
| Large helper size | Swap PyMuPDF for pypdfium2; trim PyInstaller excludes |

---

## 14. Future Ideas (not in scope now)
Excel and image support, batch and folder watching, OCR for scanned PDFs, global hotkey to open the picker, right-click "Convert with CloudConvert" shell integration, auto-update.

---

## 15. Open Decisions (set before phase 1)

1. Personal use or distribution? This decides licensing in section 12.
2. Primary OS to test on first (Windows is recommended).
3. Is Microsoft Office installed on your main machine? If yes, Office is the preferred engine there.
4. Default PDF to PPTX mode: Images (recommended) or Editable.
