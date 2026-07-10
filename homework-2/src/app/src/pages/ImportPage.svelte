<script>
  import ImportForm from "../components/ImportForm.svelte";
  import { importTickets } from "../api/tickets.js";
  import { notify } from "../stores/notifications.js";
  import { formatApiErrorDetail } from "../api/client.js";

  let submitting = false;
  let summary = null;

  async function handleImport(file, { autoClassify }) {
    submitting = true;
    summary = null;
    try {
      summary = await importTickets(file, { autoClassify });
      notify.success(
        `Imported ${summary.successful}/${summary.total} tickets.`,
      );
    } catch (err) {
      notify.error(formatApiErrorDetail(err.detail));
    } finally {
      submitting = false;
    }
  }
</script>

<div class="page">
  <div class="page-header">
    <h1>Bulk Import</h1>
  </div>

  <ImportForm onImport={handleImport} {submitting} />

  {#if summary}
    <section class="summary">
      <h2>Import Summary</h2>
      <p>
        Total: {summary.total} · Successful: {summary.successful} · Failed: {summary.failed}
      </p>
      {#if summary.errors?.length}
        <table>
          <thead>
            <tr><th>Row</th><th>Error</th></tr>
          </thead>
          <tbody>
            {#each summary.errors as e (e.index)}
              <tr><td>{e.index}</td><td>{e.error}</td></tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </section>
  {/if}
</div>

<style>
  .summary {
    margin-top: 1.5rem;
    max-width: 720px;
  }
  h2 {
    font-size: 1rem;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
    margin-top: 0.5rem;
  }
  th,
  td {
    text-align: left;
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
  }
  th {
    color: #64748b;
    font-weight: 600;
  }
</style>
