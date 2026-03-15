<script lang="ts">
  import { open as openDialog } from "@tauri-apps/api/dialog";
  import { models, installUrlForm, installZipForm, installFilesForm, toasts } from "$lib/state";
  import { postJob, deleteModel, openModelFolder, loadModels } from "$lib/api";
  import Accordion from "../components/Accordion.svelte";
  import Field from "../components/Field.svelte";

  async function installUrl() {
    if (!$installUrlForm.url.trim()) { toasts.show("Введите URL для скачивания"); return; }
    if (!$installUrlForm.model_name.trim()) { toasts.show("Введите имя модели"); return; }
    const ok = await postJob("/jobs/models/install_url", $installUrlForm);
    if (ok) await loadModels();
  }

  async function installZip() {
    if (!$installZipForm.zip_path.trim()) { toasts.show("Выберите ZIP-файл"); return; }
    if (!$installZipForm.model_name.trim()) { toasts.show("Введите имя модели"); return; }
    const ok = await postJob("/jobs/models/install_local_zip", {
      path: $installZipForm.zip_path,
      model_name: $installZipForm.model_name,
    });
    if (ok) await loadModels();
  }

  async function installFiles() {
    if (!$installFilesForm.pth_path.trim()) { toasts.show("Выберите .pth файл"); return; }
    if (!$installFilesForm.model_name.trim()) { toasts.show("Введите имя модели"); return; }
    const ok = await postJob("/jobs/models/install_local_files", {
      path: $installFilesForm.pth_path,
      extra_path: $installFilesForm.index_path || null,
      model_name: $installFilesForm.model_name,
    });
    if (ok) await loadModels();
  }

  async function pickZip() {
    const sel = await openDialog({ multiple: false, filters: [{ name: "ZIP", extensions: ["zip"] }] });
    if (typeof sel === "string") $installZipForm.zip_path = sel;
  }

  async function pickPth() {
    const sel = await openDialog({ multiple: false, filters: [{ name: "PTH", extensions: ["pth"] }] });
    if (typeof sel === "string") $installFilesForm.pth_path = sel;
  }

  async function pickIndex() {
    const sel = await openDialog({ multiple: false, filters: [{ name: "INDEX", extensions: ["index"] }] });
    if (typeof sel === "string") $installFilesForm.index_path = sel;
  }
</script>

<div class="card">
  <h2>RVC модели</h2>

  <div class="chips">
    {#each $models as m}
      <div class="chip">
        <div class="chipName" title={m}>{m}</div>
        <div class="chipActions">
          <button class="iconBtn" title="Папка" on:click={() => openModelFolder(m)}>📁</button>
          <button class="iconBtn danger" title="Удалить" on:click={() => deleteModel(m)}>🗑</button>
        </div>
      </div>
    {/each}
  </div>

  {#if !$models.length}
    <div class="text-muted">Нет установленных моделей.</div>
  {/if}

  <div class="hr" />

  <Accordion title="Установка по ссылке (ZIP)">
    <Field label="URL">
      <input type="text" bind:value={$installUrlForm.url} placeholder="https://..." />
    </Field>
    <Field label="Имя модели">
      <input type="text" bind:value={$installUrlForm.model_name} placeholder="MyModel" />
    </Field>
    <button class="btn primary" on:click={installUrl}>Установить</button>
  </Accordion>

  <div class="hr" />

  <Accordion title="Распаковка ZIP">
    <Field label="ZIP файл">
      <div class="row">
        <input type="text" bind:value={$installZipForm.zip_path} placeholder="Путь к ZIP…" />
        <button class="btn" on:click={pickZip}>Выбрать</button>
      </div>
    </Field>
    <Field label="Имя модели">
      <input type="text" bind:value={$installZipForm.model_name} placeholder="MyModel" />
    </Field>
    <button class="btn primary" on:click={installZip}>Распаковать</button>
  </Accordion>

  <div class="hr" />

  <Accordion title="Загрузка .pth / .index">
    <Field label=".pth файл">
      <div class="row">
        <input type="text" bind:value={$installFilesForm.pth_path} placeholder=".pth путь…" />
        <button class="btn" on:click={pickPth}>Выбрать</button>
      </div>
    </Field>
    <Field label=".index файл">
      <div class="row">
        <input type="text" bind:value={$installFilesForm.index_path} placeholder=".index путь (необяз.)…" />
        <button class="btn" on:click={pickIndex}>Выбрать</button>
      </div>
    </Field>
    <Field label="Имя модели">
      <input type="text" bind:value={$installFilesForm.model_name} placeholder="MyModel" />
    </Field>
    <button class="btn primary" on:click={installFiles}>Загрузить</button>
  </Accordion>
</div>