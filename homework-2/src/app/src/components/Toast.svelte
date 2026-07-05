<script>
  import { notifications, dismiss } from "../stores/notifications.js";
</script>

<div class="toast-stack">
  {#each $notifications as note (note.id)}
    <div class="toast toast-{note.type}" role="alert">
      <span>{note.message}</span>
      <button
        class="toast-close"
        on:click={() => dismiss(note.id)}
        aria-label="Dismiss">×</button
      >
    </div>
  {/each}
</div>

<style>
  .toast-stack {
    position: fixed;
    top: 1rem;
    right: 1rem;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    max-width: min(90vw, 360px);
  }
  .toast {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.65rem 1rem;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    font-size: 0.9rem;
  }
  .toast-success {
    background: #dcfce7;
    color: #14532d;
  }
  .toast-error {
    background: #fee2e2;
    color: #7f1d1d;
  }
  .toast-close {
    background: none;
    border: none;
    font-size: 1.1rem;
    line-height: 1;
    cursor: pointer;
    color: inherit;
  }
</style>
