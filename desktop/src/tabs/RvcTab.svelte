<script lang="ts">
  import { open as openDialog } from "@tauri-apps/api/dialog";
  import { rvcForm } from "$lib/state";
  import { postJob } from "$lib/api";
  import { toasts } from "$lib/state";
  import { OUTPUT_FORMATS } from "$lib/types";
  import ModelSelect from "../components/ModelSelect.svelte";
  import PitchBlock from "../components/PitchBlock.svelte";
  import ConversionSettings from "../components/ConversionSettings.svelte";
  import Field from "../components/Field.svelte";

  async function pickFile() {
    const sel = await openDialog({
      multiple: false,
      filters: [{ name: "Audio", extensions: ["mp3", "wav", "flac", "ogg", "m4a"] }],
    });
    if (typeof sel === "string") {
      $rvcForm.input_path = sel;
    }
  }

  async function generate() {
    if (!$rvcForm.input_path.trim()) { toasts.show("Выберите входной аудио-файл"); return; }
    if (!$rvcForm.rvc_model.trim()) { toasts.show("Выберите RVC модель"); return; }
    await postJob("/jobs/convert", $rvcForm);
  }
</script>

<div class="card">
  <h2>RVC • Конвертация</h2>

  <Field label="Входной файл">
    <div class="row">
      <input type="text" bind:value={$rvcForm.input_path} placeholder="Путь к аудио…" />
      <button class="btn" on:click={pickFile}>Выбрать</button>
    </div>
  </Field>

  <ModelSelect bind:value={$rvcForm.rvc_model} />

  <PitchBlock
    bind:autopitch={$rvcForm.autopitch}
    bind:autopitch_threshold={$rvcForm.autopitch_threshold}
    bind:rvc_pitch={$rvcForm.rvc_pitch}
  />

  <Field label="Формат выхода">
    <select bind:value={$rvcForm.output_format}>
      {#each OUTPUT_FORMATS as fmt}
        <option value={fmt}>{fmt}</option>
      {/each}
    </select>
  </Field>

  <ConversionSettings
    bind:f0_method={$rvcForm.f0_method}
    bind:index_rate={$rvcForm.index_rate}
    bind:volume_envelope={$rvcForm.volume_envelope}
    bind:protect={$rvcForm.protect}
    bind:stereo_sound={$rvcForm.stereo_sound}
    bind:audio_upscaling={$rvcForm.audio_upscaling}
    bind:autotune={$rvcForm.autotune}
    bind:autotune_tonic={$rvcForm.autotune_tonic}
    bind:autotune_scale={$rvcForm.autotune_scale}
    bind:autotune_strength={$rvcForm.autotune_strength}
    bind:f0_min={$rvcForm.f0_min}
    bind:f0_max={$rvcForm.f0_max}
  />

  <button class="btn primary" on:click={generate}>Генерировать</button>
</div>