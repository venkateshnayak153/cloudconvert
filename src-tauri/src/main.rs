// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod engines;
mod jobs;
mod settings;
mod tray;

use engines::EngineStatus;
use jobs::JobManager;
use settings::{snap_to_edge, AppConfig, ConfigStore, WindowPosition};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Manager, PhysicalPosition, State};

struct AppState {
    job_manager: JobManager,
    config_store: ConfigStore,
    config: Mutex<AppConfig>,
    helper_path: PathBuf,
}

#[tauri::command]
fn start_conversion(
    state: State<'_, Arc<AppState>>,
    app: AppHandle,
    job_id: String,
    input_path: String,
    target_format: String,
    pptx_mode: String,
) -> Result<(), String> {
    let helper_str = state.helper_path.to_string_lossy().to_string();
    state.job_manager.start_job(app, helper_str, job_id, input_path, target_format, pptx_mode)
}

#[tauri::command]
fn cancel_conversion(state: State<'_, Arc<AppState>>, job_id: String) -> Result<(), String> {
    state.job_manager.cancel_job(&job_id)
}

#[tauri::command]
fn get_engine_status(state: State<'_, Arc<AppState>>) -> EngineStatus {
    let helper_str = state.helper_path.to_string_lossy().to_string();
    engines::detect_engines(&helper_str)
}

#[tauri::command]
fn open_path(path: String) -> Result<(), String> {
    open::that(path).map_err(|e| e.to_string())
}

#[tauri::command]
fn show_in_folder(path: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open")
            .arg("-R")
            .arg(&path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("explorer")
            .arg(format!("/select,\"{}\"", path))
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "linux")]
    {
        let p = std::path::Path::new(&path);
        let dir = if p.is_file() {
            p.parent().unwrap_or(p)
        } else {
            p
        };
        open::that(dir).map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
async fn open_file_dialog(app: AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;
    let (tx, rx) = tokio::sync::oneshot::channel();
    app.dialog()
        .file()
        .add_filter("Supported Documents", &["pdf", "docx", "doc", "pptx", "ppt", "docm", "pptm", "rtf"])
        .pick_file(move |file_path| {
            let _ = tx.send(file_path.map(|p| p.to_string()));
        });

    rx.await.map_err(|e| e.to_string())
}

#[tauri::command]
fn show_context_menu(app: AppHandle) {
    let _ = app.emit("open-settings", ());
}

fn main() {
    let config_store = ConfigStore::new();
    let initial_config = config_store.load();

    // Determine helper script path relative to current dir or executable
    let helper_path = std::env::current_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join("helper")
        .join("main.py");

    let app_state = Arc::new(AppState {
        job_manager: JobManager::new(),
        config_store,
        config: Mutex::new(initial_config.clone()),
        helper_path,
    });

    let app_state_clone = app_state.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec!["--autostart"]),
        ))
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(win) = app.get_webview_window("main") {
                let _ = win.show();
                let _ = win.set_focus();
            }
        }))
        .manage(app_state)
        .setup(move |app| {
            tray::setup_tray(app.handle())?;

            if let Some(window) = app.get_webview_window("main") {
                // Restore window position if saved
                if let Some(pos) = initial_config.last_position {
                    let _ = window.set_position(PhysicalPosition::new(pos.x, pos.y));
                }

                // Window move listener to remember position and snap to edge
                let win_clone = window.clone();
                let state_clone = app_state_clone.clone();

                window.on_window_event(move |event| match event {
                    tauri::WindowEvent::Moved(pos) => {
                        if let Ok(Some(monitor)) = win_clone.current_monitor() {
                            let mon_size = monitor.size();
                            let win_size = win_clone.outer_size().unwrap_or(tauri::PhysicalSize::new(320, 380));

                            let (snapped_x, snapped_y) = snap_to_edge(
                                pos.x,
                                pos.y,
                                win_size.width as i32,
                                win_size.height as i32,
                                mon_size.width as i32,
                                mon_size.height as i32,
                            );

                            if snapped_x != pos.x || snapped_y != pos.y {
                                let _ = win_clone.set_position(PhysicalPosition::new(snapped_x, snapped_y));
                            }

                            if let Ok(mut cfg) = state_clone.config.lock() {
                                cfg.last_position = Some(WindowPosition {
                                    x: snapped_x,
                                    y: snapped_y,
                                });
                                let _ = state_clone.config_store.save(&cfg);
                            }
                        }
                    }
                    _ => {}
                });
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            start_conversion,
            cancel_conversion,
            get_engine_status,
            open_path,
            show_in_folder,
            open_file_dialog,
            show_context_menu,
        ])
        .run(tauri::generate_context!())
        .expect("error while running CloudConvert application");
}
