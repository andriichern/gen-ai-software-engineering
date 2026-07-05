<script>
  import { titleCase } from "../utils/format.js";

  export let value;
  export let kind = "default"; // priority | status | category | default

  const priorityClass = {
    urgent: "badge-urgent",
    high: "badge-high",
    medium: "badge-medium",
    low: "badge-low",
  };
  const statusClass = {
    new: "badge-new",
    in_progress: "badge-progress",
    waiting_customer: "badge-waiting",
    resolved: "badge-resolved",
    closed: "badge-closed",
  };

  $: cssClass =
    kind === "priority"
      ? priorityClass[value] || "badge-default"
      : kind === "status"
        ? statusClass[value] || "badge-default"
        : "badge-default";
</script>

<span class="badge {cssClass}">{titleCase(value)}</span>

<style>
  .badge {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
    background: var(--badge-bg, #e2e8f0);
    color: var(--badge-fg, #1a202c);
  }
  .badge-urgent {
    background: #fee2e2;
    color: #991b1b;
  }
  .badge-high {
    background: #ffedd5;
    color: #9a3412;
  }
  .badge-medium {
    background: #e0e7ff;
    color: #3730a3;
  }
  .badge-low {
    background: #e5e7eb;
    color: #374151;
  }
  .badge-new {
    background: #dbeafe;
    color: #1e40af;
  }
  .badge-progress {
    background: #fef9c3;
    color: #854d0e;
  }
  .badge-waiting {
    background: #fae8ff;
    color: #86198f;
  }
  .badge-resolved {
    background: #dcfce7;
    color: #166534;
  }
  .badge-closed {
    background: #e5e7eb;
    color: #374151;
  }
</style>
