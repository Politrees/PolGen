<script lang="ts">
  import { uvrForm, uvrModels, uvrFormats, uvrStems, toasts } from "$lib/state";
  import { postJob, loadUvrModels, clearUvrModels } from "$lib/api";
  import { UVR_ARCHS } from "$lib/types";
  import type { UvrArch } from "$lib/types";
  import AudioDropZone from "../components/AudioDropZone.svelte";
  import StemPlayer from "../components/StemPlayer.svelte";
  import Accordion from "../components/Accordion.svelte";
  import Slider from "../components/Slider.svelte";
  import Field from "../components/Field.svelte";

  $: archModels = $uvrModels[$uvrForm.arch] ?? [];
  $: formats = $uvrFormats;
  $: stems = $uvrStems;

  function setArch(arch: UvrArch) {
    $uvrForm.arch = arch;
    const models = $uvrModels[arch] ?? [];
    if (models.length && !models.includes($uvrForm.model_key)) {
      $uvrForm.model_key = models[0];
    }
    if (arch === "roformer" || arch === "mdx23c") {
      $uvrForm.segment_size = 256;
      $uvrForm.overlap = 8;
    } else if (arch === "mdx") {
      $uvrForm.segment_size = 256;
      $uvrForm.overlap = 0.25;
    } else if (arch === "vr") {
      $uvrForm.window_size = 512;
      $uvrForm.aggression = 5;
    } else if (arch === "demucs") {
      $uvrForm.segment_size = 40;
      $uvrForm.overlap = 0.25;
      $uvrForm.shifts = 2;
    }
  }

  async function refreshModels() {
    await loadUvrModels();
    toasts.show("Список UVR моделей обновлён");
  }

  async function onClearModels() {
    await clearUvrModels($uvrForm.model_dir);
  }

  async function separate() {
    if (!$uvrForm.audio_path.trim()) {
      toasts.show("Выберите входной аудио-файл");
      return;
    }
    if (!$uvrForm.model_key.trim()) {
      toasts.show("Выберите модель");
      return;
    }
    await postJob("/jobs/uvr_separate", $uvrForm);
  }
</script>

