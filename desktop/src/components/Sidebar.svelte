<script lang="ts">
  import { activeTab, backendReady } from "$lib/state";
  import { refreshAll } from "$lib/api";
  import type { TabKey } from "$lib/types";

  let refreshing = false;
  let spinClass = "";

  function setTab(tab: TabKey) {
    $activeTab = tab;
  }

  async function onRefresh() {
    if (refreshing) return;
    refreshing = true;
    spinClass = "spinning";
    await refreshAll();
    refreshing = false;
    setTimeout(() => (spinClass = ""), 300);
  }

  const navItems: { key: TabKey; icon: string; label: string }[] = [
    { key: "rvc", icon: "🎤", label: "RVC" },
    { key: "tts", icon: "🗣", label: "TTS → RVC" },
    { key: "uvr", icon: "🎵", label: "UVR" },
    { key: "models", icon: "📦", label: "Модели" },
  ];
</script>

<div class="sidebar">
  <div class="brand">
    <div class="logo" />
    <div class="title">
      <b>PolGen</b>
      <span>Desktop</span>
    </div>
  </div>

  <div class="nav">
    {#each navItems as item}
      <button class:active={$activeTab === item.key} on:click={() => setTab(item.key)}>
        <span class="nav-icon">{item.icon}</span>
        {item.label}
      </button>
    {/each}
  </div>

  <div class="status">
    <div class="badge">
      <div class="dot" class:ok={$backendReady} class:warn={!$backendReady} />
      <span>{$backendReady ? "Backend: OK" : "Backend: ожидание…"}</span>
    </div>
    <button class="sidebar-refresh" disabled={refreshing} on:click={onRefresh}>
      <span class="refresh-icon {spinClass}">⟳</span>
      <span>{refreshing ? "Обновление..." : "Обновить данные"}</span>
    </button>
  </div>
</div>

<style>
  .nav-icon {
    font-size: 15px;
    margin-right: 4px;
  }

  .refresh-icon {
    display: inline-block;
    font-size: 14px;
    transition: transform 0.3s ease;
  }

  .refresh-icon.spinning {
    animation: spin-refresh 0.6s ease;
  }

  @keyframes spin-refresh {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
</style>