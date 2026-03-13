#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use fs2::FileExt;
use serde::Serialize;
use std::{
  error::Error,
  fmt,
  fs::OpenOptions,
  io::{BufRead, BufReader},
  path::{Path, PathBuf},
  process::{Child, Command, Stdio},
  sync::{Arc, Mutex},
};
use tauri::{Manager, RunEvent, WindowEvent};

#[derive(Clone)]
struct BackendState {
  url: Arc<Mutex<Option<String>>>,
  child: Arc<Mutex<Option<Child>>>,
  project_root: Arc<Mutex<Option<PathBuf>>>,
}

struct InstanceLock {
  _file: Mutex<std::fs::File>,
}

#[derive(Serialize)]
struct BackendInfo {
  url: Option<String>,
  project_root: Option<String>,
}

#[derive(Debug)]
struct SetupMsg(String);

impl fmt::Display for SetupMsg {
  fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
    write!(f, "{}", self.0)
  }
}
impl Error for SetupMsg {}

fn file_exists(p: &Path) -> bool {
  std::fs::metadata(p).is_ok()
}
fn dir_exists(p: &Path) -> bool {
  std::fs::metadata(p).map(|m| m.is_dir()).unwrap_or(false)
}

fn find_project_root() -> Option<PathBuf> {
  let mut candidates: Vec<PathBuf> = vec![];

  if let Ok(cd) = std::env::current_dir() {
    candidates.push(cd);
  }
  if let Ok(exe) = std::env::current_exe() {
    if let Some(parent) = exe.parent() {
      candidates.push(parent.to_path_buf());
    }
  }

  let mut expanded: Vec<PathBuf> = vec![];
  for c in candidates {
    let mut cur = c;
    for _ in 0..6 {
      expanded.push(cur.clone());
      if let Some(p) = cur.parent() {
        cur = p.to_path_buf();
      } else {
        break;
      }
    }
  }

  for base in expanded {
    let app_py = base.join("app.py");
    let rvc_dir = base.join("rvc");
    let models_dir = base.join("models");
    if file_exists(&app_py) && dir_exists(&rvc_dir) && dir_exists(&models_dir) {
      return Some(base);
    }
  }
  None
}

fn find_python(project_root: &Path) -> Option<PathBuf> {
  let p = project_root.join("env").join("python.exe");
  if file_exists(&p) { Some(p) } else { None }
}

fn acquire_single_instance_lock() -> Result<InstanceLock, String> {
  let lock_path = std::env::temp_dir().join("polgen_desktop.lock");
  let file = OpenOptions::new()
    .create(true)
    .read(true)
    .write(true)
    .open(&lock_path)
    .map_err(|e| format!("Не удалось открыть lock-файл {}: {e}", lock_path.display()))?;

  file
    .try_lock_exclusive()
    .map_err(|_e| "PolGen Desktop уже запущен. Закрой предыдущий экземпляр.".to_string())?;

  Ok(InstanceLock { _file: Mutex::new(file) })
}

fn spawn_backend(project_root: &Path, state: &BackendState) -> Result<(), String> {
  let python = find_python(project_root).ok_or_else(|| {
    format!("Не найден python.exe: {}", project_root.join("env").join("python.exe").display())
  })?;

  let mut cmd = Command::new(python);
  cmd.current_dir(project_root);
  cmd.args(["-m", "polgen_backend", "--host", "127.0.0.1", "--port", "0"]);
  cmd.env("PYTHONUTF8", "1");
  cmd.env("PYTHONIOENCODING", "utf-8");
  cmd.stdout(Stdio::piped());
  cmd.stderr(Stdio::piped());

  let mut child = cmd.spawn().map_err(|e| format!("Не удалось запустить backend: {e}"))?;

  let stdout = child.stdout.take().ok_or_else(|| "Не удалось захватить stdout backend".to_string())?;
  let stderr = child.stderr.take().ok_or_else(|| "Не удалось захватить stderr backend".to_string())?;

  {
    let mut guard = state.child.lock().unwrap();
    *guard = Some(child);
  }

  let url_arc = state.url.clone();
  std::thread::spawn(move || {
    let reader = BufReader::new(stdout);
    for line in reader.lines().flatten() {
      println!("[backend stdout] {line}");
      if let Some(url) = line.strip_prefix("POLGEN_BACKEND_READY ") {
        let mut g = url_arc.lock().unwrap();
        *g = Some(url.trim().to_string());
      }
    }
  });

  std::thread::spawn(move || {
    let reader = BufReader::new(stderr);
    for line in reader.lines().flatten() {
      eprintln!("[backend stderr] {line}");
    }
  });

  Ok(())
}

#[cfg(target_os = "windows")]
fn kill_orphan_polgen_python() {
  let ps = r#"
  $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'"
  foreach ($p in $procs) {
    if ($p.CommandLine -and $p.CommandLine -match "polgen_backend") {
      try { Stop-Process -Id $p.ProcessId -Force } catch {}
    }
  }
  "#;

  let _ = Command::new("powershell")
    .args(["-NoProfile", "-Command", ps])
    .status();
}
#[cfg(not(target_os = "windows"))]
fn kill_orphan_polgen_python() {}

fn kill_backend_tree(state: &BackendState) {
  let mut guard = state.child.lock().unwrap();
  if let Some(mut child) = guard.take() {
    let pid = child.id();

    #[cfg(target_os = "windows")]
    {
      let _ = Command::new("taskkill").args(["/PID", &pid.to_string(), "/T", "/F"]).status();
    }
    #[cfg(not(target_os = "windows"))]
    {
      let _ = child.kill();
    }

    let _ = child.wait();
  }
}

