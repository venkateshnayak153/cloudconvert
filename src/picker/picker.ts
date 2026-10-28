/**
 * Format Picker Component
 */
export interface PickerSelection {
  format: string;
  pptxMode: "image" | "editable";
  remember: boolean;
}

export class FormatPicker {
  private element: HTMLElement;
  private filenameEl: HTMLElement;
  private formatsEl: HTMLElement;
  private pptxOptionsEl: HTMLElement;
  private rememberEl: HTMLInputElement;
  private closeBtn: HTMLElement;
  private cancelBtn: HTMLElement;
  private onSelectCallback: ((selection: PickerSelection) => void) | null = null;
  private onCancelCallback: (() => void) | null = null;

  constructor() {
    this.element = document.getElementById("format-picker") as HTMLElement;
    this.filenameEl = document.getElementById("picker-filename") as HTMLElement;
    this.formatsEl = document.getElementById("picker-formats") as HTMLElement;
    this.pptxOptionsEl = document.getElementById("picker-pptx-options") as HTMLElement;
    this.rememberEl = document.getElementById("picker-remember") as HTMLInputElement;
    this.closeBtn = document.getElementById("picker-close-btn") as HTMLElement;
    this.cancelBtn = document.getElementById("picker-cancel-btn") as HTMLElement;

    this.closeBtn.addEventListener("click", () => this.hide());
    this.cancelBtn.addEventListener("click", () => this.hide());

    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !this.element.classList.contains("hidden")) {
        this.hide();
      }
    });
  }

  public show(
    filename: string,
    validFormats: string[],
    onSelect: (selection: PickerSelection) => void,
    onCancel?: () => void
  ) {
    this.filenameEl.textContent = filename;
    this.onSelectCallback = onSelect;
    this.onCancelCallback = onCancel || null;
    this.formatsEl.innerHTML = "";

    const hasPptx = validFormats.includes("pptx") || validFormats.includes("ppt");
    if (hasPptx) {
      this.pptxOptionsEl.classList.remove("hidden");
    } else {
      this.pptxOptionsEl.classList.add("hidden");
    }

    validFormats.forEach((fmt) => {
      const btn = document.createElement("button");
      btn.className = "format-btn";
      btn.textContent = fmt.toUpperCase();
      btn.addEventListener("click", () => {
        const modeEl = document.querySelector('input[name="pptx-mode"]:checked') as HTMLInputElement;
        const pptxMode = (modeEl?.value as "image" | "editable") || "image";
        const remember = this.rememberEl.checked;
        this.element.classList.add("hidden");
        if (this.onSelectCallback) {
          this.onSelectCallback({ format: fmt, pptxMode, remember });
        }
      });
      this.formatsEl.appendChild(btn);
    });

    this.element.classList.remove("hidden");
  }

  public hide() {
    this.element.classList.add("hidden");
    if (this.onCancelCallback) {
      this.onCancelCallback();
    }
  }

  public isVisible(): boolean {
    return !this.element.classList.contains("hidden");
  }
}
