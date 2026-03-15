<script lang="ts">
  import Accordion from "./Accordion.svelte";
  import Slider from "./Slider.svelte";
  import { F0_METHODS, TONIC_NOTES, SCALES } from "$lib/types";

  export let f0_method: string;
  export let index_rate: number;
  export let volume_envelope: number;
  export let protect: number;
  export let stereo_sound: boolean;
  export let audio_upscaling: boolean;
  export let autotune: boolean;
  export let autotune_tonic: string;
  export let autotune_scale: string;
  export let autotune_strength: number;
  export let f0_min: number;
  export let f0_max: number;
</script>

<Accordion title="Настройки преобразования">
  <Accordion title="Стандартные настройки">
    <div class="field">
      <label>Метод F0</label>
      <select bind:value={f0_method}>
        {#each F0_METHODS as m}
          <option value={m}>{m}</option>
        {/each}
      </select>
    </div>
    <Slider label="Влияние индекса" bind:value={index_rate} min={0} max={1} step={0.01} />
    <Slider label="Смешивание RMS" bind:value={volume_envelope} min={0} max={1} step={0.01} />
    <Slider label="Защита согласных" bind:value={protect} min={0} max={0.5} step={0.01} />
  </Accordion>

  <Accordion title="Дополнительные настройки">
    <label class="checkbox-wrap">
      <input type="checkbox" bind:checked={stereo_sound} />
      <span>Стерео</span>
    </label>
    <label class="checkbox-wrap">
      <input type="checkbox" bind:checked={audio_upscaling} />
      <span>Аудио-апскейл (FlashSR)</span>
    </label>

    <label class="checkbox-wrap">
      <input type="checkbox" bind:checked={autotune} />
      <span>Автотюн</span>
    </label>

    {#if autotune}
      <div class="autotune-fields">
        <div class="field">
          <label>Тоника</label>
          <select bind:value={autotune_tonic}>
            {#each TONIC_NOTES as n}
              <option value={n}>{n}</option>
            {/each}
          </select>
        </div>
        <div class="field">
          <label>Гамма</label>
          <select bind:value={autotune_scale}>
            {#each SCALES as s}
              <option value={s}>{s}</option>
            {/each}
          </select>
        </div>
        <Slider label="Сила автотюна" bind:value={autotune_strength} min={0} max={1} step={0.1} />
      </div>
    {/if}

    <div class="hr" />
    <Slider label="F0 мин" bind:value={f0_min} min={1} max={120} step={1} />
    <Slider label="F0 макс" bind:value={f0_max} min={380} max={16000} step={1} />
  </Accordion>
</Accordion>