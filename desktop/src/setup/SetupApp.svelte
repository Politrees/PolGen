<script lang="ts">
  import { onMount } from "svelte";
  import { invoke } from "@tauri-apps/api/tauri";
  import { appWindow } from "@tauri-apps/api/window";
  import { currentStep, envStatus, platform, selectedUrl, appendLog } from "./state";
  import type { EnvStatus, PlatformInfo } from "./types";

  import SetupTitlebar from "./SetupTitlebar.svelte";
  import StepCheck from "./StepCheck.svelte";
  import StepConfigure from "./StepConfigure.svelte";
  import StepInstall from "./StepInstall.svelte";
  import StepDone from "./StepDone.svelte";

  const stepTitles: Record<string, string> = {
    check: "Проверка системы",
    configure: "Настройка",
    install: "Установка",
    done: "Готово",
  };

  $: stepIndex = ["check", "configure", "install", "done"].indexOf($currentStep);
  $: stepTitle = stepTitles[$currentStep] ?? "";

  onMount(async () => {
    // Загрузка данных о системе
    try {
      const env = await invoke<EnvStatus>("check_env_ready");
      envStatus.set(env);
    } catch {
      envStatus.set({ ready: false, python_found: false, env_exists: false, project_root: null });
    }

    try {
      const info = await invoke<PlatformInfo>("detect_platform");
      platform.set(info);
      if (info.recommended_url) selectedUrl.set(info.recommended_url);
    } catch {
      platform.set(null);
    }

    // Если уже установлено — сразу к завершению
    const env = $envStatus;
    if (env?.ready) {
      appendLog("Окружение уже установлено.");
      $currentStep = "done";
    }
  });

  async function closeApp() {
    try {
      await invoke("exit_app");
    } catch {
      await appWindow.close();
    }
  }
</script>

<SetupTitlebar on:close={closeApp} />

<div class="setup-card">
  <!-- Шаговый индикатор -->
  <div class="steps-indicator">
    {#each ["check", "configure", "install", "done"] as step, i}
      <div
        class="step-dot"
        class:active={i === stepIndex}
        class:completed={i < stepIndex}
      >
        {#if i < stepIndex}
          ✓
        {:else}
          {i + 1}
        {/if}
      </div>
      {#if i < 3}
        <div class="step-line" class:completed={i < stepIndex} />
      {/if}
    {/each}
  </div>
  <div class="step-title">{stepTitle}</div>

  <div class="hr" />

  <!-- Шаги -->
  {#if $currentStep === "check"}
    <StepCheck />
  {:else if $currentStep === "configure"}
    <StepConfigure />
  {:else if $currentStep === "install"}
    <StepInstall />
  {:else if $currentStep === "done"}
    <StepDone />
  {/if}
</div>