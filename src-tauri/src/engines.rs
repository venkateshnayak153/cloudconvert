use serde::{Deserialize, Serialize};
use std::process::Command;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct EngineStatus {
    pub word: bool,
    pub powerpoint: bool,
    pub libreoffice: bool,
    pub pdf2docx: bool,
    pub pdf_to_pptx: bool,
}

#[derive(Debug, Deserialize)]
struct HelperEngineEvent {
    event: String,
    engines: Option<EngineStatus>,
}

pub fn detect_engines(helper_bin_or_script: &str) -> EngineStatus {
    // Attempt running python helper
    let output = Command::new("python3")
        .arg(helper_bin_or_script)
        .arg("detect-engines")
        .output();

    if let Ok(out) = output {
        if out.status.success() {
            let stdout_str = String::from_utf8_lossy(&out.stdout);
            for line in stdout_str.lines() {
                if let Ok(parsed) = serde_json::from_str::<HelperEngineEvent>(line) {
                    if parsed.event == "engines" {
                        if let Some(eng) = parsed.engines {
                            return eng;
                        }
                    }
                }
            }
        }
    }

    // Fallback detection
    let is_mac = cfg!(target_os = "macos");
    let word_installed = if is_mac {
        std::path::Path::new("/Applications/Microsoft Word.app").exists()
    } else {
        false
    };
    let ppt_installed = if is_mac {
        std::path::Path::new("/Applications/Microsoft PowerPoint.app").exists()
    } else {
        false
    };
    let libreoffice_installed = if is_mac {
        std::path::Path::new("/Applications/LibreOffice.app").exists()
    } else {
        false
    };

    EngineStatus {
        word: word_installed,
        powerpoint: ppt_installed,
        libreoffice: libreoffice_installed,
        pdf2docx: true,
        pdf_to_pptx: true,
    }
}
