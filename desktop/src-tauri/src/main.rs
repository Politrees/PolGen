#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use fs2::FileExt;
use serde::Serialize;
use std::{
    error::Error,
    fmt,
    fs::{self, OpenOptions},
    io::{self, BufRead, BufReader, Read, Write},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
    time::Instant,
};
use tauri::{Manager, RunEvent, WindowEvent};

#[derive(Clone)]
struct BackendState {
    url: Arc<Mutex<Option<String>>>,
    child: Arc<Mutex<Option<Child>>>,
    project_root: Arc<Mutex<Option<PathBuf>>>,
    setup_running: Arc<AtomicBool>,
}

struct InstanceLock { _file: Mutex<std::fs::File> }

#[derive(Debug)]
struct SetupMsg(String);
impl fmt::Display for SetupMsg { fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { write!(f, "{}", self.0) } }
impl Error for SetupMsg {}

#[derive(Serialize, Clone)]
struct EnvStatus { ready: bool, python_found: bool, env_exists: bool, project_root: Option<String> }

#[derive(Serialize, Clone)]
struct SetupLogEvent { line: String }

#[derive(Serialize, Clone)]
struct SetupDoneEvent { success: bool, message: String }

#[derive(Serialize, Clone)]
struct PlatformInfo { os: String, has_nvidia: bool, recommended_url: String, all_variants: Vec<EnvVariant> }

#[derive(Serialize, Clone)]
struct EnvVariant { label: String, url: String, description: String }

#[derive(Serialize, Clone)]
struct DownloadProgressEvent {
    downloaded_mb: f64,
    total_mb: f64,
    percent: f64,
    speed_mbps: f64,
    eta_seconds: f64,
    message: String,
}

#[derive(Serialize, Clone)]
struct DownloadDoneEvent { success: bool, message: String }

// ═══════════════════════════════════════════════════════════════

fn file_exists(p: &Path) -> bool { fs::metadata(p).is_ok() }
fn dir_exists(p: &Path) -> bool { fs::metadata(p).map(|m| m.is_dir()).unwrap_or(false) }

fn find_project_root() -> Option<PathBuf> {
    // 1. Переменная окружения
    if let Ok(root) = std::env::var("POLGEN_ROOT") {
        let p = PathBuf::from(&root);
        if file_exists(&p.join("app.py")) { return Some(p); }
    }

    // 2. Кандидаты: cwd + exe dir
    let mut candidates: Vec<PathBuf> = vec![];
    if let Ok(cd) = std::env::current_dir() { candidates.push(cd); }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(p) = exe.parent() { candidates.push(p.to_path_buf()); }
    }

    // 3. Вверх до 8 уровней от каждого кандидата
    let mut expanded: Vec<PathBuf> = vec![];
    for c in &candidates {
        let mut cur = c.clone();
        for _ in 0..8 {
            expanded.push(cur.clone());
            match cur.parent() {
                Some(p) => cur = p.to_path_buf(),
                None => break,
            }
        }
    }

    // 4. Ищем маркеры: app.py + rvc/ (models/ может не существовать при первом запуске)
    for base in &expanded {
        let has_app = file_exists(&base.join("app.py"));
        let has_rvc = dir_exists(&base.join("rvc"));
        if has_app && has_rvc {
            return Some(base.clone());
        }
    }

    None
}

fn ensure_dirs(root: &Path) {
    let dirs = [
        root.join("models"),
        root.join("models").join("RVC_models"),
        root.join("output"),
        root.join("output").join("RVC_output"),
    ];
    for d in &dirs {
        let _ = fs::create_dir_all(d);
    }
}

fn find_python(project_root: &Path) -> Option<PathBuf> {
    let env_dir = project_root.join("env");
    if cfg!(target_os = "windows") {
        for p in &[env_dir.join("python.exe"), env_dir.join("Scripts").join("python.exe")] {
            if file_exists(p) { return Some(p.clone()); }
        }
    } else {
        for name in &["python3", "python"] {
            let p = env_dir.join("bin").join(name);
            if file_exists(&p) { return Some(p); }
        }
    }
    None
}

fn find_installer_script(root: &Path) -> Option<PathBuf> {
    let name = if cfg!(target_os = "windows") { "run-PolGen-installer.bat" } else { "run-PolGen-installer.sh" };
    let p = root.join(name);
    if file_exists(&p) { Some(p) } else { None }
}

