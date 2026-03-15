import { writable } from "svelte/store";
import type { EnvStatus, PlatformInfo, SetupStep, InstallMode } from "./types";

export const envStatus = writable<EnvStatus | null>(null);
export const platform = writable<PlatformInfo | null>(null);
export const currentStep = writable<SetupStep>("check");
export const installMode = writable<InstallMode>("download");
export const selectedUrl = writable("");
export const isRunning = writable(false);
export const installProgress = writable(0);
export const installMessage = writable("");
export const installLogs = writable<string[]>([]);
export const installSuccess = writable<boolean | null>(null);

export function appendLog(line: string) {
  installLogs.update((lines) => {
    const next = [...lines, line];
    return next.length > 3000 ? next.slice(next.length - 3000) : next;
  });
}

export function clearLogs() {
  installLogs.set([]);
}