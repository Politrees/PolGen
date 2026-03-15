<script lang="ts">
  import { convertFileSrc } from "@tauri-apps/api/tauri";
  import { playerPath, logs } from "$lib/state";
  import { openFilePath, openOutputDir } from "$lib/api";
  import { basename, formatTime } from "$lib/utils";

  let audio: HTMLAudioElement;
  let playing = false;
  let currentTime = 0;
  let duration = 0;
  let volume = 1;
  let seeking = false;
  let audioSrc = "";

  $: enabled = !!$playerPath;
  $: filename = $playerPath ? basename($playerPath) : "Нет аудио";
  $: title = $playerPath ?? "";
  $: progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  $: if ($playerPath) {
    loadAudio($playerPath);
  }

  function loadAudio(path: string) {
    playing = false;
    currentTime = 0;
    duration = 0;
    try {
      audioSrc = convertFileSrc(path) + "?t=" + Date.now();
    } catch (e) {
      logs.append(`[Player] convertFileSrc: ${e}`);
      audioSrc = "";
    }
  }

  function toggle() {
    if (!audio || !enabled) return;
    if (audio.paused) {
      audio.play().catch(() => {});
      playing = true;
    } else {
      audio.pause();
      playing = false;
    }
  }

  function onTimeUpdate() {
    if (!seeking) currentTime = audio?.currentTime ?? 0;
  }

  function onLoadedMetadata() {
    duration = audio?.duration ?? 0;
  }

  function onEnded() {
    playing = false;
  }

  function onError() {
    logs.append("[Player] Ошибка воспроизведения");
  }

  function onSeekInput(e: Event) {
    const val = parseFloat((e.target as HTMLInputElement).value);
    if (audio) audio.currentTime = val;
    currentTime = val;
  }

  function onVolumeInput(e: Event) {
    volume = parseFloat((e.target as HTMLInputElement).value);
    if (audio) audio.volume = volume;
  }

  $: volumeIcon = volume === 0 ? "🔇" : volume < 0.5 ? "🔉" : "🔊";
  $: volumePct = `${Math.round(volume * 100)}%`;
</script>

