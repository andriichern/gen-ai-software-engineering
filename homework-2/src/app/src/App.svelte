<script>
  import { Router, Route } from "svelte-routing";
  import "./app.css";
  import NavBar from "./components/NavBar.svelte";
  import Toast from "./components/Toast.svelte";
  import TicketListPage from "./pages/TicketListPage.svelte";
  import TicketFormPage from "./pages/TicketFormPage.svelte";
  import TicketDetailPage from "./pages/TicketDetailPage.svelte";
  import ImportPage from "./pages/ImportPage.svelte";
  import CategoriesPage from "./pages/CategoriesPage.svelte";

  export let url = "";
</script>

<Router {url}>
  <NavBar />
  <Toast />
  <Route path="/" component={TicketListPage} />
  <Route path="/tickets/new" component={TicketFormPage} />
  <Route path="/tickets/:id/edit" let:params>
    <TicketFormPage id={params.id} />
  </Route>
  <Route path="/tickets/:id" let:params>
    <TicketDetailPage id={params.id} />
  </Route>
  <Route path="/import" component={ImportPage} />
  <Route path="/categories" component={CategoriesPage} />
</Router>
