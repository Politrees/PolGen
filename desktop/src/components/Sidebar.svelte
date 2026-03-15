<script lang="ts">
  import { activeTab, backendReady } from "$lib/state";
  import { refreshAll } from "$lib/api";
  import type { TabKey } from "$lib/types";

  let refreshing = false;

  function setTab(tab: TabKey) {
    $activeTab = tab;
  }

  async function onRefresh() {
    if (refreshing) return;
    refreshing = true;
    await refreshAll();
    refreshing = false;
  }
</script>

<div class="sidebar">
  <div class="brand">
    <div class="logo" />
    <div class="title">
      <b>PolGen Desktop</b>
    </div>
  </div>

  <div class="nav">
    <button class:active={$activeTab === "rvc"} on:click={() => setTab("rvc")}>
      RVC
    </button>
    <button class:active={$activeTab === "tts"} on:click={() => setTab("tts")}>
      TTS → RVC
    </button>
    <button class:active={$activeTab === "models"} on:click={() => setTab("models")}>
      Модели
    </button>
  </div>

  <div class="status">
    <div class="badge">
      <div class="dot" class:ok={$backendReady} class:warn={!$backendReady} />
      <span>{$backendReady ? "Backend: OK" : "Backend: не подключён"}</span>
    </div>
    <button class="sidebar-refresh" disabled={refreshing} on:click={onRefresh}>
      {refreshing ? "⏳ ..." : "⟳  Обновить данные"}
    </button>
  </div>
</div>