<div class="player" class:player-active={enabled} class:player-playing={playing}>
  {#if audioSrc}
    <audio
      bind:this={audio}
      src={audioSrc}
      preload="metadata"
      on:timeupdate={onTimeUpdate}
      on:loadedmetadata={onLoadedMetadata}
      on:ended={onEnded}
      on:error={onError}
    />
  {/if}

  <!-- Верхняя строка: управление воспроизведением -->
  <div class="player-controls">
    <button class="player-play" disabled={!enabled} on:click={toggle}>
      {#if playing}
        <span class="pause-icon">⏸</span>
      {:else}
        <span class="play-icon">▶</span>
      {/if}
    </button>

    <span class="player-time">{formatTime(currentTime)}</span>

    <div class="player-seek-wrap">
      <input
        type="range"
        class="player-seek"
        min="0"
        max={duration || 100}
        step="0.1"
        value={currentTime}
        disabled={!enabled}
        style="--progress: {progress}%"
        on:mousedown={() => (seeking = true)}
        on:touchstart={() => (seeking = true)}
        on:mouseup={() => (seeking = false)}
        on:touchend={() => (seeking = false)}
        on:input={onSeekInput}
      />
    </div>

    <span class="player-time">{formatTime(duration)}</span>

    <div class="player-volume">
      <span class="volume-icon">{volumeIcon}</span>
      <input
        type="range"
        class="volume-slider"
        min="0"
        max="1"
        step="0.01"
        value={volume}
        style="--vol-pct: {volumePct}"
        on:input={onVolumeInput}
      />
    </div>
  </div>

  <!-- Нижняя строка: инфо и действия -->
  <div class="player-info">
    <div class="player-track">
      {#if playing}
        <div class="eq-bars">
          <span /><span /><span /><span />
        </div>
      {/if}
      <span class="player-filename" {title}>{filename}</span>
    </div>

    <div class="player-actions">
      <button
        class="player-action"
        title="Открыть файл"
        disabled={!enabled}
        on:click={() => $playerPath && openFilePath($playerPath)}
      >
        📄 Файл
      </button>
      <button
        class="player-action"
        title="Открыть папку"
        on:click={openOutputDir}
      >
        📁 Папка
      </button>
    </div>
  </div>
</div>

<style>
  .player {
    flex-shrink: 0;
    border-top: 1px solid var(--border);
    background: rgba(13, 17, 23, 0.95);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    padding: 10px 20px 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    opacity: 0.4;
    transition: all 0.35s ease;
    position: relative;
    overflow: hidden;
  }

  .player audio { display: none; }

  .player-active {
    opacity: 1;
    border-top-color: rgba(35, 134, 54, 0.25);
  }

  .player-active::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, var(--accent) 30%, var(--accent-hover) 50%, var(--accent) 70%, transparent 100%);
    opacity: 0.6;
  }

  .player-playing::before {
    height: 2px;
    opacity: 1;
    animation: player-glow 2s ease-in-out infinite;
  }

  @keyframes player-glow {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
  }

  .player-controls {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .player-play {
    all: unset;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 38px; height: 38px;
    border-radius: 50%;
    background: var(--accent);
    color: #fff;
    font-size: 15px;
    flex-shrink: 0;
    transition: all 0.2s ease;
  }
  .player-play:hover:not(:disabled) {
    background: var(--accent-hover);
    box-shadow: 0 0 16px rgba(35, 134, 54, 0.4);
    transform: scale(1.08);
  }
  .player-play:active:not(:disabled) { transform: scale(0.95); }
  .player-play:disabled {
    background: #161b22;
    cursor: default;
    color: var(--text-muted);
  }

  .play-icon, .pause-icon {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .player-time {
    font-size: 11px;
    font-family: ui-monospace, SFMono-Regular, monospace;
    color: var(--text-muted);
    min-width: 38px;
    text-align: center;
    flex-shrink: 0;
  }

  .player-seek-wrap {
    flex: 1;
    display: flex;
    align-items: center;
    min-width: 0;
  }

  .player-seek {
    width: 100%;
    height: 6px;
    -webkit-appearance: none;
    appearance: none;
    border-radius: 3px;
    outline: none;
    cursor: pointer;
    background: linear-gradient(
      to right,
      var(--accent) 0%, var(--accent) var(--progress, 0%),
      #161b22 var(--progress, 0%), #161b22 100%
    );
    transition: height 0.15s ease;
  }
  .player-seek:hover { height: 8px; }
  .player-seek::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 14px; height: 14px;
    border-radius: 50%;
    background: #fff;
    border: 2px solid var(--accent);
    cursor: pointer;
    transition: all 0.15s ease;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
  }
  .player-seek::-webkit-slider-thumb:hover {
    background: var(--accent-text);
    box-shadow: 0 0 10px rgba(35, 134, 54, 0.4);
    transform: scale(1.2);
  }
  .player-seek:disabled { cursor: default; opacity: 0.3; }
  .player-seek:disabled::-webkit-slider-thumb {
    background: #30363d;
    border-color: #30363d;
    cursor: default;
    transform: none;
  }

  /* Volume */
  .player-volume {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .volume-icon {
    font-size: 14px;
    cursor: default;
    min-width: 18px;
    text-align: center;
  }

  .volume-slider {
    width: 70px;
    height: 4px;
    -webkit-appearance: none;
    appearance: none;
    border-radius: 2px;
    outline: none;
    cursor: pointer;
    background: linear-gradient(
      to right,
      var(--text-muted) 0%, var(--text-muted) var(--vol-pct, 100%),
      #161b22 var(--vol-pct, 100%), #161b22 100%
    );
  }
  .volume-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 10px; height: 10px;
    border-radius: 50%;
    background: #fff;
    border: 1px solid var(--text-muted);
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .volume-slider::-webkit-slider-thumb:hover {
    transform: scale(1.2);
  }

  /* Bottom row */
  .player-info {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 24px;
  }

  .player-track {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    flex: 1;
  }

  .player-filename {
    font-size: 13px;
    color: var(--text);
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }

  .player-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }

  .player-action {
    all: unset;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border-radius: 6px;
    color: var(--text-muted);
    font-size: 11px;
    font-weight: 500;
    transition: all 0.15s ease;
    border: 1px solid transparent;
  }
  .player-action:hover {
    background: rgba(255, 255, 255, 0.06);
    color: #fff;
    border-color: var(--border);
  }
  .player-action:disabled {
    opacity: 0.3;
    cursor: default;
    pointer-events: none;
  }

  /* EQ bars */
  .eq-bars {
    display: flex;
    align-items: flex-end;
    gap: 2px;
    height: 14px;
    flex-shrink: 0;
  }

  .eq-bars span {
    display: block;
    width: 3px;
    border-radius: 1px;
    background: var(--accent-text);
  }

  .eq-bars span:nth-child(1) { animation: eq-bounce 0.45s ease-in-out infinite alternate; height: 6px; }
  .eq-bars span:nth-child(2) { animation: eq-bounce 0.55s ease-in-out infinite alternate; animation-delay: 0.1s; height: 10px; }
  .eq-bars span:nth-child(3) { animation: eq-bounce 0.4s ease-in-out infinite alternate; animation-delay: 0.2s; height: 8px; }
  .eq-bars span:nth-child(4) { animation: eq-bounce 0.5s ease-in-out infinite alternate; animation-delay: 0.15s; height: 5px; }

  @keyframes eq-bounce {
    0% { height: 3px; }
    100% { height: 14px; }
  }
</style>