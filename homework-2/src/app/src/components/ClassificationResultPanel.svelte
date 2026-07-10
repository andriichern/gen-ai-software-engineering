<script>
  import Badge from "./Badge.svelte";
  import { formatConfidence } from "../utils/format.js";

  export let result;
</script>

{#if result}
  <div class="result-panel">
    <div class="result-row">
      <Badge value={result.category} kind="category" />
      <Badge value={result.priority} kind="priority" />
      <span class="confidence"
        >Confidence: {formatConfidence(result.confidence)}</span
      >
    </div>
    <p class="reasoning">{result.reasoning}</p>
    {#if result.keywords_found?.length}
      <div class="keywords">
        {#each result.keywords_found as kw (kw)}
          <span class="keyword-chip">{kw}</span>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .result-panel {
    border: 1px solid #c7d2fe;
    background: #eef2ff;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .result-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
  }
  .confidence {
    font-size: 0.85rem;
    color: #3730a3;
    font-weight: 600;
  }
  .reasoning {
    margin: 0;
    font-size: 0.85rem;
    color: #334155;
  }
  .keywords {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }
  .keyword-chip {
    font-size: 0.75rem;
    background: white;
    border: 1px solid #c7d2fe;
    border-radius: 999px;
    padding: 0.1rem 0.5rem;
    color: #3730a3;
  }
</style>
