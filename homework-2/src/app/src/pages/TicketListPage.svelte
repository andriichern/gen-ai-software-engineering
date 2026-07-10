<script>
  import { onMount } from "svelte";
  import TicketFiltersBar from "../components/TicketFiltersBar.svelte";
  import TicketList from "../components/TicketList.svelte";
  import { listTickets, deleteTicket } from "../api/tickets.js";
  import { listCategories } from "../api/categories.js";
  import { notify } from "../stores/notifications.js";
  import { formatApiErrorDetail } from "../api/client.js";

  let tickets = [];
  let categories = [];
  let loading = true;
  let filters = {
    category: "",
    priority: "",
    status: "",
    customer_id: "",
    assigned_to: "",
    tag: "",
  };

  async function loadTickets() {
    loading = true;
    try {
      tickets = await listTickets(filters);
    } catch (err) {
      notify.error(formatApiErrorDetail(err.detail));
    } finally {
      loading = false;
    }
  }

  async function handleDelete(ticket) {
    if (!confirm(`Delete ticket "${ticket.subject}"?`)) return;
    try {
      await deleteTicket(ticket.id);
      notify.success("Ticket deleted.");
      await loadTickets();
    } catch (err) {
      notify.error(formatApiErrorDetail(err.detail));
    }
  }

  function handleFilterChange(next) {
    filters = next;
    loadTickets();
  }

  onMount(async () => {
    try {
      categories = await listCategories();
    } catch (err) {
      notify.error(formatApiErrorDetail(err.detail));
    }
    loadTickets();
  });
</script>

<div class="page">
  <div class="page-header">
    <h1>Tickets</h1>
  </div>

  <TicketFiltersBar {categories} {filters} onChange={handleFilterChange} />

  {#if loading}
    <p class="loading">Loading tickets…</p>
  {:else}
    <TicketList {tickets} onDelete={handleDelete} />
  {/if}
</div>
