import { CloudWidget } from "./cloud/cloud.ts";
import { FormatPicker, PickerSelection } from "./picker/picker.ts";
import { StatusToast } from "./toast/toast.ts";
import { SettingsModal } from "./settings/settings.ts";

const cloud = new CloudWidget();
const picker = new FormatPicker();
const toast = new StatusToast();
const settings = new SettingsModal();
const isTauri = () => (window as any).__TAURI__?.core?.invoke !== undefined;
let currentJobId: string | null = null;

if ((window as any).__TAURI__) {
  const { listen } = (window as any).__TAURI__.event;

  // Native Tauri drag & drop events on macOS
  listen("tauri://drag-drop", (event: any) => {
    const paths = event.payload?.paths;
    if (paths && paths.length > 0) {
      handleFileDropped(paths[0]);
    }
  });

  listen("tauri://drag-enter", () => {
    if (cloud.getState() !== "processing") {
      cloud.setState("dragover");
    }
  });

  listen("tauri://drag-leave", () => {
    if (cloud.getState() === "dragover") {
      cloud.setState("idle");
    }
  });

  listen("conversion-progress", (event: any) => {
    const payload = event.payload;
    cloud.setProgress(payload.percent);
    toast.updateProgress(payload.percent, payload.stage || "Converting…");
  });

  listen("conversion-done", (event: any) => {
    const payload = event.payload;
    cloud.setState("success");
    cloud.setProgress(100);
    toast.showSuccess(payload.output);
  });

  listen("conversion-error", (event: any) => {
    const payload = event.payload;
    cloud.setState("error");
    toast.showError(payload.code, payload.message);
  });

  listen("open-settings", () => {
    settings.show();
  });
}


// Valid formats mapping
const VALID_TARGETS_MAP: Record<string, string[]> = {
  pdf: ["docx", "doc", "pptx", "ppt"],
  docx: ["pdf", "doc"],
  doc: ["pdf", "docx"],
  pptx: ["pdf", "ppt"],
  ppt: ["pdf", "pptx"],
  docm: ["pdf", "doc", "docx"],
  dotx: ["pdf", "doc", "docx"],
  pptm: ["pdf", "ppt", "pptx"],
  potx: ["pdf", "ppt", "pptx"],
  rtf: ["pdf", "docx"],
};

const MIME_MAP: Record<string, string> = {
  "application/pdf": "pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
  "application/msword": "doc",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
  "application/vnd.ms-powerpoint": "ppt",
  "application/rtf": "rtf",
  "text/rtf": "rtf",
};

function getFileExtension(filename: string): string {
  try {
    const clean = decodeURIComponent(filename).trim().split("?")[0].split("#")[0];
    const parts = clean.split(".");
    if (parts.length > 1) {
      return parts.pop()?.toLowerCase() || "";
    }
  } catch {
    const parts = filename.trim().split(".");
    if (parts.length > 1) {
      return parts.pop()?.toLowerCase() || "";
    }
  }
  return "";
}

function handleFileDropped(filePath: string, fileName?: string, fileObj?: File) {
  const rawName = fileName || filePath.split(/[/\\]/).pop() || filePath;
  let ext = getFileExtension(rawName);

  // If a conversion is already in progress, ask the user whether to cancel it
  if (cloud.getState() === "processing") {
    const confirmCancel = window.confirm(
      "A conversion is already in progress. Cancel it and start a new one?"
    );
    if (confirmCancel) {
      cancelConversion();
    } else {
      return; // abort handling this new drop
    }
  }

  // Fallback to MIME type if extension is missing or unparseable
  if (!ext && fileObj && fileObj.type && MIME_MAP[fileObj.type]) {
    ext = MIME_MAP[fileObj.type];
  }

  // Helpful explanation for common macOS native formats
  if (ext === "pages") {
    cloud.setState("invalid", "Apple Pages not supported");
    toast.showError(
      "UNSUPPORTED_TYPE",
      "Apple Pages (.pages) cannot be converted directly. Please export to Word (.docx) or PDF in Pages first."
    );
    return;
  }

  if (ext === "key" || ext === "keynote") {
    cloud.setState("invalid", "Apple Keynote not supported");
    toast.showError(
      "UNSUPPORTED_TYPE",
      "Apple Keynote (.key) cannot be converted directly. Please export to PowerPoint (.pptx) or PDF in Keynote first."
    );
    return;
  }

  if (ext === "numbers" || ext === "xlsx" || ext === "xls" || ext === "csv") {
    cloud.setState("invalid", "Spreadsheets not supported");
    toast.showError(
      "UNSUPPORTED_TYPE",
      "Spreadsheet formats are out of scope. CloudConvert supports DOC, DOCX, PPT, PPTX, and PDF."
    );
    return;
  }

  if (["png", "jpg", "jpeg", "webp", "gif", "svg", "bmp"].includes(ext)) {
    cloud.setState("invalid", "Images not supported");
    toast.showError(
      "UNSUPPORTED_TYPE",
      "Image formats are not supported. CloudConvert supports DOC, DOCX, PPT, PPTX, and PDF."
    );
    return;
  }

  if (rawName.startsWith("._")) {
    cloud.setState("invalid", "macOS metadata file");
    toast.showError(
      "UNSUPPORTED_TYPE",
      `'${rawName}' is a macOS AppleDouble metadata file. Please select the actual document instead.`
    );
    return;
  }

  if (!VALID_TARGETS_MAP[ext]) {
    cloud.setState("invalid", "Unsupported file");
    toast.showError(
      "UNSUPPORTED_TYPE",
      `Format '${ext.toUpperCase() || "unknown"}' is not supported. Supported: DOC, DOCX, PPT, PPTX, PDF.`
    );
    return;
  }

  const validFormats = VALID_TARGETS_MAP[ext];

  // Show format picker beside cloud
  cloud.setState("hover");
  picker.show(
    rawName,
    validFormats,
    (selection: PickerSelection) => {
      startConversion(filePath, rawName, selection);
    },
    () => {
      cloud.setState("idle");
    }
  );
}

