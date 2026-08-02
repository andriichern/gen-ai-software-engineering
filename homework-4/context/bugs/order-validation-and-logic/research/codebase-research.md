# Codebase Research: Initial Findings

## Summary

- Total issues identified: 4
- Issues from test failures: 3 (covering 9 individual failing test cases)
- Issues from static analysis: 1 (latent, not currently exercised by any failing test)

Note: SEC-1 (missing input sanitization for `customerId`/`paymentId` in `src/lib/validator.ts`) is documented in `context/bugs/order-validation-and-logic/bug-context.md` but is explicitly out of scope for this agent and is left for the Security Verifier agent.

## Issues Found

### Issue 1: Missing validation for `orderedItems` (non-empty array of strings)

**Severity Level**: [To be assigned in Phase 2]
**File**: `src/lib/validator.ts`
**Line(s)**: 15-17
**Type**: Validation

**Current Code**:
```typescript
  // BUG-1: No validation for orderedItems
  // Should check: array type, non-empty, elements are strings
  // Currently: accepts empty arrays, null, undefined, non-arrays
  if (typeof data.orderedItems !== "undefined" && !Array.isArray(data.orderedItems)) {
    errors.orderedItems = "orderedItems must be an array";
  }
```

**Expected Behavior**: `validateCreateOrder()` should reject requests where `orderedItems` is missing, not an array, an empty array, or contains non-string elements.

**Actual Behavior**: The check only fires when `orderedItems` is present AND not an array. It does not fire for `undefined`/missing, does not reject empty arrays `[]`, and does not check that array elements are strings (e.g. `['item-1', 123]` passes).

**Evidence**:
- Test failure: `Validator › validateCreateOrder › should reject orderedItems that is an empty array` (`tests/unit/validator.test.ts:17-26`)
- Test failure: `Validator › validateCreateOrder › should reject orderedItems with non-string elements` (`tests/unit/validator.test.ts:39-48`)
- Test failure: `Order API Integration › Create Order › should reject order with empty orderedItems array` (`tests/integration/api.test.ts:25`)
- Reproduction: `validateCreateOrder({ orderedItems: [], customerId: 'cust-123', deliveryAddress: '123 Main St' })` returns `{ valid: true }`.

---

### Issue 2: Missing validation for `deliveryAddress` (non-empty string)

**Severity Level**: [To be assigned in Phase 2]
**File**: `src/lib/validator.ts`
**Line(s)**: 19-24
**Type**: Validation

**Current Code**:
```typescript
  // BUG-2: No validation for deliveryAddress - allows empty/null strings
  // Should check: non-empty string
  // Currently: allows "", null, undefined
  if (typeof data.deliveryAddress !== "string") {
    errors.deliveryAddress = "deliveryAddress must be a string";
  }
```

**Expected Behavior**: `validateCreateOrder()` should reject a `deliveryAddress` that is an empty (or whitespace-only) string, in addition to rejecting non-string/null/undefined values.

**Actual Behavior**: Only the type is checked. An empty string `""` passes `typeof data.deliveryAddress !== "string"` (it is a string) so no error is recorded, and the order is created with a blank delivery address.

**Evidence**:
- Test failure: `Validator › validateCreateOrder › should reject empty deliveryAddress` (`tests/unit/validator.test.ts:51-60`)
- Test failure: `Order API Integration › Create Order › should reject order with empty deliveryAddress` (`tests/integration/api.test.ts:34`)
- Reproduction: `validateCreateOrder({ orderedItems: ['item-1'], customerId: 'cust-123', deliveryAddress: '' })` returns `{ valid: true }`.
- Note: `validateCreateOrder({ ..., deliveryAddress: null })` is correctly rejected today (`typeof null !== 'string'`), so that specific unit test (`tests/unit/validator.test.ts:62-71`) currently passes; only the empty-string case is broken.

---

### Issue 3: No order-status state machine enforcement

**Severity Level**: [To be assigned in Phase 2]
**File**: `src/lib/service.ts`
**Line(s)**: 55-84 (`updateOrder()` lines 62-64, `updateStatus()` lines 77-83)
**Type**: State Machine

