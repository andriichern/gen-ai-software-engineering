<script>
  import { Link } from "svelte-routing";
  import Badge from "./Badge.svelte";
  import { formatDateTime } from "../utils/format.js";

  export let tickets = [];
  export let onDelete = () => {};
</script>

{#if tickets.length === 0}
  <p class="empty-state">No tickets match the current filters.</p>
{:else}
  <div class="ticket-table">
    {#each tickets as ticket (ticket.id)}
      <div class="ticket-row">
        <div class="ticket-main">
          <Link to={`/tickets/${ticket.id}`} class="ticket-subject">{ticket.subject}</Link>
          <span class="ticket-customer">{ticket.customer_name} · {ticket.customer_email}</span>
        </div>
        <div class="ticket-meta">
          <Badge value={ticket.category} kind="category" />
          <Badge value={ticket.priority} kind="priority" />
          <Badge value={ticket.status} kind="status" />
        </div>
        <div class="ticket-date">{formatDateTime(ticket.created_at)}</div>
        <div class="ticket-actions">
          <Link to={`/tickets/${ticket.id}/edit`}>Edit</Link>
          <button type="button" class="btn-danger-link" on:click={() => onDelete(ticket)}>Delete</button>
        </div>
      </div>
    {/each}
  </div>
{/if}

<style>
  .empty-state {
    color: #64748b;
    padding: 2rem 0;
    text-align: center;
  }
  .ticket-table {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .ticket-row {
    display: grid;
    grid-template-columns: 2fr 1.4fr auto auto;
    gap: 1rem;
    align-items: center;
    padding: 0.75rem 1rem;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
  }
  .ticket-main {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }
  .ticket-main :global(.ticket-subject) {
    font-weight: 600;
    color: #0f172a;
    text-decoration: none;
  }
  .ticket-main :global(.ticket-subject:hover) {
    text-decoration: underline;
  }
  .ticket-customer {
    font-size: 0.8rem;
    color: #64748b;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .ticket-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }
  .ticket-date {
    font-size: 0.8rem;
    color: #64748b;
    white-space: nowrap;
  }
  .ticket-actions {
    display: flex;
    gap: 0.75rem;
    font-size: 0.85rem;
  }
  .btn-danger-link {
    background: none;
    border: none;
    color: #b91c1c;
    cursor: pointer;
    padding: 0;
    font-size: 0.85rem;
  }

  @media (max-width: 720px) {
    .ticket-row {
      grid-template-columns: 1fr;
      gap: 0.5rem;
    }
  }
</style>
