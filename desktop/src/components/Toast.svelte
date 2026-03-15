<script lang="ts">
  import { toasts } from "$lib/state";
  import { fly, fade } from "svelte/transition";
</script>

<div class="toast-container">
  {#each $toasts as toast (toast.id)}
    <div
      class="toast toast-visible"
      in:fly={{ x: 20, duration: 250 }}
      out:fade={{ duration: 200 }}
    >
      {toast.message}
    </div>
  {/each}
</div>