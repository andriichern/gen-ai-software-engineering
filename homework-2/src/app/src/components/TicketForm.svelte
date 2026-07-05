<script>
  import { PRIORITIES, STATUSES, SOURCES, DEVICE_TYPES } from "../utils/constants.js";
  import { titleCase } from "../utils/format.js";
  import { validateTicketForm } from "../utils/validation.js";

  export let categories = [];
  export let initial = null; // existing ticket, when editing
  export let submitLabel = "Create Ticket";
  export let onSubmit = () => {};
  export let submitting = false;

  const isEdit = !!initial;

  let fields = {
    customer_id: initial?.customer_id || "",
    customer_email: initial?.customer_email || "",
    customer_name: initial?.customer_name || "",
    subject: initial?.subject || "",
    description: initial?.description || "",
    category: initial?.category || "",
    priority: initial?.priority || "",
    status: initial?.status || "new",
    assigned_to: initial?.assigned_to || "",
    tags: (initial?.tags || []).join(", "),
    source: initial?.metadata?.source || "web_form",
    browser: initial?.metadata?.browser || "",
    device_type: initial?.metadata?.device_type || "",
  };

  let errors = {};
  let autoClassify = false;

  function buildPayload() {
    const payload = {
      customer_id: fields.customer_id.trim(),
      customer_email: fields.customer_email.trim(),
      customer_name: fields.customer_name.trim(),
      subject: fields.subject.trim(),
      description: fields.description.trim(),
      assigned_to: fields.assigned_to.trim() || null,
      tags: fields.tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
      metadata: {
        source: fields.source,
        browser: fields.browser.trim() || null,
        device_type: fields.device_type || null,
      },
    };
    if (fields.category) payload.category = fields.category;
    if (fields.priority) payload.priority = fields.priority;
    if (isEdit) payload.status = fields.status;
    return payload;
  }

  function handleSubmit() {
    const { valid, errors: validationErrors } = validateTicketForm(fields);
    errors = validationErrors;
    if (!valid) return;
    onSubmit(buildPayload(), { autoClassify });
  }
</script>

<form class="ticket-form" on:submit|preventDefault={handleSubmit} novalidate>
  <div class="grid">
    <label>
      Customer ID
      <input type="text" bind:value={fields.customer_id} />
      {#if errors.customer_id}<span class="field-error">{errors.customer_id}</span>{/if}
    </label>

    <label>
      Customer Email
      <input type="email" bind:value={fields.customer_email} />
      {#if errors.customer_email}<span class="field-error">{errors.customer_email}</span>{/if}
    </label>

    <label>
      Customer Name
      <input type="text" bind:value={fields.customer_name} />
      {#if errors.customer_name}<span class="field-error">{errors.customer_name}</span>{/if}
    </label>

    <label>
      Assigned To
      <input type="text" bind:value={fields.assigned_to} placeholder="agent-1 (optional)" />
    </label>
  </div>

  <label>
    Subject
    <input type="text" bind:value={fields.subject} maxlength="200" />
    {#if errors.subject}<span class="field-error">{errors.subject}</span>{/if}
  </label>

  <label>
    Description
    <textarea rows="4" bind:value={fields.description} maxlength="2000"></textarea>
    {#if errors.description}<span class="field-error">{errors.description}</span>{/if}
  </label>

  <div class="grid">
    <label>
      Category
      <select bind:value={fields.category}>
        <option value="">Auto / unset</option>
        {#each categories as c}
          <option value={c.category}>{titleCase(c.category)}</option>
        {/each}
        <option value="other">Other</option>
      </select>
    </label>

    <label>
      Priority
      <select bind:value={fields.priority}>
        <option value="">Auto / unset</option>
        {#each PRIORITIES as p}
          <option value={p}>{titleCase(p)}</option>
        {/each}
      </select>
    </label>

    {#if isEdit}
      <label>
        Status
        <select bind:value={fields.status}>
          {#each STATUSES as s}
            <option value={s}>{titleCase(s)}</option>
          {/each}
        </select>
      </label>
    {/if}

    <label>
      Tags (comma separated)
      <input type="text" bind:value={fields.tags} placeholder="vip, urgent" />
    </label>
  </div>

  <fieldset class="metadata">
    <legend>Metadata</legend>
    <div class="grid">
      <label>
        Source
        <select bind:value={fields.source}>
          {#each SOURCES as s}
            <option value={s}>{titleCase(s)}</option>
          {/each}
        </select>
      </label>
      <label>
        Browser
        <input type="text" bind:value={fields.browser} placeholder="Chrome (optional)" />
      </label>
      <label>
        Device Type
        <select bind:value={fields.device_type}>
          <option value="">Unspecified</option>
          {#each DEVICE_TYPES as d}
            <option value={d}>{titleCase(d)}</option>
          {/each}
        </select>
      </label>
    </div>
  </fieldset>

  {#if !isEdit}
    <label class="checkbox-row">
      <input type="checkbox" bind:checked={autoClassify} />
      Run auto-classification on create
    </label>
  {/if}

  <button type="submit" class="btn-primary" disabled={submitting}>
    {submitting ? "Saving…" : submitLabel}
  </button>
</form>

<style>
  .ticket-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    max-width: 720px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.85rem;
    color: #334155;
  }
  input, select, textarea {
    padding: 0.5rem 0.6rem;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-size: 0.9rem;
    font-family: inherit;
  }
  .field-error {
    color: #b91c1c;
    font-size: 0.78rem;
  }
  fieldset.metadata {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.75rem 1rem 1rem;
  }
  legend {
    font-size: 0.8rem;
    color: #64748b;
    padding: 0 0.35rem;
  }
  .checkbox-row {
    flex-direction: row;
    align-items: center;
    gap: 0.5rem;
  }

  @media (max-width: 640px) {
    .grid {
      grid-template-columns: 1fr;
    }
  }
</style>
