<script>
  import { onMount } from "svelte";
  import { navigate } from "svelte-routing";
  import TicketDetailView from "../components/TicketDetailView.svelte";
  import { getTicket, deleteTicket, autoClassifyTicket } from "../api/tickets.js";
  import { notify } from "../stores/notifications.js";
  import { formatApiErrorDetail } from "../api/client.js";

  export let id;

  let ticket = null;
  let loading = true;
  let loadError = null;
  let classificationResult = null;
  let classifying = false;

  async function load() {
    loading = true;
    try {
      ticket = await getTicket(id);
    } catch (err) {
      loadError = formatApiErrorDetail(err.detail);
    } finally {
      loading = false;
    }
  }

  onMount(load);

  async function handleClassify() {
    classifying = true;
    try {
      classificationResult = await autoClassifyTicket(id);
      await load();
      notify.success("Classification complete.");
    } catch (err) {
      notify.error(formatApiErrorDetail(err.detail));
    } finally {
      classifying = false;
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete ticket "${ticket.subject}"?`)) return;
    try {
      await deleteTicket(id);
      notify.success("Ticket deleted.");
      navigate("/");
    } catch (err) {
      notify.error(formatApiErrorDetail(err.detail));
    }
  }
</script>

<div class="page">
  {#if loading}
    <p class="loading">Loading ticket…</p>
  {:else if loadError}
    <p class="error-state">{loadError}</p>
  {:else}
    <TicketDetailView
      {ticket}
      {classificationResult}
      {classifying}
      onClassify={handleClassify}
      onDelete={handleDelete}
    />
  {/if}
</div>