<div class="card">
  <h2>UVR • Разделение аудио</h2>

  <!-- Архитектура -->
  <div class="arch-tabs">
    {#each UVR_ARCHS as { key, label }}
      <button
        class="arch-tab"
        class:active={$uvrForm.arch === key}
        on:click={() => setArch(key)}
      >
        {label}
      </button>
    {/each}
  </div>

  <!-- Модель -->
  <Field label="Модель">
    <div class="model-select-row">
      <select bind:value={$uvrForm.model_key} disabled={!archModels.length}>
        {#if !archModels.length}
          <option value="">(загрузка...)</option>
        {:else}
          {#each archModels as m}
            <option value={m}>{m}</option>
          {/each}
        {/if}
      </select>
      <button class="refresh-btn" title="Обновить модели" on:click={refreshModels}>⟳</button>
    </div>
  </Field>

  <!-- Входной файл -->
  <AudioDropZone
    bind:value={$uvrForm.audio_path}
    extensions={["mp3", "wav", "flac", "ogg", "m4a", "aac", "wma"]}
    placeholder="Перетащите аудиофайл или нажмите для выбора"
  />

  <!-- Формат -->
  <Field label="Формат выхода">
    <select bind:value={$uvrForm.output_format}>
      {#each formats as fmt}
        <option value={fmt}>{fmt}</option>
      {/each}
    </select>
  </Field>

  <!-- Параметры сепарации -->
  <Accordion title="Параметры сепарации">
    {#if $uvrForm.arch === "roformer" || $uvrForm.arch === "mdx23c"}
      <label class="checkbox-wrap">
        <input type="checkbox" bind:checked={$uvrForm.override_segment_size} />
        <span>Override Segment Size</span>
      </label>
      {#if $uvrForm.override_segment_size}
        <Slider label="Segment Size" bind:value={$uvrForm.segment_size} min={32} max={4000} step={32} />
      {/if}
      <Slider label="Overlap" bind:value={$uvrForm.overlap} min={2} max={10} step={1} />
      <Slider label="Pitch Shift" bind:value={$uvrForm.pitch_shift} min={-24} max={24} step={1} />
      <Slider label="Batch Size" bind:value={$uvrForm.batch_size} min={1} max={16} step={1} />

    {:else if $uvrForm.arch === "mdx"}
      <label class="checkbox-wrap">
        <input type="checkbox" bind:checked={$uvrForm.denoise} />
        <span>Denoise</span>
      </label>
      <Slider label="Hop Length" bind:value={$uvrForm.hop_length} min={32} max={2048} step={32} />
      <Slider label="Segment Size" bind:value={$uvrForm.segment_size} min={32} max={4000} step={32} />
      <Slider label="Overlap" bind:value={$uvrForm.overlap} min={0.001} max={0.999} step={0.001} />
      <Slider label="Batch Size" bind:value={$uvrForm.batch_size} min={1} max={16} step={1} />

    {:else if $uvrForm.arch === "vr"}
      <label class="checkbox-wrap">
        <input type="checkbox" bind:checked={$uvrForm.enable_post_process} />
        <span>Post-Process</span>
      </label>
      {#if $uvrForm.enable_post_process}
        <Slider label="Post-Process Threshold" bind:value={$uvrForm.post_process_threshold} min={0.1} max={0.3} step={0.1} />
      {/if}
      <label class="checkbox-wrap">
        <input type="checkbox" bind:checked={$uvrForm.enable_tta} />
        <span>TTA (Test-Time Augmentation)</span>
      </label>
      <label class="checkbox-wrap">
        <input type="checkbox" bind:checked={$uvrForm.high_end_process} />
        <span>High-End Process</span>
      </label>
      <Slider label="Window Size" bind:value={$uvrForm.window_size} min={320} max={1024} step={32} />
      <Slider label="Aggression" bind:value={$uvrForm.aggression} min={1} max={100} step={1} />
      <Slider label="Batch Size" bind:value={$uvrForm.batch_size} min={1} max={16} step={1} />

    {:else if $uvrForm.arch === "demucs"}
      <label class="checkbox-wrap">
        <input type="checkbox" bind:checked={$uvrForm.segments_enabled} />
        <span>Segment Processing</span>
      </label>
      <Slider label="Segment Size" bind:value={$uvrForm.segment_size} min={1} max={100} step={1} />
      <Slider label="Overlap" bind:value={$uvrForm.overlap} min={0.001} max={0.999} step={0.001} />
      <Slider label="Shifts" bind:value={$uvrForm.shifts} min={0} max={20} step={1} />
    {/if}

    <div class="hr" />
    <Slider label="Normalization" bind:value={$uvrForm.norm_threshold} min={0.1} max={1} step={0.1} />
    <Slider label="Amplification" bind:value={$uvrForm.amp_threshold} min={0.0} max={1} step={0.1} />
  </Accordion>

  <!-- Настройки -->
  <Accordion title="Настройки">
    <Field label="Директория моделей">
      <input type="text" bind:value={$uvrForm.model_dir} placeholder="models/UVR_models" />
    </Field>
    <Field label="Директория выхода">
      <input type="text" bind:value={$uvrForm.output_dir} placeholder="output/UVR_output" />
    </Field>
    <Field label="Шаблон имён">
      <input type="text" bind:value={$uvrForm.rename_template} placeholder="NAME_(STEM)_MODEL" />
    </Field>
    <div class="text-muted">Ключи: NAME — файл, STEM — тип стема, MODEL — модель</div>
    <button class="btn" on:click={onClearModels}>🗑 Очистить скачанные модели</button>
  </Accordion>

  <!-- Кнопка -->
  <button class="btn primary" on:click={separate}>Разделить аудио</button>

  <!-- Результаты -->
  {#if stems.length > 0}
    <div class="hr" />
    <div class="stems-header">
      <h2>Результат</h2>
      <span class="stems-count">{stems.length} {stems.length === 1 ? "стем" : stems.length < 5 ? "стема" : "стемов"}</span>
    </div>
    <div class="stems-grid">
      {#each stems as stem (stem)}
        <StemPlayer path={stem} />
      {/each}
    </div>
  {/if}
</div>

<style>
  .arch-tabs {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }

  .arch-tab {
    all: unset;
    cursor: pointer;
    flex: 1;
    min-width: 80px;
    text-align: center;
    padding: 9px 8px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border);
    transition: all 0.2s ease;
  }

  .arch-tab:hover {
    background: rgba(255, 255, 255, 0.06);
    color: #fff;
    border-color: rgba(255, 255, 255, 0.12);
  }

  .arch-tab.active {
    background: rgba(35, 134, 54, 0.12);
    border-color: rgba(35, 134, 54, 0.3);
    color: var(--accent-text);
    box-shadow: inset 0 -2px 0 var(--accent);
  }

  .stems-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .stems-count {
    font-size: 11px;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.04);
    padding: 3px 10px;
    border-radius: 20px;
    border: 1px solid var(--border);
  }

  .stems-grid {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
</style>