fn detect_nvidia_gpu() -> bool {
    Command::new("nvidia-smi").stdout(Stdio::null()).stderr(Stdio::null()).status().map(|s| s.success()).unwrap_or(false)
}

fn get_version_from_file(root: &Path) -> String {
    fs::read_to_string(root.join("VERSION")).ok()
        .map(|s| s.trim().trim_start_matches('v').to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "1.3.0-beta.8".into())
}

fn acquire_single_instance_lock() -> Result<InstanceLock, String> {
    let lock_path = std::env::temp_dir().join("polgen_desktop.lock");
    let file = OpenOptions::new().create(true).read(true).write(true).open(&lock_path)
        .map_err(|e| format!("lock: {e}"))?;
    file.try_lock_exclusive().map_err(|_| "PolGen Desktop уже запущен.".to_string())?;
    Ok(InstanceLock { _file: Mutex::new(file) })
}

fn format_eta(secs: f64) -> String {
    if secs <= 0.0 || !secs.is_finite() { return "—".into(); }
    let s = secs as u64;
    if s < 60 { format!("{s} сек") }
    else if s < 3600 { format!("{}:{:02}", s / 60, s % 60) }
    else { format!("{}:{:02}:{:02}", s / 3600, (s % 3600) / 60, s % 60) }
}

// ═══════════════════════════════════════════════════════════════
// HTTP download
// ═══════════════════════════════════════════════════════════════

fn download_file_with_progress(url: &str, dst: &Path, handle: &tauri::AppHandle, label: &str) -> Result<(), String> {
    let _ = handle.emit_all("setup-log", SetupLogEvent { line: format!("Скачивание {label}: {url}") });
    let resp = ureq::get(url).call().map_err(|e| format!("HTTP: {e}"))?;
    let total: u64 = resp.header("content-length").and_then(|s| s.parse().ok()).unwrap_or(0);
    let total_mb = total as f64 / 1048576.0;

    let mut reader = resp.into_reader();
    let mut file = fs::File::create(dst).map_err(|e| format!("create: {e}"))?;

    let mut downloaded: u64 = 0;
    let mut buf = [0u8; 256 * 1024];
    let start = Instant::now();
    let mut last_report = Instant::now();

    loop {
        let n = reader.read(&mut buf).map_err(|e| format!("read: {e}"))?;
        if n == 0 { break; }
        file.write_all(&buf[..n]).map_err(|e| format!("write: {e}"))?;
        downloaded += n as u64;

        if last_report.elapsed().as_millis() > 250 {
            let elapsed = start.elapsed().as_secs_f64().max(0.01);
            let dm = downloaded as f64 / 1048576.0;
            let speed = dm / elapsed;
            let pct = if total > 0 { (downloaded as f64 / total as f64) * 100.0 } else { 0.0 };
            let remaining = if total > 0 && speed > 0.01 { ((total - downloaded) as f64 / 1048576.0) / speed } else { 0.0 };
            let _ = handle.emit_all("download-progress", DownloadProgressEvent {
                downloaded_mb: dm, total_mb, percent: pct, speed_mbps: speed, eta_seconds: remaining,
                message: format!("{label}: {dm:.0}/{total_mb:.0} MB • {speed:.1} MB/s • ~{}", format_eta(remaining)),
            });
            last_report = Instant::now();
        }
    }
    let _ = handle.emit_all("setup-log", SetupLogEvent { line: format!("{label}: {:.0} MB скачано.", downloaded as f64 / 1048576.0) });
    Ok(())
}

// ═══════════════════════════════════════════════════════════════
// Backend
// ═══════════════════════════════════════════════════════════════

fn spawn_backend(root: &Path, state: &BackendState) -> Result<(), String> {
    let python = find_python(root).ok_or_else(|| "Python не найден".to_string())?;
    let mut cmd = Command::new(&python);
    cmd.current_dir(root).args(["-m", "polgen_backend", "--host", "127.0.0.1", "--port", "0"])
       .env("PYTHONUTF8", "1").env("PYTHONIOENCODING", "utf-8")
       .stdout(Stdio::piped()).stderr(Stdio::piped());
    #[cfg(target_os = "windows")] { use std::os::windows::process::CommandExt; cmd.creation_flags(0x08000000); }
    let mut child = cmd.spawn().map_err(|e| format!("spawn: {e}"))?;
    let stdout = child.stdout.take().ok_or("no stdout")?;
    let stderr = child.stderr.take().ok_or("no stderr")?;
    *state.child.lock().unwrap() = Some(child);
    let url_arc = state.url.clone();
    std::thread::spawn(move || { for line in BufReader::new(stdout).lines().flatten() { println!("[backend] {line}"); if let Some(url) = line.strip_prefix("POLGEN_BACKEND_READY ") { *url_arc.lock().unwrap() = Some(url.trim().to_string()); } } });
    std::thread::spawn(move || { for line in BufReader::new(stderr).lines().flatten() { eprintln!("[backend err] {line}"); } });
    Ok(())
}

