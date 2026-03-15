import { writable } from "svelte/store";
import type {
  JobSnapshot,
  TabKey,
  RvcForm,
  TtsForm,
  UvrForm,
  InstallUrlForm,
  InstallZipForm,
  InstallFilesForm,
  ToastItem,
} from "./types";

// ═══════════════════════════════════════════════════════════════
// Backend
// ═══════════════════════════════════════════════════════════════

export const backendUrl = writable<string | null>(null);
export const backendReady = writable(false);

// ═══════════════════════════════════════════════════════════════
// Data
// ═══════════════════════════════════════════════════════════════

export const models = writable<string[]>([]);
export const edgeVoices = writable<Record<string, string[]>>({});

// UVR
export const uvrModels = writable<Record<string, string[]>>({});
export const uvrFormats = writable<string[]>(["wav", "flac", "mp3", "ogg", "m4a"]);
export const uvrStems = writable<string[]>([]);

// ═══════════════════════════════════════════════════════════════
// Navigation
// ═══════════════════════════════════════════════════════════════

export const activeTab = writable<TabKey>("models");

// ═══════════════════════════════════════════════════════════════
// Job tracking
// ═══════════════════════════════════════════════════════════════

export const currentJob = writable<JobSnapshot | null>(null);
export const currentJobId = writable<string | null>(null);
export const jobRunning = writable(false);

// ═══════════════════════════════════════════════════════════════
// Player
// ═══════════════════════════════════════════════════════════════

export const playerPath = writable<string | null>(null);

// ═══════════════════════════════════════════════════════════════
// Logs & Toasts
// ═══════════════════════════════════════════════════════════════

const MAX_LOG_LINES = 5000;

function createLogStore() {
  const { subscribe, update } = writable<string[]>([]);

  return {
    subscribe,
    append(line: string) {
      update((lines) => {
        const next = [...lines, line];
        return next.length > MAX_LOG_LINES
          ? next.slice(next.length - MAX_LOG_LINES)
          : next;
      });
    },
    clear() {
      update(() => []);
    },
  };
}

export const logs = createLogStore();

let toastIdCounter = 0;

function createToastStore() {
  const { subscribe, update } = writable<ToastItem[]>([]);

  return {
    subscribe,
    show(message: string, duration = 4000) {
      const id = ++toastIdCounter;
      update((items) => [...items, { id, message }]);
      setTimeout(() => {
        update((items) => items.filter((t) => t.id !== id));
      }, duration);
    },
  };
}

export const toasts = createToastStore();

// ═══════════════════════════════════════════════════════════════
// Form state (persistent between tab switches)
// ═══════════════════════════════════════════════════════════════

export const rvcForm = writable<RvcForm>({
  input_path: "",
  rvc_model: "",
  f0_method: "rmvpe",
  f0_min: 50,
  f0_max: 1100,
  rvc_pitch: 0,
  protect: 0.5,
  index_rate: 0,
  volume_envelope: 1,
  autopitch: false,
  autopitch_threshold: 155,
  autotune: false,
  autotune_tonic: "C",
  autotune_scale: "chromatic",
  autotune_strength: 1.0,
  stereo_sound: false,
  audio_upscaling: false,
  output_format: "mp3",
});

export const ttsForm = writable<TtsForm>({
  input_path: "",
  rvc_model: "",
  language: "",
  tts_voice: "",
  tts_text: "",
  tts_rate: 0,
  tts_volume: 0,
  tts_pitch: 0,
  f0_method: "rmvpe",
  f0_min: 50,
  f0_max: 1100,
  rvc_pitch: 0,
  protect: 0.5,
  index_rate: 0,
  volume_envelope: 1,
  autopitch: false,
  autopitch_threshold: 155,
  autotune: false,
  autotune_tonic: "C",
  autotune_scale: "chromatic",
  autotune_strength: 1.0,
  stereo_sound: false,
  audio_upscaling: false,
  output_format: "mp3",
});

export const uvrForm = writable<UvrForm>({
  audio_path: "",
  arch: "roformer",
  model_key: "",
  model_dir: "models/UVR_models",
  output_dir: "output/UVR_output",
  output_format: "wav",
  rename_template: "NAME_(STEM)_MODEL",
  norm_threshold: 0.9,
  amp_threshold: 0.0,
  batch_size: 1,
  segment_size: 256,
  override_segment_size: false,
  overlap: 8,
  pitch_shift: 0,
  hop_length: 1024,
  denoise: false,
  window_size: 512,
  aggression: 5,
  enable_tta: false,
  enable_post_process: false,
  post_process_threshold: 0.2,
  high_end_process: false,
  shifts: 2,
  segments_enabled: true,
});

export const installUrlForm = writable<InstallUrlForm>({
  url: "",
  model_name: "",
});

export const installZipForm = writable<InstallZipForm>({
  zip_path: "",
  model_name: "",
});

export const installFilesForm = writable<InstallFilesForm>({
  pth_path: "",
  index_path: "",
  model_name: "",
});