<script lang="ts">
  export let title: string;
  export let open: boolean = false;
</script>

<details bind:open>
  <summary>{title}</summary>
  <div class="accordion-body">
    <slot />
  </div>
</details>