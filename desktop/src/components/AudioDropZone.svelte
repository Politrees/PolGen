<script lang="ts">
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import { listen, type UnlistenFn } from "@tauri-apps/api/event";
  import { open as openDialog } from "@tauri-apps/api/dialog";
  import { basename } from "$lib/utils";

  export let value: string = "";
  export let extensions: string[] = ["mp3", "wav", "flac", "ogg", "m4a"];
  export let placeholder: string = "Перетащите аудиофайл сюда или нажмите для выбора";

  const dispatch = createEventDispatcher<{ change: string }>();

  let dragOver = false;
  let listeners: UnlistenFn[] = [];
  let pulseAnim = false;

  $: hasFile = value.trim().length > 0;
  $: displayName = hasFile ? basename(value) : "";

  onMount(async () => {
    listeners.push(
      await listen<string[]>("tauri://file-drop-hover", () => {
        dragOver = true;
      })
    );

    listeners.push(
      await listen<string[]>("tauri://file-drop", (event) => {
        dragOver = false;
        const files = event.payload as string[];
        if (files.length > 0) {
          const file = files[0];
          const ext = file.split(".").pop()?.toLowerCase() ?? "";
          if (extensions.includes(ext)) {
            setValue(file);
          }
        }
      })
    );

    listeners.push(
      await listen("tauri://file-drop-cancelled", () => {
        dragOver = false;
      })
    );
  });

  onDestroy(() => {
    for (const un of listeners) un();
  });

  function setValue(path: string) {
    value = path;
    dispatch("change", path);

    // Короткая анимация подтверждения
    pulseAnim = true;
    setTimeout(() => (pulseAnim = false), 600);
  }

  async function pickFile() {
    const sel = await openDialog({
      multiple: false,
      filters: [{ name: "Audio", extensions }],
    });
    if (typeof sel === "string") {
      setValue(sel);
    }
  }

  function clear(e: MouseEvent) {
    e.stopPropagation();
    value = "";
    dispatch("change", "");
  }
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<!-- svelte-ignore a11y-click-events-have-key-events -->
<div
  class="dropzone"
  class:dropzone-hover={dragOver}
  class:dropzone-filled={hasFile}
  class:dropzone-pulse={pulseAnim}
  on:click={pickFile}
>
  {#if hasFile}
    <div class="dropzone-file">
      <div class="dropzone-icon">🎵</div>
      <div class="dropzone-info">
        <span class="dropzone-name" title={value}>{displayName}</span>
        <span class="dropzone-path" title={value}>{value}</span>
      </div>
      <button class="dropzone-clear" title="Очистить" on:click={clear}>✕</button>
    </div>
  {:else}
    <div class="dropzone-empty">
      <div class="dropzone-icon-large">
        {#if dragOver}
          <span class="drop-arrow">⬇</span>
        {:else}
          <span>📂</span>
        {/if}
      </div>
      <span class="dropzone-label">{placeholder}</span>
      <span class="dropzone-hint">
        {extensions.map(e => `.${e}`).join(", ")}
      </span>
    </div>
  {/if}
</div>

<style>
  .dropzone {
    position: relative;
    border: 2px dashed rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    padding: 20px;
    cursor: pointer;
    transition: all 0.3s ease;
    background: rgba(0, 0, 0, 0.15);
    overflow: hidden;
  }

  .dropzone::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: 12px;
    opacity: 0;
    background: linear-gradient(135deg, rgba(35, 134, 54, 0.08), rgba(56, 139, 253, 0.05));
    transition: opacity 0.3s ease;
    pointer-events: none;
  }

  .dropzone:hover {
    border-color: rgba(35, 134, 54, 0.3);
    background: rgba(0, 0, 0, 0.2);
  }

  .dropzone:hover::before {
    opacity: 1;
  }

  /* Drag hover */
  .dropzone-hover {
    border-color: var(--accent) !important;
    background: rgba(35, 134, 54, 0.08) !important;
    box-shadow: 0 0 24px rgba(35, 134, 54, 0.15);
    transform: scale(1.01);
  }

  .dropzone-hover::before {
    opacity: 1 !important;
    background: linear-gradient(135deg, rgba(35, 134, 54, 0.15), rgba(56, 139, 253, 0.1)) !important;
  }

  /* File selected */
  .dropzone-filled {
    border-style: solid;
    border-color: rgba(35, 134, 54, 0.25);
    padding: 14px 16px;
    background: rgba(35, 134, 54, 0.04);
  }

  /* Pulse animation on file select */
  .dropzone-pulse {
    animation: dropzone-confirm 0.6s ease;
  }

  @keyframes dropzone-confirm {
    0% { box-shadow: 0 0 0 0 rgba(35, 134, 54, 0.4); }
    50% { box-shadow: 0 0 0 8px rgba(35, 134, 54, 0); }
    100% { box-shadow: none; }
  }

  /* Empty state */
  .dropzone-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 8px 0;
  }

  .dropzone-icon-large {
    font-size: 28px;
    line-height: 1;
    transition: transform 0.3s ease;
  }

  .dropzone:hover .dropzone-icon-large {
    transform: translateY(-2px);
  }

  .dropzone-hover .dropzone-icon-large {
    transform: translateY(-4px) scale(1.15);
  }

  .drop-arrow {
    display: inline-block;
    animation: drop-bounce 0.6s ease-in-out infinite alternate;
  }

  @keyframes drop-bounce {
    from { transform: translateY(-4px); }
    to { transform: translateY(2px); }
  }

  .dropzone-label {
    font-size: 13px;
    color: var(--text-muted);
    font-weight: 500;
    text-align: center;
  }

  .dropzone-hint {
    font-size: 11px;
    color: rgba(139, 148, 158, 0.6);
  }

  /* File info */
  .dropzone-file {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .dropzone-icon {
    font-size: 22px;
    flex-shrink: 0;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(35, 134, 54, 0.1);
    border-radius: 8px;
  }

  .dropzone-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .dropzone-name {
    font-size: 13px;
    font-weight: 600;
    color: #fff;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dropzone-path {
    font-size: 10px;
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }

  .dropzone-clear {
    all: unset;
    cursor: pointer;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    color: var(--text-muted);
    font-size: 12px;
    flex-shrink: 0;
    transition: all 0.15s ease;
  }

  .dropzone-clear:hover {
    background: rgba(248, 81, 73, 0.15);
    color: var(--danger);
  }
</style>