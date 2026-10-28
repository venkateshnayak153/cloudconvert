/**
 * Status and Result Toast Component
 */
export class StatusToast {
  private element: HTMLElement;
  private progressView: HTMLElement;
  private progressTitle: HTMLElement;
  private progressPct: HTMLElement;
  private barFill: HTMLElement;
  private stageText: HTMLElement;
  private cancelBtn: HTMLElement;

  private successView: HTMLElement;
  private successFilename: HTMLElement;
  private openBtn: HTMLElement;
  private showFolderBtn: HTMLElement;
  private copyPathBtn: HTMLElement;

  private errorView: HTMLElement;
  private errorMsg: HTMLElement;
  private detailsBtn: HTMLElement;
  private dismissBtn: HTMLElement;
  private detailsLog: HTMLElement;

  private onCancelCallback: (() => void) | null = null;
  private currentOutputPath: string = "";

  constructor() {
    this.element = document.getElementById("status-toast") as HTMLElement;

    this.progressView = document.getElementById("toast-progress-view") as HTMLElement;
    this.progressTitle = document.getElementById("toast-progress-title") as HTMLElement;
    this.progressPct = document.getElementById("toast-progress-pct") as HTMLElement;
    this.barFill = document.getElementById("toast-bar-fill") as HTMLElement;
    this.stageText = document.getElementById("toast-stage-text") as HTMLElement;
    this.cancelBtn = document.getElementById("toast-cancel-btn") as HTMLElement;

    this.successView = document.getElementById("toast-success-view") as HTMLElement;
    this.successFilename = document.getElementById("toast-success-name") as HTMLElement;
    this.openBtn = document.getElementById("toast-open-btn") as HTMLElement;
    this.showFolderBtn = document.getElementById("toast-show-folder-btn") as HTMLElement;
    this.copyPathBtn = document.getElementById("toast-copy-path-btn") as HTMLElement;

    this.errorView = document.getElementById("toast-error-view") as HTMLElement;
    this.errorMsg = document.getElementById("toast-error-message") as HTMLElement;
    this.detailsBtn = document.getElementById("toast-details-btn") as HTMLElement;
    this.dismissBtn = document.getElementById("toast-dismiss-btn") as HTMLElement;
    this.detailsLog = document.getElementById("toast-details-log") as HTMLElement;

    this.initListeners();
  }

  private async copyToClipboard(text: string): Promise<void> {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        return;
      }
    } catch {
      // Fallback below
    }
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  }

  private initListeners() {
    this.cancelBtn.addEventListener("click", () => {
      if (this.onCancelCallback) this.onCancelCallback();
      this.hide();
    });

    this.dismissBtn.addEventListener("click", () => this.hide());

    this.detailsBtn.addEventListener("click", () => {
      this.detailsLog.classList.toggle("hidden");
    });

    this.copyPathBtn.addEventListener("click", async () => {
      if (this.currentOutputPath) {
        await this.copyToClipboard(this.currentOutputPath);
        const originalText = this.copyPathBtn.textContent;
        this.copyPathBtn.textContent = "Copied!";
        setTimeout(() => {
          this.copyPathBtn.textContent = originalText;
        }, 1500);
      }
    });

    this.openBtn.addEventListener("click", () => {
      if (!this.currentOutputPath) return;
      if ((window as any).__TAURI__) {
        (window as any).__TAURI__.core.invoke("open_path", { path: this.currentOutputPath });
      } else {
        // Browser fallback: trigger file download or open in browser
        const filename = this.currentOutputPath.split(/[/\\]/).pop() || "converted_file";
        const dummyContent = `Simulated converted file: ${filename}\n\nConverted by CloudConvert engine.\nIn native desktop app mode, this opens directly in your default OS viewer.`;
        const blob = new Blob([dummyContent], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    });

    this.showFolderBtn.addEventListener("click", async () => {
      if (!this.currentOutputPath) return;
      if ((window as any).__TAURI__) {
        (window as any).__TAURI__.core.invoke("show_in_folder", { path: this.currentOutputPath });
      } else {
        // Browser fallback: copy folder path and notify user
        const folder = this.currentOutputPath.replace(/[/\\][^/\\]+$/, "") || "/Desktop";
        await this.copyToClipboard(folder);
        const orig = this.showFolderBtn.textContent;
        this.showFolderBtn.textContent = "Folder Copied!";
        setTimeout(() => {
          this.showFolderBtn.textContent = orig;
        }, 1500);
        alert(
          `[Desktop Mode Feature]\n\nIn the desktop app, this opens macOS Finder at the file's folder.\n\nFolder path copied to clipboard:\n${folder}`
        );
      }
    });
  }

  public showProgress(filename: string, onCancel?: () => void) {
    this.onCancelCallback = onCancel || null;
    this.progressTitle.textContent = `Converting ${filename}…`;
    this.progressPct.textContent = "0%";
    this.barFill.style.width = "0%";
    this.stageText.textContent = "Starting conversion…";

    this.progressView.classList.remove("hidden");
    this.successView.classList.add("hidden");
    this.errorView.classList.add("hidden");
    this.element.classList.remove("hidden");
  }

  public updateProgress(percent: number, stage: string) {
    this.progressPct.textContent = `${percent}%`;
    this.barFill.style.width = `${percent}%`;
    this.stageText.textContent = stage;
  }

  public showSuccess(outputPath: string) {
    this.currentOutputPath = outputPath;
    const name = outputPath.split(/[/\\]/).pop() || outputPath;
    this.successFilename.textContent = name;

    this.progressView.classList.add("hidden");
    this.successView.classList.remove("hidden");
    this.errorView.classList.add("hidden");
    this.element.classList.remove("hidden");
  }

  public showError(code: string, message: string, details?: string) {
    let friendly = message;
    switch (code) {
      case "NO_ENGINE":
        friendly = "Install LibreOffice (free) to convert this file type.";
        break;
      case "PASSWORD_PROTECTED":
        friendly = "This file is password protected.";
        break;
      case "CORRUPT_FILE":
        friendly = "This file looks damaged and could not be opened.";
        break;
      case "UNSUPPORTED_TYPE":
        friendly = "That file type isn't supported.";
        break;
      case "TIMEOUT":
        friendly = "The conversion took too long and was stopped.";
        break;
      case "DISK_FULL":
      case "PERMISSION":
        friendly = "Couldn't save next to the original. Choose another folder.";
        break;
      case "ENGINE_CRASH":
        friendly = "The converter stopped unexpectedly. Try again.";
        break;
    }

    this.errorMsg.textContent = friendly;
    this.detailsLog.textContent = details || `${code}: ${message}`;
    this.detailsLog.classList.add("hidden");

    this.progressView.classList.add("hidden");
    this.successView.classList.add("hidden");
    this.errorView.classList.remove("hidden");
    this.element.classList.remove("hidden");
  }

  public hide() {
    this.element.classList.add("hidden");
  }
}
