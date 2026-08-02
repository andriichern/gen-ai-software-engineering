# Security Vulnerability Report

## Summary

**Scan Date**: 2026-08-02
**Scan Type**: Full Codebase (no prior `security-report.md` baseline found)
**Detected Language**: TypeScript (Node.js) — Framework: **NestJS** (`@nestjs/common`, `@nestjs/core`, `@nestjs/platform-express`)

**Total Findings**: 7
**Critical**: 0
**High**: 2
**Medium**: 3
**Low**: 2
**Info**: 0

---

## Scan Scope

**Scope Type**: Full Codebase

All source files under `src/` were scanned:
- `src/main.ts`
- `src/app.module.ts`
- `src/orders/orders.controller.ts`
- `src/orders/orders.service.ts`
- `src/orders/orders.module.ts`
- `src/lib/service.ts`
- `src/lib/validator.ts`
- `src/lib/store.ts`
- `src/lib/types.ts`
- `src/lib/errors.ts`

These files also correspond to the areas touched by `fix-summary.md` (`src/lib/validator.ts`, `src/lib/service.ts`), so this scan also serves as verification that the recent bug fixes did not introduce new vulnerabilities.

---

## Findings

### Finding 1: Missing Authentication and Authorization on All Order Endpoints

**Severity**: HIGH
**Category**: OWASP A01:2021 Broken Access Control
**File**: `src/orders/orders.controller.ts`
**Line(s)**: 16-80 (all routes)

**Issue**: Every route in `OrdersController` (`POST /api/orders`, `GET /api/orders`, `GET /api/orders/:id`, `DELETE /api/orders/:id`, `PATCH /api/orders/:id/status`, `PATCH /api/orders/:id/payment`, `PATCH /api/orders/:id/delivery`) is exposed with no authentication guard, no session/user context, and no ownership check. Any caller who can reach the API can read, list, update the status of, mark as paid, or delete **any** order belonging to **any** customer, simply by supplying an order `id`.

**Why it matters**: This is a textbook Insecure Direct Object Reference (IDOR) combined with a complete lack of authentication. An attacker (or even a legitimate customer) can enumerate or guess order IDs and view other customers' delivery addresses, mark competitor orders "Sent"/"paid", or delete orders outright — with zero access control. In a real deployment this would allow data disclosure and destructive tampering across tenants.

**Remediation**: Add an authentication guard (e.g., NestJS `AuthGuard`/JWT strategy) at the controller or route level, and add an authorization check that the authenticated principal owns (or is entitled to act on) the target order before executing the operation.

**Example**:
```typescript
// Before
@Delete(':id')
delete(@Param('id') id: string) {
  return this.ordersService.delete(id);
}
```
→
```typescript
// After
@UseGuards(JwtAuthGuard)
@Delete(':id')
delete(@Param('id') id: string, @CurrentUser() user: AuthUser) {
  return this.ordersService.delete(id, user); // service verifies user owns/can manage this order
}
```

---

### Finding 2: Predictable, Non-Cryptographic Order ID Generation

**Severity**: HIGH
**Category**: OWASP A02:2021 Cryptographic Failures
**File**: `src/lib/service.ts`
**Line(s)**: 5-7

**Issue**:
```typescript
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}
```
Order IDs — which double as the only "access token" for reading/updating/deleting an order (see Finding 1) — are generated from `Date.now()` plus `Math.random()`. `Math.random()` is not cryptographically secure and is seedable/predictable, and prefixing with a coarse timestamp further narrows the search space for brute-forcing or guessing valid IDs.

**Why it matters**: Combined with the missing-authorization issue above, a predictable ID scheme means an attacker doesn't even need a leaked ID — IDs created around a known time window can be brute-forced with a small keyspace, exposing other customers' orders.

**Remediation**: Use a cryptographically secure, high-entropy, non-sequential identifier such as `crypto.randomUUID()` (Node ≥14.17) or the `uuid` package (v4).

**Example**:
```typescript
import { randomUUID } from "crypto";

function generateId(): string {
  return randomUUID();
}
```

---