fn kill_backend_tree(state: &BackendState) {
    if let Some(mut child) = state.child.lock().unwrap().take() {
        #[cfg(target_os = "windows")] { let _ = Command::new("taskkill").args(["/PID", &child.id().to_string(), "/T", "/F"]).stdout(Stdio::null()).stderr(Stdio::null()).status(); }
        #[cfg(not(target_os = "windows"))] { let _ = child.kill(); }
        let _ = child.wait();
    }
}

fn kill_orphan_polgen_python() {
    #[cfg(target_os = "windows")] {
        let _ = Command::new("powershell").args(["-NoProfile", "-Command",
            r#"Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "polgen_backend" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"#
        ]).stdout(Stdio::null()).stderr(Stdio::null()).status();
    }
    #[cfg(not(target_os = "windows"))] { let _ = Command::new("pkill").args(["-f", "polgen_backend"]).stdout(Stdio::null()).stderr(Stdio::null()).status(); }
}

fn kill_backend_and_orphans(state: &BackendState) { kill_backend_tree(state); kill_orphan_polgen_python(); }

fn open_path_in_explorer(path: &str) -> Result<(), String> {
    if path.trim().is_empty() { return Err("path пустой".into()); }
    let r = if cfg!(target_os = "windows") { Command::new("explorer").arg(path).spawn() }
    else if cfg!(target_os = "macos") { Command::new("open").arg(path).spawn() }
    else { Command::new("xdg-open").arg(path).spawn() };
    r.map(|_| ()).map_err(|e| format!("{e}"))
}

fn is_safe_model_name(name: &str) -> bool { !name.is_empty() && !name.contains("..") && !name.contains('/') && !name.contains('\\') }

// ═══════════════════════════════════════════════════════════════
// Post-install
// ═══════════════════════════════════════════════════════════════

fn install_ffmpeg(root: &Path, handle: &tauri::AppHandle) -> Result<(), String> {
    if cfg!(target_os = "windows") {
        let ffmpeg = root.join("ffmpeg.exe");
        let ffprobe = root.join("ffprobe.exe");
        if file_exists(&ffmpeg) && file_exists(&ffprobe) {
            let _ = handle.emit_all("setup-log", SetupLogEvent { line: "FFmpeg уже установлен.".into() });
            return Ok(());
        }
        let base = "https://huggingface.co/Politrees/RVC_resources/resolve/main/tools/ffmpeg";
        if !file_exists(&ffmpeg) { download_file_with_progress(&format!("{base}/ffmpeg.exe?download=true"), &ffmpeg, handle, "ffmpeg.exe")?; }
        if !file_exists(&ffprobe) { download_file_with_progress(&format!("{base}/ffprobe.exe?download=true"), &ffprobe, handle, "ffprobe.exe")?; }
    } else {
        let _ = handle.emit_all("setup-log", SetupLogEvent { line: "FFmpeg: системный.".into() });
    }
    Ok(())
}

