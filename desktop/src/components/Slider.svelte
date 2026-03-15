<script lang="ts">
  export let label: string;
  export let value: number;
  export let min: number = 0;
  export let max: number = 1;
  export let step: number = 0.01;

  function getPct(v: number): string {
    const pct = max > min ? ((v - min) / (max - min)) * 100 : 0;
    return `${pct}%`;
  }
</script>

<div class="field">
  <label>{label}</label>
  <div class="slider-row">
    <input
      type="range"
      {min}
      {max}
      {step}
      bind:value
      style="--value-pct: {getPct(value)}"
    />
    <span class="slider-val">{value}</span>
  </div>
</div>