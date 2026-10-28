/**
 * Settings Modal Controller
 */
export interface AppSettings {
  autostart: boolean;
  opacity: number;
  cloudSize: "s" | "m" | "l";
  theme: "system" | "light" | "dark";
  outputMode: "next_to_original" | "custom";
  customFolder: string;
  suffix: string;
  autoOpen: boolean;
  preferredEngine: "auto" | "office" | "libreoffice";
  defaultPptxMode: "image" | "editable";
}

export class SettingsModal {
  private modal: HTMLElement;
  private closeBtn: HTMLElement;
  private saveBtn: HTMLElement;
  private tabButtons: NodeListOf<HTMLButtonElement>;
  private tabPanes: NodeListOf<HTMLElement>;

  private autostartInput: HTMLInputElement;
  private opacityInput: HTMLInputElement;
  private opacityVal: HTMLElement;
  private sizeSelect: HTMLSelectElement;
  private themeSelect: HTMLSelectElement;
  private outputModeSelect: HTMLSelectElement;
  private customFolderRow: HTMLElement;
  private customFolderInput: HTMLInputElement;
  private suffixInput: HTMLInputElement;
  private autoOpenInput: HTMLInputElement;
  private preferredEngineSelect: HTMLSelectElement;

  private statusWord: HTMLElement;
  private statusPpt: HTMLElement;
  private statusLibre: HTMLElement;
  private btnInstallLibre: HTMLElement;

  private onSettingsChanged: ((settings: AppSettings) => void) | null = null;

  constructor() {
    this.modal = document.getElementById("settings-dialog") as HTMLElement;
    this.closeBtn = document.getElementById("settings-close-btn") as HTMLElement;
    this.saveBtn = document.getElementById("settings-save-btn") as HTMLElement;
    this.tabButtons = document.querySelectorAll(".tab-btn");
    this.tabPanes = document.querySelectorAll(".tab-pane");

    this.autostartInput = document.getElementById("set-autostart") as HTMLInputElement;
    this.opacityInput = document.getElementById("set-opacity") as HTMLInputElement;
    this.opacityVal = document.getElementById("set-opacity-val") as HTMLElement;
    this.sizeSelect = document.getElementById("set-size") as HTMLSelectElement;
    this.themeSelect = document.getElementById("set-theme") as HTMLSelectElement;
    this.outputModeSelect = document.getElementById("set-output-mode") as HTMLSelectElement;
    this.customFolderRow = document.getElementById("custom-folder-row") as HTMLElement;
    this.customFolderInput = document.getElementById("set-custom-folder") as HTMLInputElement;
    this.suffixInput = document.getElementById("set-suffix") as HTMLInputElement;
    this.autoOpenInput = document.getElementById("set-auto-open") as HTMLInputElement;
    this.preferredEngineSelect = document.getElementById("set-preferred-engine") as HTMLSelectElement;

    this.statusWord = document.getElementById("status-word") as HTMLElement;
    this.statusPpt = document.getElementById("status-powerpoint") as HTMLElement;
    this.statusLibre = document.getElementById("status-libreoffice") as HTMLElement;
    this.btnInstallLibre = document.getElementById("btn-install-libreoffice") as HTMLElement;

    this.initEvents();
  }

  private initEvents() {
    this.closeBtn.addEventListener("click", () => this.hide());
    this.saveBtn.addEventListener("click", () => {
      this.save();
      this.hide();
    });

    this.tabButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetTab = btn.getAttribute("data-tab");
        this.tabButtons.forEach((b) => b.classList.remove("active"));
        this.tabPanes.forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById(`tab-${targetTab}`)?.classList.add("active");
      });
    });

    this.opacityInput.addEventListener("input", () => {
      this.opacityVal.textContent = `${this.opacityInput.value}%`;
      document.documentElement.style.setProperty("--cloud-opacity", `${Number(this.opacityInput.value) / 100}`);
    });

    this.outputModeSelect.addEventListener("change", () => {
      if (this.outputModeSelect.value === "custom") {
        this.customFolderRow.classList.remove("hidden");
      } else {
        this.customFolderRow.classList.add("hidden");
      }
    });

    this.sizeSelect.addEventListener("change", () => {
      const sz = this.sizeSelect.value === "s" ? "56px" : this.sizeSelect.value === "l" ? "96px" : "72px";
      document.documentElement.style.setProperty("--cloud-size", sz);
    });
  }

  public show(onChanged?: (settings: AppSettings) => void) {
    this.onSettingsChanged = onChanged || null;
    this.refreshEngineStatus();
    this.modal.classList.remove("hidden");
  }

  public hide() {
    this.modal.classList.add("hidden");
  }

  public updateEnginesDisplay(engines: { word: boolean; powerpoint: boolean; libreoffice: boolean }) {
    this.statusWord.textContent = engines.word ? "✓ Installed" : "✗ Not found";
    this.statusWord.className = `engine-status ${engines.word ? "status-ok" : "status-fail"}`;

    this.statusPpt.textContent = engines.powerpoint ? "✓ Installed" : "✗ Not found";
    this.statusPpt.className = `engine-status ${engines.powerpoint ? "status-ok" : "status-fail"}`;

    this.statusLibre.textContent = engines.libreoffice ? "✓ Installed" : "✗ Not found";
    this.statusLibre.className = `engine-status ${engines.libreoffice ? "status-ok" : "status-fail"}`;

    if (!engines.word && !engines.powerpoint && !engines.libreoffice) {
      this.btnInstallLibre.classList.remove("hidden");
    } else {
      this.btnInstallLibre.classList.add("hidden");
    }
  }

  public async refreshEngineStatus() {
    if ((window as any).__TAURI__) {
      try {
        const engines = await (window as any).__TAURI__.core.invoke("get_engine_status");
        this.updateEnginesDisplay(engines);
      } catch (e) {
        console.error("Failed to query engines from backend:", e);
      }
    } else {
      // In web dev mode
      this.updateEnginesDisplay({ word: false, powerpoint: false, libreoffice: false });
    }
  }

  private save() {
    const pptxMode = (document.querySelector('input[name="default-pptx-mode"]:checked') as HTMLInputElement)?.value as
      | "image"
      | "editable";

    const settings: AppSettings = {
      autostart: this.autostartInput.checked,
      opacity: Number(this.opacityInput.value),
      cloudSize: this.sizeSelect.value as "s" | "m" | "l",
      theme: this.themeSelect.value as "system" | "light" | "dark",
      outputMode: this.outputModeSelect.value as "next_to_original" | "custom",
      customFolder: this.customFolderInput.value,
      suffix: this.suffixInput.value,
      autoOpen: this.autoOpenInput.checked,
      preferredEngine: this.preferredEngineSelect.value as "auto" | "office" | "libreoffice",
      defaultPptxMode: pptxMode || "image",
    };

    localStorage.setItem("cloudconvert_settings", JSON.stringify(settings));
    if (this.onSettingsChanged) {
      this.onSettingsChanged(settings);
    }
  }
}