fn install_rvc_models(root: &Path, handle: &tauri::AppHandle) -> Result<(), String> {
    let python = find_python(root).ok_or("Python не найден")?;
    let _ = handle.emit_all("setup-log", SetupLogEvent { line: "Установка RVC + FlashSR моделей...".into() });
    let _ = handle.emit_all("download-progress", DownloadProgressEvent {
        downloaded_mb: 0.0, total_mb: 0.0, percent: 100.0, speed_mbps: 0.0, eta_seconds: 0.0,
        message: "Установка моделей (rmvpe, hubert, FlashSR)...".into(),
    });

    let mut cmd = Command::new(&python);
    cmd.current_dir(root)
       .args([
           "-c",
           "from assets.model_installer import check_and_install_models; check_and_install_models(include_flashsr=True)",
       ])
       .env("PYTHONUTF8", "1")
       .env("PYTHONIOENCODING", "utf-8")
       .stdout(Stdio::piped())
       .stderr(Stdio::piped());

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }

    let mut child = cmd.spawn().map_err(|e| format!("model_installer spawn: {e}"))?;

    // stdout — tqdm пишет прогресс сюда
    if let Some(out) = child.stdout.take() {
        let h = handle.clone();
        std::thread::spawn(move || {
            let reader = BufReader::new(out);
            for line in reader.lines().flatten() {
                // Фильтруем пустые строки и \r-прогрессбары tqdm
                let clean = line.trim().to_string();
                if !clean.is_empty() {
                    let _ = h.emit_all("setup-log", SetupLogEvent { line: clean });
                }
            }
        });
    }

    // stderr — tqdm часто пишет прогресс в stderr
    if let Some(err) = child.stderr.take() {
        let h = handle.clone();
        std::thread::spawn(move || {
            let reader = BufReader::new(err);
            for line in reader.lines().flatten() {
                let clean = line.trim().to_string();
                if !clean.is_empty() {
                    let _ = h.emit_all("setup-log", SetupLogEvent { line: clean });
                }
            }
        });
    }

    let status = child.wait().map_err(|e| format!("model_installer wait: {e}"))?;
    if status.success() {
        let _ = handle.emit_all("setup-log", SetupLogEvent { line: "✓ Модели установлены.".into() });
    } else {
        let _ = handle.emit_all("setup-log", SetupLogEvent { line: format!("⚠ model_installer exit: {status}") });
    }
    Ok(())
}

// ═══════════════════════════════════════════════════════════════
// Tauri Commands
// ═══════════════════════════════════════════════════════════════

#[tauri::command]
fn backend_get_url(state: tauri::State<BackendState>) -> Option<String> { state.url.lock().unwrap().clone() }

#[tauri::command]
fn backend_restart(state: tauri::State<BackendState>) -> Result<(), String> {
    kill_backend_and_orphans(&state);
    *state.url.lock().unwrap() = None;
    let root = state.project_root.lock().unwrap().clone().ok_or("no root")?;
    spawn_backend(&root, &state)
}

#[tauri::command]
fn check_env_ready(state: tauri::State<BackendState>) -> EnvStatus {
    match state.project_root.lock().unwrap().clone() {
        Some(root) => EnvStatus {
            ready: dir_exists(&root.join("env")) && find_python(&root).is_some(),
            python_found: find_python(&root).is_some(),
            env_exists: dir_exists(&root.join("env")),
            project_root: Some(root.display().to_string()),
        },
        None => EnvStatus { ready: false, python_found: false, env_exists: false, project_root: None },
    }
}

#[tauri::command]
fn detect_platform(state: tauri::State<BackendState>) -> PlatformInfo {
    let root = state.project_root.lock().unwrap().clone();
    let version = root.as_ref().map(|r| get_version_from_file(r)).unwrap_or_else(|| "1.3.0-beta.8".into());
    let base = "https://huggingface.co/Politrees/PolGen/resolve/main";
    let has_nvidia = detect_nvidia_gpu();
    let os_name = if cfg!(target_os = "windows") { "windows" } else if cfg!(target_os = "macos") { "macos" } else { "linux" };

    let mut variants = vec![];
    if cfg!(target_os = "windows") {
        variants.push(EnvVariant { label: "Windows CUDA (NVIDIA)".into(), url: format!("{base}/Windows/PolGen-{version}_Windows_CUDA.zip?download=true"), description: "NVIDIA GPU. Рекомендуется.".into() });
        variants.push(EnvVariant { label: "Windows CPU".into(), url: format!("{base}/Windows/PolGen-{version}_Windows_CPU.zip?download=true"), description: "AMD / без GPU.".into() });
    } else if cfg!(target_os = "linux") {
        variants.push(EnvVariant { label: "Linux CUDA (NVIDIA)".into(), url: format!("{base}/Linux/PolGen-{version}_Linux_CUDA.zip?download=true"), description: "NVIDIA GPU. Рекомендуется.".into() });
        variants.push(EnvVariant { label: "Linux CPU".into(), url: format!("{base}/Linux/PolGen-{version}_Linux_CPU.zip?download=true"), description: "AMD / без GPU.".into() });
    } else {
        variants.push(EnvVariant { label: "MacOS".into(), url: format!("{base}/MacOS/PolGen-{version}_MacOS.zip?download=true"), description: "Apple Silicon / Intel.".into() });
    }
    let recommended_url = if cfg!(target_os = "macos") { variants[0].url.clone() } else if has_nvidia { variants[0].url.clone() } else { variants.last().unwrap().url.clone() };
    PlatformInfo { os: os_name.into(), has_nvidia, recommended_url, all_variants: variants }
}

