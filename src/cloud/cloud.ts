/**
 * Cloud Widget State Controller
 */
export type CloudState =
  | "idle"
  | "hover"
  | "dragover"
  | "invalid"
  | "processing"
  | "success"
  | "error";

export class CloudWidget {
  private container: HTMLElement;
  private tooltip: HTMLElement;
  private progressBar: SVGCircleElement | null;
  private currentState: CloudState = "idle";
  private resetTimeout: number | null = null;
  private readonly circumference = 226; // 2 * PI * 36

  constructor(
    containerId: string = "cloud-container",
    tooltipId: string = "cloud-tooltip",
    progressBarId: string = "progress-bar"
  ) {
    this.container = document.getElementById(containerId) as HTMLElement;
    this.tooltip = document.getElementById(tooltipId) as HTMLElement;
    this.progressBar = document.getElementById(progressBarId) as unknown as SVGCircleElement;
  }

  public setState(state: CloudState, tooltipText?: string) {
    if (this.resetTimeout) {
      clearTimeout(this.resetTimeout);
      this.resetTimeout = null;
    }

    this.container.classList.remove(
      "cloud-state-idle",
      "cloud-state-hover",
      "cloud-state-dragover",
      "cloud-state-invalid",
      "cloud-state-processing",
      "cloud-state-success",
      "cloud-state-error"
    );

    this.currentState = state;
    this.container.classList.add(`cloud-state-${state}`);

    if (tooltipText) {
      this.tooltip.textContent = tooltipText;
    } else {
      switch (state) {
        case "idle":
          this.tooltip.textContent = "Drop a file or click";
          break;
        case "dragover":
          this.tooltip.textContent = "Drop to convert";
          break;
        case "invalid":
          this.tooltip.textContent = "Unsupported file";
          break;
        case "processing":
          this.tooltip.textContent = "Converting…";
          break;
        case "success":
          this.tooltip.textContent = "Complete!";
          break;
        case "error":
          this.tooltip.textContent = "Conversion failed";
          break;
      }
    }

    if (state === "success") {
      this.resetTimeout = window.setTimeout(() => {
        this.setState("idle");
      }, 1500);
    } else if (state === "error") {
      this.resetTimeout = window.setTimeout(() => {
        this.setState("idle");
      }, 3000);
    } else if (state === "invalid") {
      this.resetTimeout = window.setTimeout(() => {
        this.setState("idle");
      }, 1200);
    }
  }

  public setProgress(percent: number) {
    if (this.progressBar) {
      const offset = this.circumference - (percent / 100) * this.circumference;
      this.progressBar.style.strokeDashoffset = `${offset}`;
    }
  }

  public getState(): CloudState {
    return this.currentState;
  }
}