async function startConversion(filePath: string, fileName: string, selection: PickerSelection) {
  cloud.setState("processing");
  cloud.setProgress(5);
  toast.showProgress(fileName, () => {
    cancelConversion();
  });

  if ((window as any).__TAURI__) {
    try {
      const { invoke } = (window as any).__TAURI__.core;
      currentJobId = "job_" + Math.random().toString(36).substring(2, 9);
      await invoke("start_conversion", {
        jobId: currentJobId,
        inputPath: filePath,
        targetFormat: selection.format,
        pptxMode: selection.pptxMode,
      });
    } catch (err: any) {
      cloud.setState("error");
      toast.showError("ENGINE_CRASH", err?.message || String(err));
    }
    // Not running in Tauri – abort conversion
    toast.showError("Conversion only works in the desktop app. Run `npm run tauri dev`. ");
    cloud.setState("error");
    return;
}

async function cancelConversion() {
  if (currentJobId && (window as any).__TAURI__) {
    try {
      await (window as any).__TAURI__.core.invoke("cancel_conversion", { jobId: currentJobId });
    } catch (e) {
      console.error("Cancel failed:", e);
    }
  }
  cloud.setState("idle");
  cloud.setProgress(0);
}

// -------------------------------------------------------------------
// Drag and Drop Listeners (Window + Container)
// -------------------------------------------------------------------
const cloudContainer = document.getElementById("cloud-container");
const fileInput = document.getElementById("file-picker-input") as HTMLInputElement;

// The inline script in index.html already prevents browser navigation for all drag events.
// Here we just handle the visual state and file processing.

document.addEventListener("dragenter", (e) => {
  e.preventDefault();
  if (cloud.getState() !== "processing" && e.dataTransfer && e.dataTransfer.items.length > 0) {
    cloud.setState("dragover");
  }
}, { capture: true });

document.addEventListener("dragover", (e) => {
  e.preventDefault();
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = "copy";
  }
}, { capture: true });

document.addEventListener("dragleave", (e) => {
  e.preventDefault();
  // Only revert to idle if mouse truly left the browser window
  const rect = document.documentElement.getBoundingClientRect();
  if (
    e.clientX <= 0 ||
    e.clientY <= 0 ||
    e.clientX >= rect.width ||
    e.clientY >= rect.height
  ) {
    if (cloud.getState() === "dragover") {
      cloud.setState("idle");
    }
  }
}, { capture: true });

document.addEventListener("drop", (e) => {
  e.preventDefault();
  e.stopPropagation();

  if (cloud.getState() === "dragover") {
    cloud.setState("idle");
  }

  if (cloud.getState() === "processing") return;

  const dt = e.dataTransfer;
  if (!dt || dt.files.length === 0) return;

  const file = dt.files[0];

  // Try to get full path (available in Tauri or Electron), fallback to file.name
  const fullPath = (file as any).path || file.name;
  handleFileDropped(fullPath, file.name, file);
}, { capture: true });

if (cloudContainer) {
  // Click to open file picker (when idle or hover)
  cloudContainer.addEventListener("click", () => {
    if (cloud.getState() === "idle" || cloud.getState() === "hover") {
      if ((window as any).__TAURI__) {
        (window as any).__TAURI__.core.invoke("open_file_dialog").then((filePath: string | null) => {
          if (filePath) {
            handleFileDropped(filePath);
          }
        });
      } else {
        fileInput.click();
      }
    }
  });
}

if (fileInput) {
  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files.length > 0) {
      const file = fileInput.files[0];
      const path = (file as any).path || file.name;
      handleFileDropped(path, file.name, file);
    }
  });
}

// -------------------------------------------------------------------
// Tauri Native Events Listener
// -------------------------------------------------------------------

// Right click context menu
window.addEventListener("contextmenu", (e) => {
  e.preventDefault();
  if ((window as any).__TAURI__) {
    (window as any).__TAURI__.core.invoke("show_context_menu");
  } else {
    settings.show();
  }
});
