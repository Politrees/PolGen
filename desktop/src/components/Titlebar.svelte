<script lang="ts">
  import { appWindow } from "@tauri-apps/api/window";
  import { activeTab } from "$lib/state";

  const titles: Record<string, string> = {
    rvc: "RVC • Конвертация аудио",
    tts: "TTS → RVC • Синтез и конвертация",
    models: "Модели • Установка / Удаление",
  };

  async function onMouseDown(ev: MouseEvent) {
    if (ev.button !== 0) return;
    const target = ev.target as HTMLElement;
    if (target.closest("button, input, select, textarea")) return;
    try {
      await appWindow.startDragging();
    } catch {}
  }
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="titlebar" on:mousedown={onMouseDown}>
  <h1>{titles[$activeTab] ?? "PolGen Desktop"}</h1>
  <div class="spacer" />
  <div class="windowBtns">
    <button class="winBtn" on:click={() => appWindow.minimize()}>━</button>
    <button class="winBtn" on:click={() => appWindow.toggleMaximize()}>🗖</button>
    <button class="winBtn close" on:click={() => appWindow.close()}>✖</button>
  </div>
</div>