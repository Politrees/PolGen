<script lang="ts">
  import { invoke } from "@tauri-apps/api/tauri";
  import { appWindow, WebviewWindow } from "@tauri-apps/api/window";
  import { envStatus, appendLog } from "./state";
  import type { EnvStatus } from "./types";

  let launching = false;
  let error = "";

  async function launch() {
    if (launching) return;
    launching = true;
    error = "";

    // Проверяем окружение
    try {
      const env = await invoke<EnvStatus>("check_env_ready");
      envStatus.set(env);
      if (!env.ready) {
        error = "Окружение не готово. Попробуйте повторить установку.";
        launching = false;
        return;
      }
    } catch (e) {
      error = `Ошибка проверки: ${e}`;
      launching = false;
      return;
    }

    appendLog("Открытие приложения...");

    // Показываем главное окно — оно само запустит backend
    try {
      const mainWin = WebviewWindow.getByLabel("main");
      if (mainWin) {
        await mainWin.show();
        await mainWin.setFocus();
      }
    } catch (e) {
      appendLog(`show main: ${e}`);
    }

    await new Promise((r) => setTimeout(r, 500));
    await appWindow.close();
  }
</script>

<div class="setup-step done-step">
  <div class="done-icon">🎉</div>
  <h2>Всё готово!</h2>
  <p class="mode-desc">
    PolGen установлен и готов к использованию.
  </p>

  {#if error}
    <div class="setup-warn">{error}</div>
  {/if}

  <button class="setup-btn" disabled={launching} on:click={launch}>
    {#if launching}
      ⏳ Запуск...
    {:else}
      🚀 Запустить PolGen
    {/if}
  </button>
</div>