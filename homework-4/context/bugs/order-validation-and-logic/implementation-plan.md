# Implementation Plan: Bug Fixes

## Overview

**Total Fixes**: 4
**Severity Breakdown**: 0 Critical, 3 High, 0 Medium, 1 Low
**Estimated Complexity**: Low

**Summary**: Two validation gaps in `src/lib/validator.ts` and one state-machine gap in `src/lib/service.ts` are High severity and should be fixed first since they let invalid data through the core order-creation and status-update workflows; a Low-severity code-quality fix (weak `==` comparison in `listOrders()`) can be applied last since it has no observed functional impact today.

---

## Fix Strategy & Ordering

This plan prioritizes fixes by **severity first, then by interdependencies**. Fixes are applied in order to ensure:

1. High-severity issues (validation gaps and state machine enforcement) are addressed first
2. Dependencies are respected (no fix depends on unapplied changes)
3. Related fixes (both validator.ts changes) are grouped for easier testing

**Key Interdependencies**:
No interdependencies. All fixes are independent and can be applied in any order — Fix 1 and Fix 2 are both isolated additions inside `validateCreateOrder()` in `validator.ts`, Fix 3 is isolated to the two update methods in `service.ts`, and Fix 4 is a single-line operator change in a different function of the same file. None of the fixes share state or require another fix's code to exist first.

---

## Fixes by Priority

### Fix 1: Add non-empty, all-string array validation for `orderedItems`

**Severity**: High

**File(s)**: `src/lib/validator.ts`

**Problem Location**: Lines 15-17 (inside `validateCreateOrder()`)

**Current Behavior**: The existing check only rejects values that are present and not an array. It does not reject a missing `orderedItems`, an empty array `[]`, or an array containing non-string elements — all three currently pass validation and let the order be created.

**Required Fix**: Extend the `orderedItems` check in `validateCreateOrder()` so that it requires the field to be present and to be an array; rejects an empty array; and rejects an array where any element is not a string. Each failure case should populate `errors.orderedItems` with a clear, descriptive message so `Object.keys(errors).length > 0` correctly triggers `{ valid: false }`.

**Why This Fix Matters**:
- Impact Scope: Affects the core order-creation workflow for every API consumer.
- Data Risk: Prevents orders with no items or malformed item lists from being persisted in the store.
- Functionality: Restores the core "an order must contain valid items" business rule.

**Test Strategy**: Run `tests/unit/validator.test.ts` (the three `orderedItems`-related `it` blocks under `validateCreateOrder`) and `tests/integration/api.test.ts` (`should reject order with empty orderedItems array`) — all should pass after the fix. Confirm `should accept valid order data` still passes to avoid over-tightening the rule.

**Dependencies**: None

---

### Fix 2: Add non-empty string validation for `deliveryAddress`

**Severity**: High

**File(s)**: `src/lib/validator.ts`

**Problem Location**: Lines 19-24 (inside `validateCreateOrder()`)

**Current Behavior**: The existing check only verifies `typeof data.deliveryAddress === "string"`; an empty string `""` satisfies this type check and passes validation even though it is not a usable delivery address.

**Required Fix**: Extend the `deliveryAddress` check so that, in addition to the existing type check, a string value is also required to be non-empty after trimming whitespace. Populate `errors.deliveryAddress` with a clear message when the trimmed value is empty (or when the field is missing/non-string, as today).

**Why This Fix Matters**:
- Impact Scope: Affects the core order-creation workflow for every API consumer.
- Data Risk: Prevents orders with a blank/unusable delivery address from being persisted.
- Functionality: Restores the core "an order must be deliverable" business rule.

**Test Strategy**: Run `tests/unit/validator.test.ts` (`should reject empty deliveryAddress`, `should reject null deliveryAddress`) and `tests/integration/api.test.ts` (`should reject order with empty deliveryAddress`) — all should pass after the fix. Confirm `should accept valid order data` still passes.

**Dependencies**: None

---

### Fix 3: Enforce order-status state machine transitions

**Severity**: High

**File(s)**: `src/lib/service.ts`

**Problem Location**: Lines 55-84 (`updateOrder()` lines 62-64 and `updateStatus()` lines 77-83)

