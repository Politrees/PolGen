<script lang="ts">
  import Slider from "./Slider.svelte";

  export let autopitch: boolean;
  export let autopitch_threshold: number;
  export let rvc_pitch: number;
</script>

<label class="checkbox-wrap">
  <input type="checkbox" bind:checked={autopitch} />
  <span>Авто определение тона</span>
</label>

{#if autopitch}
  <div class="field">
    <label>Порог</label>
    <select bind:value={autopitch_threshold}>
      <option value={155}>Мужская модель (155)</option>
      <option value={255}>Женская модель (255)</option>
    </select>
  </div>
{:else}
  <Slider label="Высота тона (-24 … +24)" bind:value={rvc_pitch} min={-24} max={24} step={1} />
{/if}