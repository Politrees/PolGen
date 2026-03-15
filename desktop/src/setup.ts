import SetupApp from "./setup/SetupApp.svelte";

const app = new SetupApp({
  target: document.getElementById("setup-root")!,
});

export default app;