<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { appWindow } from "@tauri-apps/api/window";

  const dispatch = createEventDispatcher();

  async function onMouseDown(ev: MouseEvent) {
    if (ev.button !== 0) return;
    if ((ev.target as HTMLElement).closest("button")) return;
    try {
      await appWindow.startDragging();
    } catch {}
  }
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="setup-titlebar" on:mousedown={onMouseDown}>
  <span>PolGen — Установка</span>
  <button class="setup-close" on:click={() => dispatch("close")}>✖</button>
</div>