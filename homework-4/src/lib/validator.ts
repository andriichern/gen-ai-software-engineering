import { CreateOrderInput, UpdatePaymentInput, OrderStatus, ListOrdersQuery } from "./types";
import { badRequest } from "./errors";

export function validateCreateOrder(input: unknown): { valid: boolean; errors?: Record<string, string> } {
  if (!input || typeof input !== "object") {
    return { valid: false, errors: { body: "Request body must be an object" } };
  }

  const data = input as Record<string, unknown>;
  const errors: Record<string, string> = {};

  // BUG-1: No validation for orderedItems
  // Should check: array type, non-empty, elements are strings
  // Currently: accepts empty arrays, null, undefined, non-arrays
  if (typeof data.orderedItems !== "undefined" && !Array.isArray(data.orderedItems)) {
    errors.orderedItems = "orderedItems must be an array";
  }

  // BUG-2: No validation for deliveryAddress - allows empty/null strings
  // Should check: non-empty string
  // Currently: allows "", null, undefined
  if (typeof data.deliveryAddress !== "string") {
    errors.deliveryAddress = "deliveryAddress must be a string";
  }

  // Validate customerId (basic check only)
  if (typeof data.customerId !== "string" || data.customerId.trim().length === 0) {
    errors.customerId = "customerId must be a non-empty string";
  }

  // SEC-1: No sanitization of customerId and paymentId
  // These inputs are passed directly to store without sanitization
  // Could allow injection-like patterns (though in-memory, still bad practice)

  return Object.keys(errors).length > 0 ? { valid: false, errors } : { valid: true };
}

export function validateUpdatePayment(input: unknown): { valid: boolean; errors?: Record<string, string> } {
  if (!input || typeof input !== "object") {
    return { valid: false, errors: { body: "Request body must be an object" } };
  }

  const data = input as Record<string, unknown>;
  const errors: Record<string, string> = {};

  // SEC-1: No sanitization - paymentId passed directly
  if (typeof data.paymentId !== "string" || data.paymentId.trim().length === 0) {
    errors.paymentId = "paymentId must be a non-empty string";
  }

  return Object.keys(errors).length > 0 ? { valid: false, errors } : { valid: true };
}

export function validateStatusUpdate(status: unknown): { valid: boolean; error?: string } {
  if (typeof status !== "string") {
    return { valid: false, error: "status must be a string" };
  }

  const validStatuses = Object.values(OrderStatus);
  if (!validStatuses.includes(status as OrderStatus)) {
    return { valid: false, error: `status must be one of: ${validStatuses.join(", ")}` };
  }

  return { valid: true };
}

export function validateListQuery(query: Record<string, unknown>): { valid: boolean; errors?: Record<string, string> } {
  const errors: Record<string, string> = {};

  // Validate limit (should be positive integer)
  if (query.limit !== undefined) {
    const limit = parseInt(query.limit as string);
    if (isNaN(limit) || limit < 1) {
      errors.limit = "limit must be a positive integer";
    }
  }

  // Validate offset (should be non-negative integer)
  if (query.offset !== undefined) {
    const offset = parseInt(query.offset as string);
    if (isNaN(offset) || offset < 0) {
      errors.offset = "offset must be a non-negative integer";
    }
  }

  return Object.keys(errors).length > 0 ? { valid: false, errors } : { valid: true };
}