#[tauri::command]
fn download_env(app_handle: tauri::AppHandle, state: tauri::State<BackendState>, url: String) -> Result<(), String> {
    if state.setup_running.load(Ordering::SeqCst) { return Err("Уже запущена".into()); }
    let root = state.project_root.lock().unwrap().clone().ok_or("no root")?;
    if dir_exists(&root.join("env")) { return Err("env/ уже существует".into()); }

    state.setup_running.store(true, Ordering::SeqCst);
    let flag = state.setup_running.clone();
    let handle = app_handle.clone();

    std::thread::spawn(move || {
        let result = do_full_install(&url, &root, &handle);
        let (success, message) = match result { Ok(()) => (true, "Установка завершена!".into()), Err(e) => (false, format!("Ошибка: {e}")) };
        let _ = handle.emit_all("download-done", DownloadDoneEvent { success, message });
        flag.store(false, Ordering::SeqCst);
    });
    Ok(())
}

fn do_full_install(url: &str, root: &Path, handle: &tauri::AppHandle) -> Result<(), String> {
    let zip_path = root.join("_polgen_env_download.zip");

    // 1. Download
    download_file_with_progress(url, &zip_path, handle, "Окружение")?;

    // 2. Extract env/
    let _ = handle.emit_all("setup-log", SetupLogEvent { line: "Извлечение env/...".into() });
    let _ = handle.emit_all("download-progress", DownloadProgressEvent {
        downloaded_mb: 0.0, total_mb: 0.0, percent: 100.0, speed_mbps: 0.0, eta_seconds: 0.0,
        message: "Извлечение env/...".into(),
    });

    let zip_file = fs::File::open(&zip_path).map_err(|e| format!("open zip: {e}"))?;
    let mut archive = zip::ZipArchive::new(zip_file).map_err(|e| format!("zip parse: {e}"))?;
    let env_dir = root.join("env");
    let mut extracted: u64 = 0;

    // Логируем первые 30 путей для диагностики
    let total_entries = archive.len();
    let _ = handle.emit_all("setup-log", SetupLogEvent { line: format!("ZIP содержит {total_entries} записей") });
    for i in 0..std::cmp::min(30, total_entries) {
        if let Ok(entry) = archive.by_index(i) {
            let _ = handle.emit_all("setup-log", SetupLogEvent { line: format!("  [{i}] {}", entry.name()) });
        }
    }

    // Определяем префикс env/ внутри ZIP
    // Ищем первый путь содержащий /env/ или начинающийся с env/
    let mut env_prefix: Option<String> = None;
    for i in 0..total_entries {
        if let Ok(entry) = archive.by_index(i) {
            let name = entry.name().replace('\\', "/");
            // Ищем паттерн: "что-угодно/env/" или просто "env/"
            if let Some(pos) = name.find("/env/") {
                env_prefix = Some(name[..pos + 5].to_string()); // включая "/env/"
                let _ = handle.emit_all("setup-log", SetupLogEvent {
                    line: format!("Найден env/ с префиксом: {}", env_prefix.as_ref().unwrap()),
                });
                break;
            } else if name.starts_with("env/") {
                env_prefix = Some("env/".to_string());
                let _ = handle.emit_all("setup-log", SetupLogEvent { line: "Найден env/ в корне ZIP".into() });
                break;
            }
        }
    }

    if env_prefix.is_none() {
        // Fallback: может быть env — директория без trailing slash
        for i in 0..total_entries {
            if let Ok(entry) = archive.by_index(i) {
                let name = entry.name().replace('\\', "/");
                if name.contains("/env") && entry.is_dir() {
                    env_prefix = Some(name.to_string());
                    let _ = handle.emit_all("setup-log", SetupLogEvent {
                        line: format!("Найден env/ (dir entry): {}", env_prefix.as_ref().unwrap()),
                    });
                    break;
                }
            }
        }
    }

    let prefix = env_prefix.ok_or_else(|| {
        "В ZIP не найдена папка env/. Проверьте что скачан правильный архив.".to_string()
    })?;

    // Извлекаем файлы
    for i in 0..total_entries {
        let mut entry = archive.by_index(i).map_err(|e| format!("zip entry {i}: {e}"))?;
        let raw_name = entry.name().replace('\\', "/");

        // Проверяем что путь начинается с найденного префикса
        if !raw_name.starts_with(&prefix) {
            continue;
        }

        // Получаем относительный путь после prefix
        let rel = &raw_name[prefix.len()..];
        if rel.is_empty() {
            fs::create_dir_all(&env_dir).map_err(|e| format!("mkdir env: {e}"))?;
            continue;
        }

        let target = env_dir.join(rel);

        if entry.is_dir() {
            fs::create_dir_all(&target).map_err(|e| format!("mkdir: {e}"))?;
        } else {
            if let Some(parent) = target.parent() {
                fs::create_dir_all(parent).map_err(|e| format!("mkdir parent: {e}"))?;
            }
            let mut out = fs::File::create(&target).map_err(|e| format!("create {}: {e}", target.display()))?;
            io::copy(&mut entry, &mut out).map_err(|e| format!("copy: {e}"))?;

            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                if let Some(mode) = entry.unix_mode() {
                    let _ = fs::set_permissions(&target, fs::Permissions::from_mode(mode));
                }
            }

            extracted += 1;
            if extracted % 2000 == 0 {
                let _ = handle.emit_all("setup-log", SetupLogEvent {
                    line: format!("Извлечено: {extracted} файлов"),
                });
                let _ = handle.emit_all("download-progress", DownloadProgressEvent {
                    downloaded_mb: 0.0, total_mb: 0.0, percent: 100.0, speed_mbps: 0.0, eta_seconds: 0.0,
                    message: format!("Извлечение: {extracted} файлов..."),
                });
            }
        }
    }

    let _ = fs::remove_file(&zip_path);
    let _ = handle.emit_all("setup-log", SetupLogEvent { line: format!("env/ извлечён: {extracted} файлов") });

    if extracted == 0 {
        return Err("Не удалось извлечь ни одного файла из env/. Структура ZIP не соответствует ожидаемой.".into());
    }

    // 3. Ensure dirs
    ensure_dirs(root);

    // 4. FFmpeg
    if let Err(e) = install_ffmpeg(root, handle) {
        let _ = handle.emit_all("setup-log", SetupLogEvent { line: format!("⚠ FFmpeg: {e}") });
    }

    // 5. RVC models
    if let Err(e) = install_rvc_models(root, handle) {
        let _ = handle.emit_all("setup-log", SetupLogEvent { line: format!("⚠ Модели: {e}") });
    }

    let _ = handle.emit_all("setup-log", SetupLogEvent { line: "✓ Установка завершена!".into() });
    Ok(())
}

