import { writable } from "svelte/store";

export const notifications = writable([]);

let nextId = 1;

function push(type, message) {
  const id = nextId++;
  notifications.update((list) => [...list, { id, type, message }]);
  setTimeout(() => dismiss(id), 5000);
}

export function dismiss(id) {
  notifications.update((list) => list.filter((n) => n.id !== id));
}

export const notify = {
  success: (message) => push("success", message),
  error: (message) => push("error", message),
};
