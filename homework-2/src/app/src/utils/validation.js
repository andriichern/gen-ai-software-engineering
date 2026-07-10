const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CATEGORY_KEY_PATTERN = /^[a-z][a-z0-9_]*$/;

/** Mirrors the backend's TicketCreate/TicketUpdate constraints so obviously
 * invalid input is caught before hitting the API. */
export function validateTicketForm(fields) {
  const errors = {};

  if (!fields.customer_id || !fields.customer_id.trim()) {
    errors.customer_id = "Customer ID is required.";
  }
  if (!fields.customer_email || !EMAIL_PATTERN.test(fields.customer_email)) {
    errors.customer_email = "Enter a valid email address.";
  }
  if (!fields.customer_name || !fields.customer_name.trim()) {
    errors.customer_name = "Customer name is required.";
  }
  if (
    !fields.subject ||
    fields.subject.length < 1 ||
    fields.subject.length > 200
  ) {
    errors.subject = "Subject must be 1-200 characters.";
  }
  if (
    !fields.description ||
    fields.description.length < 10 ||
    fields.description.length > 2000
  ) {
    errors.description = "Description must be 10-2000 characters.";
  }

  return { valid: Object.keys(errors).length === 0, errors };
}

export function validateCategoryKey(key) {
  if (!key || !CATEGORY_KEY_PATTERN.test(key)) {
    return "Key must be lowercase snake_case, starting with a letter (e.g. shipping_delay).";
  }
  if (key === "other") {
    return "'other' is the reserved fallback category and can't be created here.";
  }
  return null;
}
