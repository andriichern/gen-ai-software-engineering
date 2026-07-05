<script>
  export let onImport = () => {};
  export let submitting = false;

  let file = null;
  let autoClassify = false;

  function handleFileChange(event) {
    file = event.target.files[0] || null;
  }

  function handleSubmit() {
    if (!file) return;
    onImport(file, { autoClassify });
  }
</script>

<form class="import-form" on:submit|preventDefault={handleSubmit}>
  <label>
    Ticket file (.csv, .json, .xml)
    <input type="file" accept=".csv,.json,.xml" on:change={handleFileChange} />
  </label>

  <label class="checkbox-row">
    <input type="checkbox" bind:checked={autoClassify} />
    Auto-classify every imported ticket
  </label>

  <button type="submit" class="btn-primary" disabled={!file || submitting}>
    {submitting ? "Importing…" : "Import Tickets"}
  </button>
</form>

<style>
  .import-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    max-width: 480px;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.85rem;
    color: #334155;
  }
  .checkbox-row {
    flex-direction: row;
    align-items: center;
    gap: 0.5rem;
  }
  input[type="file"] {
    font-size: 0.85rem;
  }
</style>
