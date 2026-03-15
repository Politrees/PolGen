<script lang="ts">
  import { onMount } from "svelte";
  import { appWindow } from "@tauri-apps/api/window";
  import { activeTab, backendReady, logs } from "$lib/state";
  import { connectBackend } from "$lib/api";
  import { sleep } from "$lib/utils";

  import Sidebar from "./components/Sidebar.svelte";
  import Titlebar from "./components/Titlebar.svelte";
  import Player from "./components/Player.svelte";
  import Toast from "./components/Toast.svelte";
  import JobPanel from "./components/JobPanel.svelte";

  import RvcTab from "./tabs/RvcTab.svelte";
  import TtsTab from "./tabs/TtsTab.svelte";
  import UvrTab from "./tabs/UvrTab.svelte";
  import ModelsTab from "./tabs/ModelsTab.svelte";

  let connecting = true;
  let connectionFailed = false;
  let started = false;

  async function tryConnect() {
    connecting = true;
    connectionFailed = false;
    const ok = await connectBackend();
    connecting = false;
    connectionFailed = !ok;
  }

  async function startApp() {
    if (started) return;
    started = true;
    logs.append("[UI] Запуск…");
    await tryConnect();
    $activeTab = "models";
  }

  onMount(async () => {
    // Проверяем видимость сразу
    let visible = false;
    try {
      visible = await appWindow.isVisible();
    } catch {}

    if (visible) {
      // Обычный запуск — окно уже видимо
      await startApp();
    } else {
      // После установки — окно скрыто, ждём show
      logs.append("[UI] Ожидание установки...");

      // Подписываемся на событие фокуса/видимости
      const unlisten = await appWindow.onFocusChanged(async ({ payload: focused }) => {
        if (focused && !started) {
          unlisten();
          // Даём окну отрисоваться
          await sleep(300);
          await startApp();
        }
      });

      // Fallback: polling видимости (на случай если onFocusChanged не сработает)
      const pollVisible = async () => {
        for (let i = 0; i < 600; i++) {
          if (started) return;
          try {
            if (await appWindow.isVisible()) {
              if (!started) {
                await sleep(300);
                await startApp();
              }
              return;
            }
          } catch {}
          await sleep(500);
        }
      };
      pollVisible();
    }
  });
</script>

<div class="app">
  <Sidebar />

  <div class="main">
    <Titlebar />

    <div class="content">
      <div>
        {#if connecting}
          <div class="card">
            <div class="connecting-box">
              <div class="connecting-spinner" />
              <h2>Запуск backend...</h2>
              <p class="text-muted">Обычно занимает 5–15 секунд</p>
            </div>
          </div>
        {:else if connectionFailed}
          <div class="card">
            <h2>⚠ Backend не подключён</h2>
            <p class="text-muted">
              Не удалось подключиться. Попробуйте переподключиться или перезапустите приложение.
            </p>
            <button class="btn primary" on:click={tryConnect}>
              Переподключить
            </button>
          </div>
        {:else if $activeTab === "rvc"}
          <RvcTab />
        {:else if $activeTab === "tts"}
          <TtsTab />
        {:else if $activeTab === "uvr"}
          <UvrTab />
        {:else}
          <ModelsTab />
        {/if}
      </div>

      <div>
        <JobPanel />
      </div>
    </div>

    <Toast />
    <Player />
  </div>
</div>

<style>
  .connecting-box {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 32px 20px;
    text-align: center;
  }

  .connecting-spinner {
    width: 36px;
    height: 36px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .connecting-box h2 {
    margin: 0;
    font-size: 16px;
  }
</style>