<script>
  import { Link } from "svelte-routing";
</script>

<nav class="navbar">
  <div class="brand">Support Ticket Console</div>
  <div class="links">
    <Link to="/">Tickets</Link>
    <Link to="/tickets/new">New Ticket</Link>
    <Link to="/import">Import</Link>
    <Link to="/categories">Categories</Link>
  </div>
</nav>

<style>
  .navbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.85rem 1.25rem;
    background: #1e293b;
    color: white;
  }
  .brand {
    font-weight: 700;
    font-size: 1.05rem;
  }
  .links {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
  }
  .links :global(a) {
    color: #e2e8f0;
    text-decoration: none;
    font-size: 0.9rem;
  }
  .links :global(a:hover) {
    color: white;
    text-decoration: underline;
  }
</style>