**Current Code**:
```typescript
  static updateOrder(id: string, updates: UpdateOrderInput): Order | undefined {
    const order = store.getById(id);
    if (!order) return undefined;

    // BUG-3: No status transition validation
    // Should prevent invalid state transitions (e.g., Sent -> Processing, Sent -> New)
    // Currently: allows any transition from any state to any state
    if (updates.status) {
      order.status = updates.status;
    }
    ...
  static updateStatus(id: string, newStatus: OrderStatus): Order | undefined {
    const order = store.getById(id);
    if (!order) return undefined;

    // BUG-3: Same issue - no status transition validation
    order.status = newStatus;
    return store.update(id, order);
  }
```

**Expected Behavior**: Status should only move forward through `New → Processing → In Delivery → Sent`, one-way, with `Sent` terminal. Any other transition (e.g. `Sent → Processing`, `Sent → New`, or skipping states arbitrarily) should be rejected.

**Actual Behavior**: Both `updateOrder()` and `updateStatus()` assign `newStatus`/`updates.status` directly onto the order with no check against the current status, so any transition from any state to any state succeeds, including moving a terminal `Sent` order backwards.

**Evidence**:
- Test failure: `OrderService › updateStatus - BUG-3: No status transition validation › should prevent transition from "Sent" to "Processing"` (`tests/unit/service.test.ts:125-136`)
- Test failure: `OrderService › updateStatus - BUG-3: No status transition validation › should prevent transition from "Sent" to "New"` (`tests/unit/service.test.ts:138-146`)
- Test failure: `Order API Integration › Update Order Status › should prevent transition from Sent back to Processing` (`tests/integration/api.test.ts:96`)
- Test failure: `Order API Integration › Update Order Status › should prevent transition from Sent back to New` (`tests/integration/api.test.ts:106`)
- Reproduction: create an order, force its status to `Sent` via the store, then call `OrderService.updateStatus(id, OrderStatus.Processing)` — the status changes to `Processing` instead of being rejected.

---

### Issue 4: Weak equality (`==`) used for status filter comparison

**Severity Level**: [To be assigned in Phase 2]
**File**: `src/lib/service.ts`
**Line(s)**: 30-35
**Type**: Logic

**Current Code**:
```typescript
    // BUG-4: Status filter has loose comparison / incorrect logic
    // Current: uses loose equality (==) and string search which can match partial strings
    // e.g., filtering for "In" would match "In Delivery" and "New" due to poor logic
    if (filters?.status) {
      results = results.filter((order) => order.status == filters.status);
    }
```

**Expected Behavior**: Status filtering should use strict equality (`===`) and should only ever compare like-typed values, per the project's code-quality expectations (avoid weak/coercive comparisons entirely).

**Actual Behavior**: The comparison uses `==` instead of `===`. Because `order.status` (an `OrderStatus` enum, which is string-backed) and `filters.status` are both strings at every current call site, `==` and `===` currently produce identical results for string-vs-string comparisons — there is no actual substring/partial matching bug as the inline comment implies (`"In" == "In Delivery"` is `false` under both `==` and `===`). The `tests/unit/service.test.ts:78-84` test asserting `"In"` does not partial-match `"In Delivery"` currently **passes**. The residual risk is that `==` performs type coercion: if a non-string value ever reaches this filter (e.g. a number, boolean, or object with a custom `toString`/`valueOf`), `order.status == filters.status` could incorrectly evaluate `true` where `===` would correctly evaluate `false`. This is a code-quality / latent-correctness issue (weak comparison operator) rather than a currently-observable functional break.

**Evidence**:
- Test failure: none currently failing for this issue (all `listOrders` filter tests in `tests/unit/service.test.ts:34-85` and `tests/integration/api.test.ts` pass with the current data types).
- Reproduction (static/type-coercion risk): `order.status == 0` or similar non-string coercive comparisons would behave differently under `==` vs `===`, but no current caller supplies non-string filter values, so this cannot be reproduced through the public API today.

---

## References

- Bug Context: `context/bugs/order-validation-and-logic/bug-context.md`
- Test Files: `tests/unit/validator.test.ts`, `tests/unit/service.test.ts`, `tests/integration/api.test.ts`
- Code Base: `src/lib/validator.ts`, `src/lib/service.ts`, `src/lib/types.ts`, `src/lib/store.ts`, `src/orders/orders.service.ts`, `src/orders/orders.controller.ts`