fn kill_backend_and_orphans(state: &BackendState) {
  kill_backend_tree(state);
  kill_orphan_polgen_python();
}

#[tauri::command]
fn backend_get_url(state: tauri::State<BackendState>) -> Option<String> {
  state.url.lock().unwrap().clone()
}

#[tauri::command]
fn backend_restart(state: tauri::State<BackendState>) -> Result<(), String> {
  kill_backend_and_orphans(&state);
  {
    let mut g = state.url.lock().unwrap();
    *g = None;
  }

  let root = state
    .project_root
    .lock()
    .unwrap()
    .clone()
    .ok_or_else(|| "project_root неизвестен".to_string())?;

  spawn_backend(&root, &state)
}

#[tauri::command]
fn open_folder(path: String) -> Result<(), String> {
  if path.trim().is_empty() {
    return Err("path пустой".to_string());
  }

  #[cfg(target_os = "windows")]
  {
    Command::new("explorer").arg(&path).spawn().map_err(|e| format!("explorer error: {e}"))?;
    return Ok(());
  }
  #[cfg(target_os = "macos")]
  {
    Command::new("open").arg(&path).spawn().map_err(|e| format!("open error: {e}"))?;
    return Ok(());
  }
  #[cfg(target_os = "linux")]
  {
    Command::new("xdg-open").arg(&path).spawn().map_err(|e| format!("xdg-open error: {e}"))?;
    return Ok(());
  }

  #[allow(unreachable_code)]
  Err("unsupported os".to_string())
}

#[tauri::command]
fn open_file_default(path: String) -> Result<(), String> {
  if path.trim().is_empty() {
    return Err("path пустой".to_string());
  }

  #[cfg(target_os = "windows")]
  {
    Command::new("explorer").arg(&path).spawn().map_err(|e| format!("explorer error: {e}"))?;
    return Ok(());
  }
  #[cfg(target_os = "macos")]
  {
    Command::new("open").arg(&path).spawn().map_err(|e| format!("open error: {e}"))?;
    return Ok(());
  }
  #[cfg(target_os = "linux")]
  {
    Command::new("xdg-open").arg(&path).spawn().map_err(|e| format!("xdg-open error: {e}"))?;
    return Ok(());
  }

  #[allow(unreachable_code)]
  Err("unsupported os".to_string())
}

#[tauri::command]
fn open_output_dir(state: tauri::State<BackendState>) -> Result<(), String> {
  let root = state
    .project_root
    .lock()
    .unwrap()
    .clone()
    .ok_or_else(|| "project_root неизвестен".to_string())?;

  let out_dir = root.join("output").join("RVC_output");
  open_folder(out_dir.display().to_string())
}

fn _is_safe_model_name(name: &str) -> bool {
  if name.is_empty() { return false; }
  if name.contains("..") { return false; }
  if name.contains('/') || name.contains('\\') { return false; }
  true
}

#[tauri::command]
fn open_rvc_model_dir(state: tauri::State<BackendState>, model_name: String) -> Result<(), String> {
  if !_is_safe_model_name(&model_name) {
    return Err("model_name небезопасный".to_string());
  }

  let root = state
    .project_root
    .lock()
    .unwrap()
    .clone()
    .ok_or_else(|| "project_root неизвестен".to_string())?;

  let dir = root.join("models").join("RVC_models").join(model_name);
  open_folder(dir.display().to_string())
}

fn main() {
  let backend_state = BackendState {
    url: Arc::new(Mutex::new(None)),
    child: Arc::new(Mutex::new(None)),
    project_root: Arc::new(Mutex::new(None)),
  };

  let st_for_events = backend_state.clone();
  let context = tauri::generate_context!();

  let app = tauri::Builder::default()
    .manage(backend_state.clone())
    .setup(move |app| -> Result<(), Box<dyn Error>> {
      // IMPORTANT: match arms must return ()
      match acquire_single_instance_lock() {
        Ok(lock) => {
          app.manage(lock);
        }
        Err(msg) => {
          if let Some(w) = app.get_window("main") {
            tauri::api::dialog::message(Some(&w), "PolGen Desktop", msg.clone());
          } else {
            eprintln!("{msg}");
          }
          return Err(Box::new(SetupMsg(msg)));
        }
      }

      let root = find_project_root().ok_or_else(|| SetupMsg("Не удалось найти корень PolGen".to_string()))?;
      {
        let mut g = backend_state.project_root.lock().unwrap();
        *g = Some(root.clone());
      }

      spawn_backend(&root, &backend_state).map_err(|e| Box::new(SetupMsg(e)) as Box<dyn Error>)?;
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![
      backend_get_url,
      backend_restart,
      open_folder,
      open_file_default,
      open_output_dir,
      open_rvc_model_dir
    ])
    .build(context)
    .expect("error while building tauri application");

  app.run(move |_app_handle, event| match event {
    RunEvent::WindowEvent { event: WindowEvent::CloseRequested { .. }, .. } => {
      kill_backend_and_orphans(&st_for_events);
    }
    RunEvent::ExitRequested { .. } => {
      kill_backend_and_orphans(&st_for_events);
    }
    RunEvent::Exit => {
      kill_backend_and_orphans(&st_for_events);
    }
    _ => {}
  });
}