### Finding 3: Unsanitized/Unbounded User Input Stored and Echoed Back (`customerId`, `deliveryAddress`, `paymentId`)

**Severity**: MEDIUM
**Category**: OWASP A03:2021 Injection / A07:2021 XSS (stored) — Task 3: Injection & Missing Validation
**File**: `src/lib/validator.ts` (lines 24-33, 51-52), `src/lib/service.ts` (lines 111-118)

**Issue**: `customerId`, `deliveryAddress`, and `paymentId` are only checked for "is a non-empty string" — there is no bound on length, no character allow-listing, and no encoding/sanitization before the values are persisted in the in-memory store and returned verbatim in API responses (`Order` objects). This is explicitly flagged in the code itself:
```typescript
// SEC-1: No sanitization of customerId and paymentId
// These inputs are passed directly to store without sanitization
// Could allow injection-like patterns (though in-memory, still bad practice)
```

**Why it matters**: While the current store is in-memory (so classic SQL injection doesn't apply today), these same values will typically flow into a real database query, a log line, an email/notification template, or be rendered in a front-end/admin UI without escaping. Because the API returns the raw stored string in JSON responses, any HTML/script content placed in `deliveryAddress` or `customerId` becomes a stored-XSS payload the moment a client renders it unescaped. There's also no length cap, enabling oversized payloads (see Finding 6).

**Remediation**: Add strict input constraints (max length, allow-listed character set for IDs) and treat all free-text fields (`deliveryAddress`) as untrusted at every output boundary — escape/encode on render, and use parameterized queries when this moves to a real datastore.

**Example**:
```typescript
const MAX_ADDRESS_LEN = 500;
const ID_PATTERN = /^[a-zA-Z0-9_-]{1,64}$/;

if (typeof data.customerId !== "string" || !ID_PATTERN.test(data.customerId)) {
  errors.customerId = "customerId must be an alphanumeric identifier";
}
if (typeof data.deliveryAddress !== "string" || data.deliveryAddress.trim().length === 0) {
  errors.deliveryAddress = "deliveryAddress must not be empty";
} else if (data.deliveryAddress.length > MAX_ADDRESS_LEN) {
  errors.deliveryAddress = `deliveryAddress must be at most ${MAX_ADDRESS_LEN} characters`;
}
```

---

### Finding 4: Missing Security Headers (No Helmet)

**Severity**: MEDIUM
**Category**: OWASP A05:2021 Security Misconfiguration — Node.js-specific check
**File**: `src/main.ts`
**Line(s)**: 1-19

**Issue**: The Nest bootstrap only configures a `ValidationPipe`. There is no `helmet()` middleware (or equivalent) setting standard security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Content-Security-Policy`, etc.), and `package.json` has no `helmet` dependency at all.

**Why it matters**: Without these headers the API is more susceptible to clickjacking, MIME-sniffing attacks, and lacks transport-security enforcement once fronted by a browser-facing client.

**Remediation**: Add the `helmet` package and apply it globally before other middleware.

**Example**:
```typescript
import helmet from 'helmet';
// ...
const app = await NestFactory.create(AppModule);
app.use(helmet());
```

---

### Finding 5: No Rate Limiting on Mutating Endpoints

**Severity**: MEDIUM
**Category**: OWASP A05:2021 Security Misconfiguration / A04:2021 Insecure Design — Node.js-specific check
**File**: `src/main.ts`, `src/orders/orders.controller.ts`

**Issue**: There is no rate-limiting middleware/guard (e.g., `@nestjs/throttler`) applied anywhere. Combined with Finding 1 (no auth) and Finding 2 (guessable IDs), an attacker can send unlimited requests to brute-force order IDs or spam `POST /api/orders` to exhaust memory (the store is an unbounded in-memory `Map`, see Finding 6).

**Why it matters**: Absence of throttling enables brute-force ID guessing, credential/enumeration attacks, and denial-of-service via resource exhaustion, with no built-in mitigation.

**Remediation**: Add `@nestjs/throttler` (or an API-gateway-level rate limiter) and apply it globally.

**Example**:
```typescript
import { ThrottlerModule } from '@nestjs/throttler';

@Module({
  imports: [ThrottlerModule.forRoot([{ ttl: 60000, limit: 100 }]), OrdersModule],
})
export class AppModule {}
```

---

### Finding 6: Unbounded In-Memory Store / No Payload Size Limits (Resource Exhaustion)

**Severity**: LOW
**Category**: OWASP A04:2021 Insecure Design — Task 3: Missing Validation
**File**: `src/lib/store.ts` (lines 1-47), `src/lib/validator.ts` (orderedItems/deliveryAddress checks)

**Issue**: `OrderStore` is an in-process singleton `Map` with no maximum size, TTL, or eviction policy, and `validateCreateOrder` never caps the number of `orderedItems` or the length of individual strings/`deliveryAddress`. An unauthenticated caller (see Finding 1) can call `POST /api/orders` repeatedly with large arrays/strings to grow the process's memory without bound.

**Why it matters**: This is a straightforward denial-of-service vector — memory exhaustion can crash the Node process, and there's no persistence/backpressure to mitigate it.

**Remediation**: Enforce maximum array length and string length in the validator, and consider a bounded store (LRU/TTL) or a real persistent datastore with row/quota limits for production use.

**Example**:
```typescript
const MAX_ITEMS = 100;
if (Array.isArray(data.orderedItems) && data.orderedItems.length > MAX_ITEMS) {
  errors.orderedItems = `orderedItems must not exceed ${MAX_ITEMS} entries`;
}
```

---

### Finding 7: Missing Security Event Logging

**Severity**: LOW
**Category**: OWASP A09:2021 Security Logging and Monitoring Failures
**File**: `src/orders/orders.service.ts`, `src/lib/service.ts`

**Issue**: No security-relevant events (failed validation attempts, status-transition rejections, deletes, payment updates) are logged anywhere in the request path. `isValidStatusTransition` silently returns the order unchanged on an invalid transition (`src/lib/service.ts` lines 101-105) with no audit trail of the rejected attempt.

**Why it matters**: Without logging, there is no way to detect or investigate abuse patterns (e.g., repeated attempts to force invalid status transitions, mass deletes, or ID-guessing sweeps described in Findings 1 and 2).

**Remediation**: Add structured logging (NestJS `Logger`) around denied/failed operations, including actor identity once authentication (Finding 1) is added.

**Example**:
```typescript
if (!isValidStatusTransition(order.status, newStatus)) {
  this.logger.warn(`Rejected invalid status transition`, { orderId: id, from: order.status, to: newStatus });
  return order;
}
```

---

## Summary & Recommendations

The codebase is a small NestJS/TypeScript in-memory order API. The four functional bug fixes documented in `fix-summary.md` (orderedItems/deliveryAddress validation, status state-machine enforcement, strict equality in the status filter) were reviewed and **introduce no new vulnerabilities** — the added validation logic in `src/lib/validator.ts` and the state-transition guard in `src/lib/service.ts` are sound and, if anything, slightly reduce the attack surface by rejecting malformed input earlier.

However, the application as a whole has significant gaps outside the scope of those functional fixes:

- **No authentication/authorization anywhere** (Finding 1) is the most severe issue — every order, regardless of owner, is fully readable/writable/deletable by any caller who can reach the API.
- **Predictable ID generation** (Finding 2) compounds the access-control gap by making IDs guessable.
- Input validation exists for structural correctness (added by the bug-fix pipeline) but not for **security-relevant constraints** — length limits, character allow-listing, and output-encoding assumptions (Finding 3, Finding 6).
- Standard Node/NestJS production hardening (helmet, rate limiting, security logging) is entirely absent (Findings 4, 5, 7).

**Priority recommendation**: Address Finding 1 (auth/authorization) and Finding 2 (ID generation) before any real deployment — together they mean the API currently has no meaningful access control at all.

---

## References

- **OWASP Top 15**: https://owasp.org/www-project-top-ten/
- **NestJS Security Best Practices**: https://docs.nestjs.com/security/authentication
- **Fix Summary**: `context/bugs/order-validation-and-logic/fix-summary.md`
- **Bug Context**: `context/bugs/order-validation-and-logic/bug-context.md`