#[tauri::command]
fn run_setup(app_handle: tauri::AppHandle, state: tauri::State<BackendState>) -> Result<(), String> {
    if state.setup_running.load(Ordering::SeqCst) { return Err("Уже запущена".into()); }
    let root = state.project_root.lock().unwrap().clone().ok_or("no root")?;
    let script = find_installer_script(&root).ok_or("Установщик не найден")?;
    state.setup_running.store(true, Ordering::SeqCst);
    let flag = state.setup_running.clone();
    let handle = app_handle.clone();
    std::thread::spawn(move || {
        let result = run_installer(&script, &root, &handle);
        let (success, message) = match result { Ok(()) => (true, "Установка завершена!".into()), Err(e) => (false, format!("Ошибка: {e}")) };
        let _ = handle.emit_all("setup-done", SetupDoneEvent { success, message });
        flag.store(false, Ordering::SeqCst);
    });
    Ok(())
}

fn run_installer(script: &Path, root: &Path, handle: &tauri::AppHandle) -> Result<(), String> {
    let mut cmd = if cfg!(target_os = "windows") { let mut c = Command::new("cmd"); c.args(["/c", &script.display().to_string()]); c }
    else { let mut c = Command::new("bash"); c.arg(script); c };
    cmd.current_dir(root).stdout(Stdio::piped()).stderr(Stdio::piped()).env("PYTHONUTF8", "1");
    #[cfg(target_os = "windows")] { use std::os::windows::process::CommandExt; cmd.creation_flags(0x08000000); }
    let mut child = cmd.spawn().map_err(|e| format!("spawn: {e}"))?;
    if let Some(out) = child.stdout.take() { let h = handle.clone(); std::thread::spawn(move || { for line in BufReader::new(out).lines().flatten() { let _ = h.emit_all("setup-log", SetupLogEvent { line }); } }); }
    if let Some(err) = child.stderr.take() { let h = handle.clone(); std::thread::spawn(move || { for line in BufReader::new(err).lines().flatten() { let _ = h.emit_all("setup-log", SetupLogEvent { line }); } }); }
    let status = child.wait().map_err(|e| format!("wait: {e}"))?;
    if status.success() { Ok(()) } else { Err(format!("exit: {status}")) }
}

