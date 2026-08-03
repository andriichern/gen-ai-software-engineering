# Bug Context: Order API Bugs

## Overview
This sample Order Management API contains **5 intentional bugs + security issues** seeded for the 4-agent pipeline to detect and fix.

---

## Bugs Planted

### BUG-1: Missing Validation for `orderedItems` Array
**Location**: `src/lib/validator.ts` → `validateCreateOrder()`  
**Severity**: HIGH  
**Description**: 
- The validator does NOT check if `orderedItems` is a non-empty array
- Accepts empty arrays `[]`
- Accepts non-array values like strings or null
- Accepts array elements that are not strings

**Expected Behavior**: 
- `orderedItems` must be an array
- Must contain at least one element
- All elements must be strings (item IDs)

**Current Behavior**: No validation, accepts invalid data

---

### BUG-2: Missing Validation for `deliveryAddress`
**Location**: `src/lib/validator.ts` → `validateCreateOrder()`  
**Severity**: HIGH  
**Description**:
- The validator does NOT check if `deliveryAddress` is a non-empty string
- Accepts empty strings `""`
- Accepts null/undefined without proper error

**Expected Behavior**:
- `deliveryAddress` must be a non-empty string

**Current Behavior**: Only checks type, allows empty strings

---

### SEC-1: No Input Sanitization (Injection Risk)
**Location**: `src/lib/validator.ts` → `validateCreateOrder()` and `validateUpdatePayment()`  
**Severity**: MEDIUM  
**Type**: Input Validation / Injection Risk  
**Description**:
- `customerId` and `paymentId` are accepted as-is without sanitization
- Could allow injection patterns (though in-memory storage limits actual damage)
- No trimming of whitespace

**Expected Behavior**:
- Input should be sanitized/trimmed before storing
- Special characters should be validated

**Current Behavior**: Direct pass-through without sanitization

---

### BUG-3: No Status Transition Validation
**Location**: `src/lib/service.ts` → `updateStatus()` and `updateOrder()`  
**Severity**: HIGH  
**Description**:
- Service allows ANY status transition from ANY state to ANY state
- Can transition from `Sent` back to `Processing` (invalid)
- Can transition from `Sent` to `New` (invalid)
- No state machine enforcement

**Valid Transitions**:
```
New → Processing → In Delivery → Sent (one-way, terminal)
```

**Current Behavior**: All transitions allowed

---

### BUG-4: Incorrect Status Filtering Logic
**Location**: `src/lib/service.ts` → `listOrders()`  
**Severity**: MEDIUM  
**Description**:
- Status filter uses loose `==` comparison instead of strict `===`
- Can match unintended values
- For example: filtering by status `"In"` might incorrectly match `"In Delivery"` due to string matching quirks

**Expected Behavior**:
- Exact match comparison (strict equality)
- Must match enum values exactly

**Current Behavior**: Uses loose equality, may have false positives

---

## How to Find These Bugs

1. **Run tests**: `npm test` — tests will FAIL exposing these bugs
2. **Manual API testing**: 
   - Create order with empty `orderedItems` — should fail but doesn't
   - Create order with empty `deliveryAddress` — should fail but doesn't
   - Update order status from `Sent` to `Processing` — should fail but doesn't
   - Filter by partial status like `"In"` — should return 0 results, may return more

3. **Code review**: Search for:
   - `orderedItems` validation in `validator.ts`
   - `deliveryAddress` validation in `validator.ts`
   - Status transition checks in `service.ts` `updateStatus()` method
   - Exact equality check in `listOrders()` filter logic
   - Input sanitization in `validator.ts`

---

## Test Expectations

All tests in `__tests__/` are **correct** and expose these bugs:
- `validator.test.ts` — Tests for BUG-1, BUG-2, SEC-1
- `service.test.ts` — Tests for BUG-3, BUG-4
- `integration/api.test.ts` — End-to-end tests covering all bugs

Running `npm test` should show failures for:
- ❌ Empty orderedItems validation
- ❌ Empty deliveryAddress validation
- ❌ Invalid status transitions (Sent → Processing)
- ❌ Partial status string matching

---

## Files to Fix

- `src/lib/validator.ts` — Add validation for `orderedItems`, `deliveryAddress`, sanitization
- `src/lib/service.ts` — Add status transition validation, fix filtering logic

---

## References

- **TASKS.md**: Homework 4 requirements
- **Types**: `src/lib/types.ts` — Order entity definition
- **API Routes**: `src/app/api/orders/` — endpoint implementations