**Current Behavior**: Neither method checks the order's existing status before assigning a new one, so any transition (including from the terminal `Sent` status back to `Processing` or `New`) is silently accepted.

**Required Fix**: Introduce a single shared state-transition rule (e.g. a small allowed-transitions map or ordered sequence: `New → Processing → In Delivery → Sent`, with `Sent` terminal and no backward or skip-ahead moves permitted) and apply it in both `updateOrder()` (when `updates.status` is provided) and `updateStatus()` before the status is written to the order. When an update requests a status that is not a valid next transition from the order's current status, the update should be rejected (do not mutate `order.status`, and surface an error/rejected result consistent with how other validation failures are surfaced in this codebase, e.g. via `src/lib/errors.ts` conventions and the `BadRequestException` pattern already used in `src/orders/orders.service.ts`). Do not change `markDelivered()`, which already sets status to `Sent` as part of its own dedicated, well-defined operation — confirm the new rule allows `In Delivery → Sent` so `markDelivered()` continues to work for orders currently `In Delivery`.

**Why This Fix Matters**:
- Impact Scope: Affects the core order lifecycle workflow for every order in the system.
- Data Risk: Prevents an order's business-critical status from being reverted or corrupted into an inconsistent state (e.g., a `Sent`/delivered order reset to `Processing`).
- Functionality: Restores core workflow-sequencing enforcement with no available workaround previously existing for API consumers.

**Test Strategy**: Run `tests/unit/service.test.ts` (all `updateStatus - BUG-3` cases: reject `Sent → Processing`, reject `Sent → New`, allow `New → Processing`, allow `Processing → InDelivery`) and `tests/integration/api.test.ts` (`should prevent transition from Sent back to Processing`, `should prevent transition from Sent back to New`, and the `should allow New → Processing` style tests) — all should pass. Also re-run `markDelivered` tests to confirm no regression.

**Dependencies**: None

---

### Fix 4: Replace loose equality with strict equality in status filter

**Severity**: Low

**File(s)**: `src/lib/service.ts`

**Problem Location**: Lines 30-35 (inside `listOrders()`)

**Current Behavior**: `results.filter((order) => order.status == filters.status)` uses `==` instead of `===`. No currently reachable call path exercises a type mismatch (both operands are always strings today), so there is no observed functional defect, but the operator is inconsistent with the strict `===` used by the adjacent `customerId` and `paid` filters in the same function and leaves latent risk if a non-string value is ever passed through (e.g. via the `filters as any` cast in `src/orders/orders.service.ts`'s `list()` method).

**Required Fix**: Change the `status` filter comparison from `==` to `===`, matching the strict-equality style already used for `customerId` and `paid` filters in the same function. No other behavior change is required, since strict and loose equality currently produce identical results for all real inputs.

**Why This Fix Matters**:
- Impact Scope: Isolated to a single comparison in one function; closes a latent risk rather than fixing an observed defect.
- Data Risk: None currently, but removes a theoretical type-coercion risk if a non-string status filter value is ever introduced upstream.
- Functionality: Brings the `status` filter in line with the strict-equality convention already used elsewhere in `listOrders()`; no regression expected since all current tests already pass with either operator.

**Test Strategy**: Run `tests/unit/service.test.ts` (`listOrders - BUG-4: Status filtering` describe block, including `should not match partial status strings`) and `tests/integration/api.test.ts` status-filter tests — all should continue to pass unchanged after the fix, confirming no regression from the operator change.

**Dependencies**: None

---

## Validation & Rollback

**Validation**: After all fixes are applied, run `npm test` to confirm all tests pass (target: 46 of 46 passing, versus the current 37 of 46).

**Rollback**: If any fix causes test failures:

1. Document which fix caused the failure
2. Stop applying further fixes
3. Report the issue back to the research team

---

## References

- **Verified Research**: `context/bugs/order-validation-and-logic/research/verified-research.md`
- **Bug Context**: `context/bugs/order-validation-and-logic/bug-context.md`
- **Source Code**: `src/lib/validator.ts`, `src/lib/service.ts`
- **Test Command**: `npm test`
