<script>
  import { Link } from "svelte-routing";
  import Badge from "./Badge.svelte";
  import ClassificationResultPanel from "./ClassificationResultPanel.svelte";
  import { formatDateTime, formatConfidence } from "../utils/format.js";

  export let ticket;
  export let classificationResult = null;
  export let onClassify = () => {};
  export let onDelete = () => {};
  export let classifying = false;
</script>

<div class="detail">
  <header class="detail-header">
    <div>
      <h2>{ticket.subject}</h2>
      <p class="customer">{ticket.customer_name} · {ticket.customer_email} · {ticket.customer_id}</p>
    </div>
    <div class="header-actions">
      <Link to={`/tickets/${ticket.id}/edit`} class="btn-secondary-link">Edit</Link>
      <button type="button" class="btn-danger" on:click={() => onDelete(ticket)}>Delete</button>
    </div>
  </header>

  <div class="badges">
    <Badge value={ticket.category} kind="category" />
    <Badge value={ticket.priority} kind="priority" />
    <Badge value={ticket.status} kind="status" />
    {#if ticket.classification_overridden}
      <span class="overridden-flag">Manually overridden</span>
    {/if}
  </div>

  <section>
    <h3>Description</h3>
    <p class="description">{ticket.description}</p>
  </section>

  <section class="two-col">
    <div>
      <h3>Details</h3>
      <dl>
        <dt>Assigned To</dt><dd>{ticket.assigned_to || "Unassigned"}</dd>
        <dt>Tags</dt><dd>{ticket.tags?.length ? ticket.tags.join(", ") : "—"}</dd>
        <dt>Created</dt><dd>{formatDateTime(ticket.created_at)}</dd>
        <dt>Updated</dt><dd>{formatDateTime(ticket.updated_at)}</dd>
        <dt>Resolved</dt><dd>{formatDateTime(ticket.resolved_at)}</dd>
        <dt>Classification Confidence</dt><dd>{formatConfidence(ticket.classification_confidence)}</dd>
      </dl>
    </div>
    <div>
      <h3>Metadata</h3>
      <dl>
        <dt>Source</dt><dd>{ticket.metadata?.source || "—"}</dd>
        <dt>Browser</dt><dd>{ticket.metadata?.browser || "—"}</dd>
        <dt>Device Type</dt><dd>{ticket.metadata?.device_type || "—"}</dd>
      </dl>
    </div>
  </section>

  <section>
    <div class="classify-header">
      <h3>Auto-Classification</h3>
      <button type="button" class="btn-primary" on:click={onClassify} disabled={classifying}>
        {classifying ? "Classifying…" : "Trigger Auto-Classify"}
      </button>
    </div>
    <ClassificationResultPanel result={classificationResult} />
  </section>
</div>

<style>
  .detail {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    max-width: 900px;
  }
  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .detail-header h2 {
    margin: 0 0 0.25rem;
  }
  .customer {
    margin: 0;
    color: #64748b;
    font-size: 0.85rem;
  }
  .header-actions {
    display: flex;
    gap: 0.6rem;
  }
  .badges {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    flex-wrap: wrap;
  }
  .overridden-flag {
    font-size: 0.78rem;
    color: #92400e;
    background: #fef3c7;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
  }
  h3 {
    font-size: 0.95rem;
    color: #334155;
    margin: 0 0 0.5rem;
  }
  .description {
    white-space: pre-wrap;
    color: #1e293b;
  }
  .two-col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
  }
  dl {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.35rem 1rem;
    margin: 0;
    font-size: 0.85rem;
  }
  dt {
    color: #64748b;
  }
  dd {
    margin: 0;
    color: #1e293b;
  }
  .classify-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
  }

  @media (max-width: 640px) {
    .two-col {
      grid-template-columns: 1fr;
    }
  }
</style>
