export interface JobSnapshot {
  job_id: string;
  status: "queued" | "running" | "done" | "error";
  progress: number;
  message: string;
  result?: Record<string, any> | null;
  error?: string | null;
}

export type TabKey = "rvc" | "tts" | "uvr" | "models";

export interface RvcForm {
  input_path: string;
  rvc_model: string;
  f0_method: string;
  f0_min: number;
  f0_max: number;
  rvc_pitch: number;
  protect: number;
  index_rate: number;
  volume_envelope: number;
  autopitch: boolean;
  autopitch_threshold: number;
  autotune: boolean;
  autotune_tonic: string;
  autotune_scale: string;
  autotune_strength: number;
  stereo_sound: boolean;
  audio_upscaling: boolean;
  output_format: string;
}

export interface TtsForm extends RvcForm {
  language: string;
  tts_voice: string;
  tts_text: string;
  tts_rate: number;
  tts_volume: number;
  tts_pitch: number;
}

export type UvrArch = "roformer" | "mdx23c" | "mdx" | "vr" | "demucs";

export interface UvrForm {
  audio_path: string;
  arch: UvrArch;
  model_key: string;
  model_dir: string;
  output_dir: string;
  output_format: string;
  rename_template: string;

  // Common
  norm_threshold: number;
  amp_threshold: number;
  batch_size: number;

  // Roformer / MDX23C
  segment_size: number;
  override_segment_size: boolean;
  overlap: number;
  pitch_shift: number;

  // MDX-NET
  hop_length: number;
  denoise: boolean;

  // VR ARCH
  window_size: number;
  aggression: number;
  enable_tta: boolean;
  enable_post_process: boolean;
  post_process_threshold: number;
  high_end_process: boolean;

  // Demucs
  shifts: number;
  segments_enabled: boolean;
}

export interface InstallUrlForm {
  url: string;
  model_name: string;
}

export interface InstallZipForm {
  zip_path: string;
  model_name: string;
}

export interface InstallFilesForm {
  pth_path: string;
  index_path: string;
  model_name: string;
}

export interface ToastItem {
  id: number;
  message: string;
}

export const F0_METHODS = ["rmvpe+", "rmvpe", "fcpe", "crepe", "crepe-tiny"];
export const OUTPUT_FORMATS = ["wav", "flac", "mp3", "ogg", "m4a"];
export const TONIC_NOTES = [
  "C", "C#", "Db", "D", "D#", "Eb", "E", "F",
  "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B",
];
export const SCALES = [
  "chromatic", "major", "minor", "dorian", "phrygian", "lydian",
  "mixolydian", "harmonic_minor", "melodic_minor",
  "pentatonic_major", "pentatonic_minor", "blues",
];

export const UVR_ARCHS: { key: UvrArch; label: string }[] = [
  { key: "roformer", label: "Roformer" },
  { key: "mdx23c", label: "MDX23C" },
  { key: "mdx", label: "MDX-NET" },
  { key: "vr", label: "VR ARCH" },
  { key: "demucs", label: "Demucs" },
];