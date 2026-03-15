<script lang="ts">
  import { platform, installMode, selectedUrl, currentStep } from "./state";

  $: plat = $platform;
  $: variants = plat?.all_variants ?? [];
  $: currentVariant = variants.find((v) => v.url === $selectedUrl);

  $: isRecommended = (() => {
    if (!currentVariant || !plat) return false;
    return currentVariant.url === plat.recommended_url;
  })();

  $: showMismatchWarn = (() => {
    if (!plat || !currentVariant) return "";
    // CUDA выбран но GPU не подходит
    if (currentVariant.url.includes("CUDA") && !plat.gpu_cuda_capable) {
      return plat.has_nvidia
        ? `Ваша ${plat.gpu_name} не поддерживает CUDA режим. Рекомендуется CPU.`
        : "NVIDIA GPU не обнаружена. CUDA версия не будет работать с ускорением.";
    }
    // CPU выбран но GPU подходит — не warn, просто info
    return "";
  })();
</script>

<div class="setup-step">
  <h2>Способ установки</h2>

  <div class="mode-tabs">
    <button
      class="mode-tab"
      class:active={$installMode === "download"}
      on:click={() => ($installMode = "download")}
    >
      📦 Скачать готовое
    </button>
    <button
      class="mode-tab"
      class:active={$installMode === "conda"}
      on:click={() => ($installMode = "conda")}
    >
      🔧 Conda
    </button>
  </div>

  {#if $installMode === "download"}
    <p class="mode-desc">
      Скачивает Python-окружение с HuggingFace. Быстро, не требует Conda.
    </p>

    {#if variants.length}
      <div class="setup-field">
        <label>Версия:</label>
        <select class="setup-select" bind:value={$selectedUrl}>
          {#each variants as v}
            <option value={v.url}>
              {v.label}{v.url === plat?.recommended_url ? " ⭐" : ""}
            </option>
          {/each}
        </select>
      </div>

      {#if currentVariant}
        <div class="variant-desc">{currentVariant.description}</div>
      {/if}
    {/if}

    {#if showMismatchWarn}
      <div class="setup-warn">⚠ {showMismatchWarn}</div>
    {/if}
  {:else}
    <p class="mode-desc">
      Запускает скрипт run-PolGen-installer. Требует Conda/pip.
    </p>
    <div class="setup-warn">
      ⚠ Conda может быть недоступна в некоторых регионах.
    </div>
  {/if}

  <div class="setup-buttons">
    <button class="setup-btn-secondary" on:click={() => ($currentStep = "check")}>
      ← Назад
    </button>
    <button
      class="setup-btn"
      disabled={$installMode === "download" && !$selectedUrl}
      on:click={() => ($currentStep = "install")}
    >
      Установить →
    </button>
  </div>
</div>