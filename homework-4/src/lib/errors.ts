export interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, string>;
}

export function badRequest(message: string, details?: Record<string, string>): ErrorResponse {
  return {
    error: "BAD_REQUEST",
    message,
    details,
  };
}

export function notFound(message: string = "Resource not found"): ErrorResponse {
  return {
    error: "NOT_FOUND",
    message,
  };
}

export function internalError(message: string = "Internal server error"): ErrorResponse {
  return {
    error: "INTERNAL_ERROR",
    message,
  };
}

export function conflict(message: string): ErrorResponse {
  return {
    error: "CONFLICT",
    message,
  };
}