#[tauri::command]
fn exit_app(app_handle: tauri::AppHandle, state: tauri::State<BackendState>) {
    kill_backend_and_orphans(&state);
    app_handle.exit(0);
}

#[tauri::command]
fn open_folder(path: String) -> Result<(), String> { open_path_in_explorer(&path) }
#[tauri::command]
fn open_file_default(path: String) -> Result<(), String> { open_path_in_explorer(&path) }
#[tauri::command]
fn open_output_dir(state: tauri::State<BackendState>) -> Result<(), String> {
    let root = state.project_root.lock().unwrap().clone().ok_or("no root")?;
    open_path_in_explorer(&root.join("output").join("RVC_output").display().to_string())
}
#[tauri::command]
fn open_rvc_model_dir(state: tauri::State<BackendState>, model_name: String) -> Result<(), String> {
    if !is_safe_model_name(&model_name) { return Err("unsafe name".into()); }
    let root = state.project_root.lock().unwrap().clone().ok_or("no root")?;
    open_path_in_explorer(&root.join("models").join("RVC_models").join(model_name).display().to_string())
}

// ═══════════════════════════════════════════════════════════════

fn main() {
    let backend_state = BackendState {
        url: Arc::new(Mutex::new(None)), child: Arc::new(Mutex::new(None)),
        project_root: Arc::new(Mutex::new(None)), setup_running: Arc::new(AtomicBool::new(false)),
    };
    let st_for_events = backend_state.clone();
    let context = tauri::generate_context!();

    let app = tauri::Builder::default()
        .manage(backend_state.clone())
        .setup(move |app| -> Result<(), Box<dyn Error>> {
            match acquire_single_instance_lock() {
                Ok(lock) => { app.manage(lock); }
                Err(msg) => {
                    if let Some(w) = app.get_window("main") { tauri::api::dialog::message(Some(&w), "PolGen", msg.clone()); }
                    return Err(Box::new(SetupMsg(msg)));
                }
            }

            let root = find_project_root().ok_or_else(|| SetupMsg(
                "Корень PolGen не найден. Убедитесь что app.py и rvc/ находятся в директории проекта, \
                 или задайте POLGEN_ROOT.".into()
            ))?;

            println!("[tauri] root: {}", root.display());
            ensure_dirs(&root);
            *backend_state.project_root.lock().unwrap() = Some(root.clone());

            if find_python(&root).is_some() {
                if let Some(sw) = app.get_window("setup") { let _ = sw.close(); }
                if let Some(mw) = app.get_window("main") { let _ = mw.show(); }
                if let Err(e) = spawn_backend(&root, &backend_state) { eprintln!("[tauri] backend error: {e}"); }
            } else {
                println!("[tauri] env not ready — showing setup");
                if let Some(sw) = app.get_window("setup") { let _ = sw.show(); let _ = sw.center(); }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            backend_get_url, backend_restart, check_env_ready, detect_platform,
            run_setup, download_env, exit_app,
            open_folder, open_file_default, open_output_dir, open_rvc_model_dir
        ])
        .build(context).expect("build error");

    app.run(move |app_handle, event| match event {
        RunEvent::WindowEvent { label: _, event: WindowEvent::CloseRequested { .. }, .. } => {
            kill_backend_and_orphans(&st_for_events);
            app_handle.exit(0);
        }
        RunEvent::WindowEvent { ref label, event: WindowEvent::Destroyed, .. } => {
            if label == "setup" {
                let vis = app_handle.get_window("main").and_then(|w| w.is_visible().ok()).unwrap_or(false);
                if !vis { kill_backend_and_orphans(&st_for_events); app_handle.exit(0); }
            }
        }
        RunEvent::ExitRequested { .. } | RunEvent::Exit => { kill_backend_and_orphans(&st_for_events); }
        _ => {}
    });
}