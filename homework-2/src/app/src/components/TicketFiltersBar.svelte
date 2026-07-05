<script>
  import { PRIORITIES, STATUSES } from "../utils/constants.js";
  import { titleCase } from "../utils/format.js";

  export let categories = [];
  export let filters = { category: "", priority: "", status: "", customer_id: "", assigned_to: "", tag: "" };
  export let onChange = () => {};

  function update() {
    onChange({ ...filters });
  }

  function clearAll() {
    filters = { category: "", priority: "", status: "", customer_id: "", assigned_to: "", tag: "" };
    update();
  }
</script>

<div class="filters">
  <label>
    Category
    <select bind:value={filters.category} on:change={update}>
      <option value="">All</option>
      {#each categories as c}
        <option value={c.category}>{titleCase(c.category)}</option>
      {/each}
      <option value="other">Other</option>
    </select>
  </label>

  <label>
    Priority
    <select bind:value={filters.priority} on:change={update}>
      <option value="">All</option>
      {#each PRIORITIES as p}
        <option value={p}>{titleCase(p)}</option>
      {/each}
    </select>
  </label>

  <label>
    Status
    <select bind:value={filters.status} on:change={update}>
      <option value="">All</option>
      {#each STATUSES as s}
        <option value={s}>{titleCase(s)}</option>
      {/each}
    </select>
  </label>

  <label>
    Customer ID
    <input type="text" bind:value={filters.customer_id} on:input={update} placeholder="cust-123" />
  </label>

  <label>
    Assigned To
    <input type="text" bind:value={filters.assigned_to} on:input={update} placeholder="agent-1" />
  </label>

  <label>
    Tag
    <input type="text" bind:value={filters.tag} on:input={update} placeholder="vip" />
  </label>

  <button type="button" class="btn-secondary" on:click={clearAll}>Clear filters</button>
</div>

<style>
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    align-items: end;
    margin-bottom: 1rem;
  }
  label {
    display: flex;
    flex-direction: column;
    font-size: 0.8rem;
    color: #475569;
    gap: 0.25rem;
  }
  select, input {
    padding: 0.4rem 0.5rem;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-size: 0.9rem;
  }
</style>
