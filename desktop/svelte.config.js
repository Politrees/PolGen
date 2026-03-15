import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

export default {
  preprocess: vitePreprocess(),
  onwarn: (warning, handler) => {
    // Подавляем a11y warnings — в desktop-приложении они не критичны
    if (warning.code.startsWith("a11y-")) return;
    handler(warning);
  },
};