use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Emitter};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ProgressPayload {
    pub job: String,
    pub percent: u32,
    pub stage: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DonePayload {
    pub job: String,
    pub output: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ErrorPayload {
    pub job: String,
    pub code: String,
    pub message: String,
}

#[derive(Debug, Deserialize)]
struct RawHelperEvent {
    event: String,
    job: Option<String>,
    percent: Option<u32>,
    stage: Option<String>,
    output: Option<String>,
    code: Option<String>,
    message: Option<String>,
}

#[derive(Default, Clone)]
pub struct JobManager {
    running_processes: Arc<Mutex<HashMap<String, u32>>>,
}

impl JobManager {
    pub fn new() -> Self {
        Self {
            running_processes: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub fn start_job(
        &self,
        app: AppHandle,
        helper_path: String,
        job_id: String,
        input_path: String,
        target_format: String,
        pptx_mode: String,
    ) -> Result<(), String> {
        let running_map = self.running_processes.clone();
        let job_id_cloned = job_id.clone();

        std::thread::spawn(move || {
            let mut cmd = Command::new("python3");
            cmd.arg(&helper_path)
                .arg("convert")
                .arg("--in")
                .arg(&input_path)
                .arg("--to")
                .arg(&target_format)
                .arg("--pptx-mode")
                .arg(&pptx_mode)
                .arg("--job")
                .arg(&job_id_cloned)
                .stdout(Stdio::piped())
                .stderr(Stdio::piped());

            let mut child = match cmd.spawn() {
                Ok(c) => c,
                Err(e) => {
                    let _ = app.emit(
                        "conversion-error",
                        ErrorPayload {
                            job: job_id_cloned,
                            code: "ENGINE_CRASH".into(),
                            message: format!("Failed to spawn converter helper: {}", e),
                        },
                    );
                    return;
                }
            };

            let pid = child.id();
            {
                let mut map = running_map.lock().unwrap();
                map.insert(job_id_cloned.clone(), pid);
            }

            if let Some(stdout) = child.stdout.take() {
                let reader = BufReader::new(stdout);
                for line in reader.lines().flatten() {
                    if let Ok(event) = serde_json::from_str::<RawHelperEvent>(&line) {
                        let j_id = event.job.unwrap_or_else(|| job_id_cloned.clone());
                        match event.event.as_str() {
                            "progress" => {
                                let _ = app.emit(
                                    "conversion-progress",
                                    ProgressPayload {
                                        job: j_id,
                                        percent: event.percent.unwrap_or(0),
                                        stage: event.stage.unwrap_or_else(|| "Converting…".into()),
                                    },
                                );
                            }
                            "done" => {
                                let _ = app.emit(
                                    "conversion-done",
                                    DonePayload {
                                        job: j_id,
                                        output: event.output.unwrap_or_default(),
                                    },
                                );
                            }
                            "error" => {
                                let _ = app.emit(
                                    "conversion-error",
                                    ErrorPayload {
                                        job: j_id,
                                        code: event.code.unwrap_or_else(|| "ENGINE_CRASH".into()),
                                        message: event.message.unwrap_or_else(|| "Conversion failed".into()),
                                    },
                                );
                            }
                            _ => {}
                        }
                    }
                }
            }

            let _ = child.wait();

            let mut map = running_map.lock().unwrap();
            map.remove(&job_id_cloned);
        });

        Ok(())
    }

    pub fn cancel_job(&self, job_id: &str) -> Result<(), String> {
        let mut map = self.running_processes.lock().unwrap();
        if let Some(pid) = map.remove(job_id) {
            #[cfg(unix)]
            {
                unsafe {
                    libc::kill(pid as i32, libc::SIGTERM);
                }
            }
            #[cfg(windows)]
            {
                let _ = Command::new("taskkill")
                    .arg("/F")
                    .arg("/PID")
                    .arg(pid.to_string())
                    .output();
            }
        }
        Ok(())
    }
}
