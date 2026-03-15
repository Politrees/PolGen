export interface JobSnapshot {
  job_id: string;
  status: "queued" | "running" | "done" | "error";
  progress: number;
  message: string;
  result?: Record<string, any> | null;
  error?: string | null;
}

export type TabKey = "rvc" | "tts" | "models";

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