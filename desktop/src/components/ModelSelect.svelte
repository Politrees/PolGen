<script lang="ts">
  import { models } from "$lib/state";
  import { loadModels } from "$lib/api";

  export let value: string;

  async function refresh() {
    await loadModels();
    const list = $models;
    if (list.length && !list.includes(value)) {
      value = list[0];
    }
  }
</script>

<div class="field">
  <label>RVC модель</label>
  <div class="model-select-row">
    <select bind:value disabled={!$models.length}>
      {#if !$models.length}
        <option value="">(нет)</option>
      {:else}
        {#each $models as m}
          <option value={m}>{m}</option>
        {/each}
      {/if}
    </select>
    <button class="refresh-btn" title="Обновить список моделей" on:click={refresh}>
      ⟳
    </button>
  </div>
</div>