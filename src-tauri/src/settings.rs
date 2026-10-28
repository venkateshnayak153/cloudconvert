use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct WindowPosition {
    pub x: i32,
    pub y: i32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AppConfig {
    pub autostart: bool,
    pub idle_opacity: f32,
    pub cloud_size: String,
    pub output_dir: Option<String>,
    pub filename_suffix: String,
    pub auto_open: bool,
    pub preferred_engine: String,
    pub default_pptx_mode: String,
    pub last_position: Option<WindowPosition>,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            autostart: false,
            idle_opacity: 0.7,
            cloud_size: "m".into(),
            output_dir: None,
            filename_suffix: "_converted".into(),
            auto_open: false,
            preferred_engine: "auto".into(),
            default_pptx_mode: "image".into(),
            last_position: None,
        }
    }
}

pub struct ConfigStore {
    path: PathBuf,
}

impl ConfigStore {
    pub fn new() -> Self {
        let mut path = dirs::config_dir().unwrap_or_else(|| PathBuf::from("."));
        path.push("cloudconvert");
        let _ = fs::create_dir_all(&path);
        path.push("config.json");
        Self { path }
    }

    pub fn load(&self) -> AppConfig {
        if let Ok(data) = fs::read_to_string(&self.path) {
            if let Ok(cfg) = serde_json::from_str::<AppConfig>(&data) {
                return cfg;
            }
        }
        AppConfig::default()
    }

    pub fn save(&self, config: &AppConfig) -> Result<(), String> {
        let data = serde_json::to_string_pretty(config).map_err(|e| e.to_string())?;
        fs::write(&self.path, data).map_err(|e| e.to_string())?;
        Ok(())
    }
}

/// Snap position to screen edges if released within 24 px
pub fn snap_to_edge(x: i32, y: i32, width: i32, height: i32, screen_width: i32, screen_height: i32) -> (i32, i32) {
    const SNAP_MARGIN: i32 = 24;
    let mut new_x = x;
    let mut new_y = y;

    // Left edge
    if x < SNAP_MARGIN {
        new_x = 0;
    }
    // Right edge
    else if (screen_width - (x + width)) < SNAP_MARGIN {
        new_x = screen_width - width;
    }

    // Top edge
    if y < SNAP_MARGIN {
        new_y = 0;
    }
    // Bottom edge
    else if (screen_height - (y + height)) < SNAP_MARGIN {
        new_y = screen_height - height;
    }

    // Clamp inside screen bounds
    new_x = new_x.max(0).min(screen_width - width);
    new_y = new_y.max(0).min(screen_height - height);

    (new_x, new_y)
}
