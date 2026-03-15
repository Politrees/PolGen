<script lang="ts">
  import { convertFileSrc } from "@tauri-apps/api/tauri";
  import { openFilePath } from "$lib/api";
  import { basename, formatTime } from "$lib/utils";
  import { logs } from "$lib/state";

  export let path: string;

  let audio: HTMLAudioElement;
  let playing = false;
  let currentTime = 0;
  let duration = 0;
  let audioSrc = "";
  let loaded = false;

  $: name = basename(path);
  $: progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  $: if (path) {
    try {
      audioSrc = convertFileSrc(path) + "?t=" + Date.now();
      loaded = false;
      playing = false;
      currentTime = 0;
      duration = 0;
    } catch (e) {
      logs.append(`[StemPlayer] ${e}`);
      audioSrc = "";
    }
  }

  function toggle() {
    if (!audio || !audioSrc) return;
    if (audio.paused) {
      audio.play().catch(() => {});
      playing = true;
    } else {
      audio.pause();
      playing = false;
    }
  }

  function onTimeUpdate() {
    currentTime = audio?.currentTime ?? 0;
  }

  function onLoadedMetadata() {
    duration = audio?.duration ?? 0;
    loaded = true;
  }

  function onEnded() {
    playing = false;
    currentTime = 0;
  }

  function onSeek(e: Event) {
    const val = parseFloat((e.target as HTMLInputElement).value);
    if (audio) audio.currentTime = val;
    currentTime = val;
  }
</script>

<div class="stem-player" class:stem-playing={playing}>
  {#if audioSrc}
    <audio
      bind:this={audio}
      src={audioSrc}
      preload="metadata"
      on:timeupdate={onTimeUpdate}
      on:loadedmetadata={onLoadedMetadata}
      on:ended={onEnded}
    />
  {/if}

  <div class="stem-top">
    <button class="stem-play-btn" on:click={toggle} disabled={!audioSrc}>
      {playing ? "⏸" : "▶"}
    </button>

    <div class="stem-info">
      <span class="stem-name" title={path}>{name}</span>
      <div class="stem-seek-row">
        <span class="stem-time">{formatTime(currentTime)}</span>
        <input
          type="range"
          class="stem-seek"
          min="0"
          max={duration || 100}
          step="0.1"
          value={currentTime}
          disabled={!loaded}
          style="--progress: {progress}%"
          on:input={onSeek}
        />
        <span class="stem-time">{formatTime(duration)}</span>
      </div>
    </div>

    <button
      class="stem-open-btn"
      title="Открыть файл"
      on:click={() => openFilePath(path)}
    >
      📄
    </button>
  </div>
</div>

<style>
  .stem-player {
    background: rgba(0, 0, 0, 0.25);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 14px;
    transition: all 0.25s ease;
  }

  .stem-player:hover {
    border-color: rgba(255, 255, 255, 0.12);
    background: rgba(0, 0, 0, 0.3);
  }

  .stem-playing {
    border-color: rgba(35, 134, 54, 0.25);
    box-shadow: 0 0 12px rgba(35, 134, 54, 0.08);
  }

  .stem-player audio {
    display: none;
  }

  .stem-top {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .stem-play-btn {
    all: unset;
    cursor: pointer;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--accent);
    color: #fff;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: all 0.2s ease;
  }

  .stem-play-btn:hover:not(:disabled) {
    background: var(--accent-hover);
    box-shadow: 0 0 12px rgba(35, 134, 54, 0.35);
    transform: scale(1.08);
  }

  .stem-play-btn:active:not(:disabled) {
    transform: scale(0.95);
  }

  .stem-play-btn:disabled {
    background: #161b22;
    color: var(--text-muted);
    cursor: default;
  }

  .stem-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .stem-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .stem-seek-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .stem-time {
    font-size: 10px;
    font-family: ui-monospace, SFMono-Regular, monospace;
    color: var(--text-muted);
    min-width: 30px;
    text-align: center;
    flex-shrink: 0;
  }

  .stem-seek {
    flex: 1;
    height: 4px;
    -webkit-appearance: none;
    appearance: none;
    border-radius: 2px;
    outline: none;
    cursor: pointer;
    background: linear-gradient(
      to right,
      var(--accent) 0%,
      var(--accent) var(--progress, 0%),
      #161b22 var(--progress, 0%),
      #161b22 100%
    );
  }

  .stem-seek::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #fff;
    border: 2px solid var(--accent);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .stem-seek::-webkit-slider-thumb:hover {
    transform: scale(1.2);
    box-shadow: 0 0 6px rgba(35, 134, 54, 0.4);
  }

  .stem-seek:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .stem-open-btn {
    all: unset;
    cursor: pointer;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    font-size: 13px;
    color: var(--text-muted);
    flex-shrink: 0;
    transition: all 0.15s ease;
  }

  .stem-open-btn:hover {
    background: rgba(255, 255, 255, 0.06);
    color: #fff;
  }
</style>