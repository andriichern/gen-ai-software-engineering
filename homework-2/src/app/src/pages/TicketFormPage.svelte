<script>
  import { onMount } from "svelte";
  import { navigate } from "svelte-routing";
  import TicketForm from "../components/TicketForm.svelte";
  import { getTicket, createTicket, updateTicket } from "../api/tickets.js";
  import { listCategories } from "../api/categories.js";
  import { notify } from "../stores/notifications.js";
  import { formatApiErrorDetail } from "../api/client.js";

  export let id = null; // present when editing

  let categories = [];
  let ticket = null;
  let loading = !!id;
  let submitting = false;
  let loadError = null;

  onMount(async () => {
    try {
      categories = await listCategories();
      if (id) {
        ticket = await getTicket(id);
      }
    } catch (err) {
      loadError = formatApiErrorDetail(err.detail);
    } finally {
      loading = false;
    }
  });

  async function handleSubmit(payload, { autoClassify }) {
    submitting = true;
    try {
      if (id) {
        await updateTicket(id, payload);
        notify.success("Ticket updated.");
        navigate(`/tickets/${id}`);
      } else {
        const created = await createTicket(payload, { autoClassify });
        notify.success("Ticket created.");
        navigate(`/tickets/${created.id}`);
      }
    } catch (err) {
      notify.error(formatApiErrorDetail(err.detail));
    } finally {
      submitting = false;
    }
  }
</script>

<div class="page">
  <div class="page-header">
    <h1>{id ? "Edit Ticket" : "New Ticket"}</h1>
  </div>

  {#if loading}
    <p class="loading">Loading…</p>
  {:else if loadError}
    <p class="error-state">{loadError}</p>
  {:else}
    <TicketForm
      {categories}
      initial={ticket}
      submitLabel={id ? "Save Changes" : "Create Ticket"}
      {submitting}
      onSubmit={handleSubmit}
    />
  {/if}
</div>
