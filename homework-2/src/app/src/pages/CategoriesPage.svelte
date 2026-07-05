<script>
  import { onMount } from "svelte";
  import { listCategories, createCategory, addCategoryKeywords } from "../api/categories.js";
  import { validateCategoryKey } from "../utils/validation.js";
  import { titleCase } from "../utils/format.js";
  import { notify } from "../stores/notifications.js";
  import { formatApiErrorDetail } from "../api/client.js";

  let categories = [];
  let loading = true;

  let newKey = "";
  let newKeywords = "";
  let creating = false;

  let keywordDrafts = {}; // category key -> draft input text
  let addingKeywordFor = null;

  async function load() {
    loading = true;
    try {
      categories = await listCategories();
    } catch (err) {
      notify.error(formatApiErrorDetail(err.detail));
    } finally {
      loading = false;
    }
  }

  onMount(load);

  async function handleCreate() {
    const keyError = validateCategoryKey(newKey.trim());
    if (keyError) {
      notify.error(keyError);
      return;
    }
    creating = true;
    try {
      const keywords = newKeywords
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean);
      await createCategory(newKey.trim(), keywords);
      notify.success(`Category "${newKey.trim()}" created.`);
      newKey = "";
      newKeywords = "";
      await load();
    } catch (err) {
      notify.error(formatApiErrorDetail(err.detail));
    } finally {
      creating = false;
    }
  }

  async function handleAddKeyword(categoryKey) {
    const draft = (keywordDrafts[categoryKey] || "").trim();
    if (!draft) return;
    addingKeywordFor = categoryKey;
    try {
      const keywords = draft.split(",").map((k) => k.trim()).filter(Boolean);
      await addCategoryKeywords(categoryKey, keywords);
      notify.success(`Added keyword(s) to "${categoryKey}".`);
      keywordDrafts[categoryKey] = "";
      await load();
    } catch (err) {
      notify.error(formatApiErrorDetail(err.detail));
    } finally {
      addingKeywordFor = null;
    }
  }
</script>

<div class="page">
  <div class="page-header">
    <h1>Categories</h1>
  </div>

  <section class="new-category">
    <h2>Add a New Category</h2>
    <form on:submit|preventDefault={handleCreate} class="new-category-form">
      <label>
        Key
        <input type="text" bind:value={newKey} placeholder="shipping_delay" />
      </label>
      <label>
        Starting keywords (comma separated, optional)
        <input type="text" bind:value={newKeywords} placeholder="package late, tracking lost" />
      </label>
      <button type="submit" class="btn-primary" disabled={creating || !newKey.trim()}>
        {creating ? "Creating…" : "Create Category"}
      </button>
    </form>
    <p class="hint">
      "other" is the built-in fallback category and can't be created or edited here.
    </p>
  </section>

  <section>
    <h2>Existing Categories</h2>
    {#if loading}
      <p class="loading">Loading categories…</p>
    {:else}
      <div class="category-list">
        {#each categories as c (c.category)}
          <div class="category-card">
            <h3>{titleCase(c.category)}</h3>
            <div class="keywords">
              {#each c.keywords as kw}
                <span class="keyword-chip">{kw}</span>
              {/each}
              {#if c.keywords.length === 0}
                <span class="no-keywords">No keywords yet.</span>
              {/if}
            </div>
            <form class="add-keyword-form" on:submit|preventDefault={() => handleAddKeyword(c.category)}>
              <input
                type="text"
                bind:value={keywordDrafts[c.category]}
                placeholder="add keyword(s), comma separated"
              />
              <button type="submit" class="btn-secondary" disabled={addingKeywordFor === c.category}>
                {addingKeywordFor === c.category ? "Adding…" : "Add"}
              </button>
            </form>
            <p class="hint">
              Adding only appends new keywords — existing ones can't be removed here.
            </p>
          </div>
        {/each}
      </div>
    {/if}
  </section>
</div>

<style>
  h2 {
    font-size: 1rem;
    margin-bottom: 0.5rem;
  }
  .new-category {
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid #e2e8f0;
  }
  .new-category-form {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: end;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.85rem;
    color: #334155;
  }
  input {
    padding: 0.5rem 0.6rem;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-size: 0.9rem;
    min-width: 220px;
  }
  .hint {
    font-size: 0.78rem;
    color: #64748b;
    margin: 0.5rem 0 0;
  }
  .category-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
  }
  .category-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1rem;
  }
  .category-card h3 {
    margin: 0 0 0.5rem;
    font-size: 0.95rem;
  }
  .keywords {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-bottom: 0.75rem;
    min-height: 1.5rem;
  }
  .keyword-chip {
    font-size: 0.75rem;
    background: #eef2ff;
    border: 1px solid #c7d2fe;
    border-radius: 999px;
    padding: 0.1rem 0.5rem;
    color: #3730a3;
  }
  .no-keywords {
    font-size: 0.8rem;
    color: #94a3b8;
  }
  .add-keyword-form {
    display: flex;
    gap: 0.5rem;
  }
  .add-keyword-form input {
    flex: 1;
    min-width: 0;
  }

  @media (max-width: 640px) {
    .category-list {
      grid-template-columns: 1fr;
    }
  }
</style>
