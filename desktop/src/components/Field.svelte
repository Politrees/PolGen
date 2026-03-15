<script lang="ts">
  export let label: string;
</script>

<div class="field">
  <label>{label}</label>
  <slot />
</div>