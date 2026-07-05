export function formatDateTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export function formatConfidence(value) {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

export function titleCase(value) {
  if (!value) return "";
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
