import { request } from "./client.js";

export function listTickets(filters = {}) {
  return request("/tickets", { params: filters });
}

export function getTicket(id) {
  return request(`/tickets/${id}`);
}

export function createTicket(payload, { autoClassify = false } = {}) {
  return request("/tickets", {
    method: "POST",
    json: payload,
    params: { auto_classify: autoClassify || undefined },
  });
}

export function updateTicket(id, payload) {
  return request(`/tickets/${id}`, { method: "PUT", json: payload });
}

export function deleteTicket(id) {
  return request(`/tickets/${id}`, { method: "DELETE" });
}

export function autoClassifyTicket(id) {
  return request(`/tickets/${id}/auto-classify`, { method: "POST" });
}

export function importTickets(file, { autoClassify = false } = {}) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/tickets/import", {
    method: "POST",
    body: formData,
    params: { auto_classify: autoClassify || undefined },
  });
}
