export interface EnvStatus {
  ready: boolean;
  python_found: boolean;
  env_exists: boolean;
  project_root: string | null;
}

export interface EnvVariant {
  label: string;
  url: string;
  description: string;
}

export interface PlatformInfo {
  os: string;
  has_nvidia: boolean;
  gpu_name: string;
  gpu_vram_mb: number;
  gpu_cuda_capable: boolean;
  cuda_reason: string;
  recommended_url: string;
  all_variants: EnvVariant[];
}

export interface DownloadProgressEvent {
  downloaded_mb: number;
  total_mb: number;
  percent: number;
  speed_mbps: number;
  eta_seconds: number;
  message: string;
}

export type InstallMode = "download" | "conda";

export type SetupStep = "check" | "configure" | "install" | "done";