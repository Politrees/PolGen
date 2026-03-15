<script lang="ts">
  import { ttsForm, edgeVoices, toasts } from "$lib/state";
  import { postJob } from "$lib/api";
  import { OUTPUT_FORMATS } from "$lib/types";
  import ModelSelect from "../components/ModelSelect.svelte";
  import PitchBlock from "../components/PitchBlock.svelte";
  import ConversionSettings from "../components/ConversionSettings.svelte";
  import Slider from "../components/Slider.svelte";
  import Accordion from "../components/Accordion.svelte";
  import Field from "../components/Field.svelte";

  $: langs = Object.keys($edgeVoices);
  $: voices = $edgeVoices[$ttsForm.language] ?? [];

  function onLangChange() {
    const v = $edgeVoices[$ttsForm.language] ?? [];
    $ttsForm.tts_voice = v[0] ?? "";
  }

  async function generate() {
    if (!$ttsForm.tts_text.trim()) { toasts.show("Введите текст для синтеза"); return; }
    if (!$ttsForm.tts_voice.trim()) { toasts.show("Выберите голос TTS"); return; }
    if (!$ttsForm.rvc_model.trim()) { toasts.show("Выберите RVC модель"); return; }
    await postJob("/jobs/tts_convert", $ttsForm);
  }
</script>

<div class="card">
  <h2>TTS → RVC</h2>

  <ModelSelect bind:value={$ttsForm.rvc_model} />

  <Field label="Язык">
    <select bind:value={$ttsForm.language} on:change={onLangChange}>
      {#each langs as lang}
        <option value={lang}>{lang}</option>
      {/each}
    </select>
  </Field>

  <Field label="Голос TTS">
    <select bind:value={$ttsForm.tts_voice}>
      {#each voices as v}
        <option value={v}>{v}</option>
      {/each}
    </select>
  </Field>

  <Field label="Текст">
    <textarea bind:value={$ttsForm.tts_text} placeholder="Введите текст…" rows="5" />
  </Field>

  <Accordion title="Настройки TTS">
    <Slider label="Скорость речи" bind:value={$ttsForm.tts_rate} min={-100} max={100} step={1} />
    <Slider label="Громкость" bind:value={$ttsForm.tts_volume} min={-100} max={100} step={1} />
    <Slider label="Высота TTS" bind:value={$ttsForm.tts_pitch} min={-100} max={100} step={1} />
  </Accordion>

  <PitchBlock
    bind:autopitch={$ttsForm.autopitch}
    bind:autopitch_threshold={$ttsForm.autopitch_threshold}
    bind:rvc_pitch={$ttsForm.rvc_pitch}
  />

  <Field label="Формат выхода">
    <select bind:value={$ttsForm.output_format}>
      {#each OUTPUT_FORMATS as fmt}
        <option value={fmt}>{fmt}</option>
      {/each}
    </select>
  </Field>

  <ConversionSettings
    bind:f0_method={$ttsForm.f0_method}
    bind:index_rate={$ttsForm.index_rate}
    bind:volume_envelope={$ttsForm.volume_envelope}
    bind:protect={$ttsForm.protect}
    bind:stereo_sound={$ttsForm.stereo_sound}
    bind:audio_upscaling={$ttsForm.audio_upscaling}
    bind:autotune={$ttsForm.autotune}
    bind:autotune_tonic={$ttsForm.autotune_tonic}
    bind:autotune_scale={$ttsForm.autotune_scale}
    bind:autotune_strength={$ttsForm.autotune_strength}
    bind:f0_min={$ttsForm.f0_min}
    bind:f0_max={$ttsForm.f0_max}
  />

  <button class="btn primary" on:click={generate}>Генерировать</button>
</div>