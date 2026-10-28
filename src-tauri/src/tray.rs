use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem, Submenu},
    tray::TrayIconBuilder,
    AppHandle, Emitter, Manager, Wry,
};

pub fn setup_tray(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let open_file_item = MenuItem::with_id(app, "open_file", "Open file…", true, None::<&str>)?;
    
    // Recent conversions submenu
    let recent_sub = Submenu::with_id(app, "recent", "Recent conversions", true)?;
    let empty_recent = MenuItem::with_id(app, "recent_empty", "(No recent conversions)", false, None::<&str>)?;
    recent_sub.append(&empty_recent)?;

    let settings_item = MenuItem::with_id(app, "settings", "Settings…", true, None::<&str>)?;
    let pause_item = MenuItem::with_id(app, "pause", "Pause (hide cloud)", true, None::<&str>)?;
    let about_item = MenuItem::with_id(app, "about", "About CloudConvert", true, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;

    let menu = Menu::with_items(
        app,
        &[
            &open_file_item,
            &recent_sub,
            &PredefinedMenuItem::separator(app)?,
            &settings_item,
            &pause_item,
            &PredefinedMenuItem::separator(app)?,
            &about_item,
            &quit_item,
        ],
    )?;

    let _tray = TrayIconBuilder::new()
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| {
            match event.id.as_ref() {
                "open_file" => {
                    let _ = app.emit("tray-open-file", ());
                }
                "settings" => {
                    let _ = app.emit("open-settings", ());
                }
                "pause" => {
                    if let Some(win) = app.get_webview_window("main") {
                        if let Ok(visible) = win.is_visible() {
                            if visible {
                                let _ = win.hide();
                            } else {
                                let _ = win.show();
                            }
                        }
                    }
                }
                "about" => {
                    let _ = app.emit("open-settings", ());
                }
                "quit" => {
                    app.exit(0);
                }
                _ => {}
            }
        })
        .build(app)?;

    Ok(())
}
